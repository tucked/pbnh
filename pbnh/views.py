import hashlib
import json
import mimetypes
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import flask.typing
import pygraphviz  # type: ignore
from docutils.core import publish_string
from flask import (
    Blueprint,
    Response,
    abort,
    make_response,
    redirect,
    render_template,
    request,
)

from pbnh import db

blueprint = Blueprint("views", __name__)

DOCUTILS_MIMES = {  # parsers
    "text/markdown": "markdown",
    "text/prs.fallenstein.rst": "restructuredtext",
    "text/x-rst": "restructuredtext",
}
REDIRECT_MIME = "text/x.pbnh.redirect"
TEXT_MIMES = {  # non-text types that PbnhEditor can highlight
    "application/ecmascript",
    "application/javascript",
    "application/json",
    "application/json-seq",
    "application/jsonl",
    "application/mbox",
    "application/pgp-keys",
    "application/pgp-signature",
    "application/sql",
    "application/toml",
    "application/x-json",
    "application/x-latex",
    "application/x-ndjson",
    "application/x-perl",
    "application/x-ruby",
    "application/x-sh",
    "application/x-shellscript",
    "application/x-tex",
    "application/x-yaml",
    "application/xml",
    "application/xml-dtd",
    "application/yaml",
}
VIEW_MIMES = {
    "asciicast": {"application/asciicast+json", "application/x-asciicast"},
    "docutils": set(DOCUTILS_MIMES),
    "graphviz": {"text/vnd.graphviz", "text/x-graphviz"},
}

# https://github.com/asciinema/asciinema/issues/224
mimetypes.add_type("application/x-asciicast", ".cast", strict=False)


def _decoded_data(data: bytes, *, encoding: str = "utf-8") -> str:
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        abort(422, f"The paste cannot be decoded as text: {exc}")


def _get_paste(hashid: str) -> dict[str, Any]:
    if hashid == "about":
        about_path = Path(__file__).parent / "static" / "about.md"
        about_text = about_path.read_text().replace("pbnh.example.com", request.host)
        return {
            "data": about_text.encode(),
            "hashid": hashid,
            "ip": request.remote_addr,
            "mime": "text/markdown",
            "sunset": None,
            "timestamp": request.date,
        }
    with db.paster_context() as paster:
        return paster.query(hashid=hashid) or abort(404)


def _guess_extension(mime: str) -> str:
    return (mimetypes.guess_extension(mime, strict=False) or "")[1:]


def _guess_mime(url: str) -> str:
    return mimetypes.guess_type(url, strict=False)[0] or ""


def _mode_for_mime(mime: str) -> str:
    if mime in {REDIRECT_MIME, "redirect"}:
        return "redirect"
    if any(mime in mimes for mimes in VIEW_MIMES.values()):
        return "view"
    if mime.startswith("text/") or mime in TEXT_MIMES:
        return "text"
    return "raw"


def _redirect(path: str, *args: Any, **kwargs: Any) -> flask.typing.ResponseReturnValue:
    return redirect(
        urllib.parse.urlsplit(request.url)._replace(path=path).geturl(),
        *args,
        **kwargs,
    )


class _PasteView:
    def __init__(self, *, paste: dict[str, Any], extension: str = "") -> None:
        self.paste = paste
        self._extension = extension

    def _render_asciicast(self) -> flask.typing.ResponseReturnValue:
        # Prepare query params such that
        # {{params|tojson}} produces a valid JS object:
        params = {}
        for key, value in request.args.items():
            try:
                params[key] = json.loads(value)
            except json.JSONDecodeError:
                params[key] = str(value)
        params.setdefault("preload", True)
        return render_template(
            "asciinema.html.jinja",
            url=self.raw_path(),
            params=params,
        )

    def _render_docutils(self, *, parser: str) -> flask.typing.ResponseReturnValue:
        settings_overrides = {
            "file_insertion_enabled": False,
            "raw_enabled": False,
            "stylesheet_path": ["minimal.css"],
        }
        if "report_level" in request.args:
            try:
                settings_overrides["report_level"] = int(request.args["report_level"])
            except ValueError:
                abort(400, "report_level must be an integer.")
        return make_response(
            publish_string(
                _decoded_data(self.paste["data"]),
                source_path=self.raw_path(),
                parser=parser,
                writer="html5",
                settings_overrides=settings_overrides,
            )
        )

    def _render_graphviz(self) -> flask.typing.ResponseReturnValue:
        try:
            return Response(
                pygraphviz.AGraph(string=_decoded_data(self.paste["data"])).draw(
                    prog="dot", format="svg"
                ),
                mimetype="image/svg+xml",
            )
        except Exception as exc:
            abort(422, f"Graphviz rendering failed: {exc}")

    def _render_raw(self) -> flask.typing.ResponseReturnValue:
        return Response(self.paste["data"], mimetype=self.mime())

    def _render_redirect(self) -> flask.typing.ResponseReturnValue:
        if self._extension:
            abort(400, "Extensions are not supported for redirects.")
        return redirect(_decoded_data(self.paste["data"]), 302)

    def _render_text(self) -> flask.typing.ResponseReturnValue:
        return render_template("editor.html.jinja", url=self.raw_path())

    def _render_view(self) -> flask.typing.ResponseReturnValue:
        mime = self.paste["mime"]
        if self._extension:
            mime = _guess_mime(f"/{self.paste['hashid']}.{self._extension}") or abort(
                400,
                "There is no renderer associated with"
                f" the .{self._extension} extension.",
            )
        if parser := DOCUTILS_MIMES.get(mime):
            return self._render_docutils(parser=parser)
        if mime in VIEW_MIMES["asciicast"]:
            return self._render_asciicast()
        if mime in VIEW_MIMES["graphviz"]:
            return self._render_graphviz()
        abort(400, f"There is no renderer associated with the {mime} media type.")

    def etag(self, mode: str) -> str:
        # This is for caching, not security...
        # If there is a collision, the worst that could happen is
        # a 304 (Not Modified) may be inappropriately returned.
        usedforsecurity = False
        hashid = self.paste["hashid"]
        if hashid == "about":
            hashid = hashlib.sha1(
                self.paste["data"],
                usedforsecurity=usedforsecurity,
            ).hexdigest()
        etag = f"{hashid}.{self.extension()}/{mode or self.mode()}"
        if request.args:
            etag += (
                "?"
                + hashlib.sha1(
                    json.dumps(request.args, sort_keys=True, default=str).encode(),
                    usedforsecurity=usedforsecurity,
                ).hexdigest()
            )
        return etag

    def extension(self) -> str:
        return self._extension or _guess_extension(self.mime())

    def mime(self) -> str:
        return (
            _guess_mime(f"{self.paste['hashid']}.{self._extension}")
            if self._extension
            else self.paste["mime"]
        )

    def mode(self) -> str:
        return _mode_for_mime(self.mime())

    def raw_path(self) -> str:
        return f"/{self.paste['hashid']}.{self.extension()}"

    def rendered(self, mode: str) -> flask.typing.ResponseReturnValue:
        if not mode:
            mode = self.mode()

        if mode in {"cast", "md", "rst"}:  # legacy
            return _redirect(f"/{self.paste['hashid']}.{mode}/view", 301)
        if mode == "txt":  # legacy
            return _redirect(request.path.replace("/txt", "/text"), 301)

        try:
            renderer = {
                "raw": self._render_raw,
                "redirect": self._render_redirect,
                "text": self._render_text,
                "view": self._render_view,
            }[mode]
        except KeyError as exc:
            abort(400, f"{exc} is not a recognized rendering mode.")

        if mode == "redirect":
            return renderer()

        etag = self.etag(mode)
        response = make_response(
            Response(status=304)
            if request.if_none_match.contains_weak(etag)
            else renderer()
        )
        response.set_etag(etag)
        return response


@blueprint.post("/")
def create_paste() -> flask.typing.ResponseReturnValue:
    """Create a new paste."""
    # Calculate the expiration.
    now = request.date or datetime.now(timezone.utc)
    try:
        sunset = now + timedelta(seconds=int(request.form["sunset"]))
    except KeyError:
        sunset = None
    except ValueError as exc:
        abort(400, f"sunset: {exc}")
    if sunset and sunset <= now:
        abort(400, f"sunset ({sunset}) cannot be at/before the request time ({now}).")

    # Get the paste data and MIME type.
    mime = None
    if location := request.form.get("redirect") or request.form.get("r"):
        data = location.encode("utf-8")
        mime = REDIRECT_MIME
    elif text := request.form.get("content") or request.form.get("c"):
        data = text.encode("utf-8")
        mime = request.form.get("mime")
        if mime and "/" not in mime:
            mime = f"text/{mime}"
    elif file_storage := request.files.get("content") or request.files.get("c"):
        data = file_storage.stream.read()
        mime = (
            request.form.get("mime")
            or mimetypes.guess_type(file_storage.filename or "")[0]
        )
    else:
        abort(400, "No content was sent (via the redirect/r or content/c fields).")

    # Create the paste.
    try:
        with db.paster_context() as paster:
            hashid = paster.create(
                data, mime=mime, ip=request.remote_addr, sunset=sunset
            )
    except db.HashCollision as exc:
        hashid = str(exc)
        status = 409
    except db.PasteExists as exc:
        hashid = str(exc)
        status = 200
    else:
        status = 201

    # Return the paste.
    return {"hashid": hashid, "link": request.url + hashid}, status


@blueprint.get("/")
def index() -> str:
    """Render the home page."""
    return render_template("editor.html.jinja")


@blueprint.get("/<string:hashid>.")
@blueprint.get("/<string:hashid>./")
@blueprint.get("/<string:hashid>./<string:mode>")
@blueprint.get("/<string:hashid>.<string:extension>")
def retrieve_paste(
    hashid: str, extension: str = "", mode: str = ""
) -> flask.typing.ResponseReturnValue:
    """Retrieve a paste."""
    paste = _get_paste(hashid)
    if not extension:
        extension = _guess_extension(paste["mime"])
        if extension:
            return _redirect(
                request.path.replace(f"/{hashid}.", f"/{hashid}.{extension}"), 301
            )
    elif extension == "asciinema":
        # .asciinema is a legacy pbnh thing...
        # asciinema used to use .json (application/asciicast+json),
        # and now it uses .cast (application/x-asciicast).
        return _redirect(f"/{hashid}.cast/view", 301)
    return _PasteView(paste=paste, extension=extension).rendered(mode or "raw")


@blueprint.get("/<string:hashid>")
@blueprint.get("/<string:hashid>/<string:mode>")
@blueprint.get("/<string:hashid>.<string:extension>/<string:mode>")
def render_paste(
    hashid: str, extension: str = "", mode: str = ""
) -> flask.typing.ResponseReturnValue:
    """Render a paste."""
    return _PasteView(paste=_get_paste(hashid), extension=extension).rendered(mode)


@blueprint.get("/<string:hashid>/")
@blueprint.get("/<string:hashid>.<string:extension>/")
def redirect_to_mode(
    hashid: str, extension: str = ""
) -> flask.typing.ResponseReturnValue:
    """Redirect to a URL with an explicit mode."""
    mode = _PasteView(paste=_get_paste(hashid), extension=extension).mode()
    return _redirect(request.path + mode, 302)

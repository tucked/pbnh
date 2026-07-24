import functools
import hashlib
import json
import mimetypes
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import flask.typing
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
REDIRECT_MIME = "text/x.pbnh.redirect"

# https://github.com/asciinema/asciinema/issues/224
mimetypes.add_type("application/x-asciicast", ".cast", strict=False)


def _decoded_data(data: bytes, *, encoding: str = "utf-8") -> str:
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        abort(422, f"The paste cannot be decoded as text ({exc}).")


def _etag(paste: dict[str, Any], extension: str, mode: str) -> str:
    # This is for caching, not security...
    # If there is a collision, the worst that could happen is
    # a 304 (Not Modified) may be inappropriately returned.
    usedforsecurity = False
    hashid = paste["hashid"]
    if hashid == "about":
        hashid = hashlib.sha1(
            paste["data"],
            usedforsecurity=usedforsecurity,
        ).hexdigest()
    etag = f"{hashid}.{extension}/{mode}"
    if request.args:
        etag += (
            "?"
            + hashlib.sha1(
                json.dumps(request.args, sort_keys=True, default=str).encode(),
                usedforsecurity=usedforsecurity,
            ).hexdigest()
        )
    return etag


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
    if mime.startswith("text/"):
        if mime == "text/markdown":
            return "md"
        if mime in {"text/x-rst", "text/prs.fallenstein.rst"}:
            return "rst"
        return "text"
    if mime in {"application/asciicast+json", "application/x-asciicast"}:
        return "cast"
    return "raw"


def _redirect(path: str, *args: Any, **kwargs: Any) -> flask.typing.ResponseReturnValue:
    return redirect(
        urllib.parse.urlsplit(request.url)._replace(path=path).geturl(),
        *args,
        **kwargs,
    )


class _RenderRequest:
    def __init__(self, *, paste: dict[str, Any], extension: str = "") -> None:
        self.paste = paste
        self.extension = extension

    def _render_asciicast(self) -> str:
        extension = self.extension or "cast"
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
            url=f"/{self.paste['hashid']}.{extension}",
            params=params,
        )

    def _render_docutils(self, *, parser: str) -> Response:
        source_path = self.paste["hashid"]
        if self.extension:
            source_path += f".{self.extension}"
        return make_response(
            publish_string(
                _decoded_data(self.paste["data"]),
                source_path=source_path,
                parser=parser,
                writer="html5",
                settings_overrides={"stylesheet_path": ["minimal.css"]},
            )
        )

    def _render_raw(self) -> Response:
        return Response(
            self.paste["data"],
            mimetype=_guess_mime(request.url) if self.extension else self.paste["mime"],
        )

    def _render_redirect(self) -> flask.typing.ResponseReturnValue:
        if self.extension:
            abort(400, "Extensions are not supported for redirects.")
        return redirect(_decoded_data(self.paste["data"]), 302)

    def _render_text(self) -> str:
        extension = self.extension or _guess_extension(self.paste["mime"])
        return render_template(
            "editor.html.jinja", url=f"/{self.paste['hashid']}.{extension}"
        )

    def _renderer_for_mode(
        self,
        mode: str,
    ) -> Callable[..., flask.typing.ResponseReturnValue]:
        def _wrapped_renderer(
            renderer: Callable[..., flask.typing.ResponseReturnValue],
        ) -> Callable[..., flask.typing.ResponseReturnValue]:
            if mode == "redirect":
                return renderer

            def _render_unless_unmodified(
                **kwargs: object,
            ) -> Response:
                etag = _etag(
                    self.paste,
                    self.extension or _guess_extension(self.paste["mime"]),
                    mode,
                )
                response = make_response(
                    Response(status=304)
                    if request.if_none_match.contains_weak(etag)
                    else renderer(**kwargs)
                )
                response.set_etag(etag)
                return response

            return _render_unless_unmodified

        try:
            renderer = {
                "cast": self._render_asciicast,
                "md": functools.partial(self._render_docutils, parser="markdown"),
                "raw": self._render_raw,
                "redirect": self._render_redirect,
                "rst": functools.partial(
                    self._render_docutils, parser="restructuredtext"
                ),
                "text": self._render_text,
                "txt": self._render_text,  # legacy
            }[mode]
        except KeyError as exc:
            abort(400, f"{exc} is not a recognized rendering mode.")

        # https://github.com/python/mypy/issues/17478
        return _wrapped_renderer(renderer)  # type: ignore

    def rendered(self, mode: str) -> flask.typing.ResponseReturnValue:
        return self._renderer_for_mode(mode or _mode_for_mime(self.paste["mime"]))()


@blueprint.post("/")
def create_paste() -> tuple[dict[str, str], int]:
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
        suffix = ""
        if extension:
            suffix += f".{extension}"
        if mode:
            suffix += f"/{mode}"
        elif request.path.endswith("/"):
            suffix += "/"
        if suffix:
            return _redirect(f"/{hashid}{suffix}", 301)
    elif extension == "asciinema":
        # .asciinema is a legacy pbnh thing...
        # asciinema used to use .json (application/asciicast+json),
        # and now it uses .cast (application/x-asciicast).
        return _redirect(f"/{hashid}/cast", 301)
    return _RenderRequest(paste=paste, extension=extension).rendered("raw")


@blueprint.get("/<string:hashid>")
@blueprint.get("/<string:hashid>/<string:mode>")
@blueprint.get("/<string:hashid>.<string:extension>/<string:mode>")
def render_paste(
    hashid: str, extension: str = "", mode: str = ""
) -> flask.typing.ResponseReturnValue:
    """Render a paste."""
    return _RenderRequest(paste=_get_paste(hashid), extension=extension).rendered(mode)


@blueprint.get("/<string:hashid>/")
@blueprint.get("/<string:hashid>.<string:extension>/")
def redirect_to_mode(
    hashid: str, extension: str = ""
) -> flask.typing.ResponseReturnValue:
    """Redirect to a URL with an explicit mode."""
    paste = _get_paste(hashid)
    mime = _guess_mime(request.url) if extension else paste["mime"]
    mode = _mode_for_mime(mime)
    return _redirect(request.path + mode, 302)

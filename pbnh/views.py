from datetime import datetime, timezone, timedelta
import json
import mimetypes
from pathlib import Path
from typing import Any, Callable

from docutils.core import publish_parts
from flask import (
    abort,
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    Response,
)
import flask.typing

from pbnh import db


blueprint = Blueprint("views", __name__)
REDIRECT_MIME = "text/x.pbnh.redirect"


def _decoded_data(data: bytes, *, encoding: str = "utf-8") -> str:
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        abort(422, f"The paste cannot be decoded as text ({exc}).")


def _get_paste(hashid: str) -> dict[str, Any]:
    with db.paster_context() as paster:
        return paster.query(hashid=hashid) or abort(404)


def _guess_mime(url: str) -> str | None:
    return mimetypes.guess_type(url, strict=False)[0] or {
        ".cast": "application/x-asciicast",
        ".rst": "text/x-rst",  # https://github.com/python/cpython/issues/101137
    }.get(Path(url).suffix)


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


def _render_asciicast(*, hashid: str, extension: str = "", **_: Any) -> str:
    if not extension:
        extension = "cast"
    # Prepare query params such that
    # {{params|tojson}} produces a valid JS object:
    params = {}
    for key, value in request.args.items():
        try:
            params[key] = json.loads(value)
        except json.JSONDecodeError:
            params[key] = str(value)
    return render_template(
        "asciinema.html.jinja", url=f"/{hashid}.{extension}", params=params
    )


def _render_markdown(*, hashid: str, extension: str = "", **_: Any) -> str:
    if not extension:
        extension = "md"
    return render_template("markdown.html.jinja", url=f"/{hashid}.{extension}")


def _render_raw(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    **_: Any,
) -> Response:
    mime = ""
    if extension:
        mime = _guess_mime(f"/{hashid}.{extension}") or abort(
            400,
            "There is no media type associated with"
            f" the provided extension (.{extension}).",
        )
    if not paste:
        paste = _get_paste(hashid)
    return Response(paste["data"], mimetype=mime or paste["mime"])


def _render_redirect(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    **_: Any,
) -> flask.typing.ResponseReturnValue:
    if extension:
        abort(400, "Extensions are not supported for redirects.")
    if not paste:
        paste = _get_paste(hashid)
    return redirect(_decoded_data(paste["data"]), 302)


def _render_restructuredtext(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    **_: Any,
) -> Response:
    if extension:
        abort(400, "Extensions are not supported for reStructedText rendering.")
    if not paste:
        paste = _get_paste(hashid)
    return Response(
        publish_parts(_decoded_data(paste["data"]), writer_name="html")["html_body"]
    )


def _render_text(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    **_: Any,
) -> str:
    if not paste:
        paste = _get_paste(hashid)
    if extension:
        mime = _guess_mime(f"/{hashid}.{extension}") or extension
    else:
        mime = paste["mime"]
        extension = (mimetypes.guess_extension(mime, strict=False) or "")[1:] or mime
    return render_template(
        "paste.html.jinja",
        paste=_decoded_data(paste["data"]),
        mime=mime,
        extension=extension,
    )


def _renderer_for_mode(
    mode: str,
) -> Callable[..., flask.typing.ResponseReturnValue]:
    try:
        # https://github.com/python/mypy/issues/12053
        return {  # type: ignore
            "cast": _render_asciicast,
            "md": _render_markdown,
            "raw": _render_raw,
            "redirect": _render_redirect,
            "rst": _render_restructuredtext,
            "text": _render_text,
            "txt": _render_text,  # legacy
        }[mode]
    except KeyError as exc:
        abort(400, f"{exc} is not a recognized rendering mode.")


@blueprint.get("/")
def index() -> str:
    return render_template("index.html.jinja")


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


@blueprint.get("/about")
@blueprint.get("/about.md")
def about() -> flask.typing.ResponseReturnValue:
    if str(request.url_rule) == "/about.md":
        # /about used to be /about.md:
        return redirect("/about", 301)
    return render_template(
        "markdown.html.jinja", url=f"{current_app.static_url_path}/about.md"
    )


@blueprint.get("/<string:hashid>/")
@blueprint.get("/<string:hashid>.<string:extension>/")
def redirect_to_mode(
    hashid: str, extension: str = ""
) -> flask.typing.ResponseReturnValue:
    if extension:
        return redirect(f"/{hashid}.{extension}/raw", 301)
    paste = _get_paste(hashid)
    mode = _mode_for_mime(paste["mime"])
    return redirect(f"/{hashid}/{mode}", 301)


@blueprint.get("/<string:hashid>.")
@blueprint.get("/<string:hashid>./<string:mode>")
def redirect_to_raw(hashid: str, mode: str = "") -> flask.typing.ResponseReturnValue:
    paste = _get_paste(hashid)
    suffix = mimetypes.guess_extension(paste["mime"], strict=False) or abort(
        422,
        "There is no extension associated with"
        f" the paste's media type ({paste['mime']}).",
    )
    location = f"/{hashid}{suffix}"
    if mode:
        location += f"/{mode}"
    return redirect(location, 301)


@blueprint.get("/<string:hashid>")
@blueprint.get("/<string:hashid>/<string:mode>")
@blueprint.get("/<string:hashid>.<string:extension>")
@blueprint.get("/<string:hashid>.<string:extension>/<string:mode>")
def view_paste(
    hashid: str, extension: str = "", mode: str = ""
) -> flask.typing.ResponseReturnValue:
    if mode:
        renderer = _renderer_for_mode(mode)
        return renderer(hashid=hashid, extension=extension)
    if extension:
        if extension == "asciinema":
            # .asciinema is a legacy pbnh thing...
            # asciinema used to use .json (application/asciicast+json),
            # and now it uses .cast (application/x-asciicast).
            return redirect(request.url.replace(".asciinema", "/cast"), 301)
        return _render_raw(hashid=hashid, extension=extension)
    paste = _get_paste(hashid)
    renderer = _renderer_for_mode(_mode_for_mime(paste["mime"]))
    return renderer(hashid=hashid, extension=extension, paste=paste)


@blueprint.errorhandler(404)
def fourohfour(error: Exception) -> tuple[str, int]:
    return render_template("404.html.jinja"), 404

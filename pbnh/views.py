import functools
import json
import mimetypes
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import flask.typing
from docutils.core import publish_string
from flask import Blueprint, Response, abort, redirect, render_template, request

from pbnh import db

blueprint = Blueprint("views", __name__)
REDIRECT_MIME = "text/x.pbnh.redirect"


def _decoded_data(data: bytes, *, encoding: str = "utf-8") -> str:
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        abort(422, f"The paste cannot be decoded as text ({exc}).")


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


def _guess_mime(url: str) -> str | None:
    return mimetypes.guess_type(url, strict=False)[0] or {
        ".cast": "application/x-asciicast",
        ".rst": "text/x-rst",  # https://github.com/python/cpython/issues/101137
    }.get(Path(urllib.parse.urlsplit(url).path).suffix)


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


def _render_asciicast(*, hashid: str, extension: str = "", **_: object) -> str:
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
    params.setdefault("preload", True)
    return render_template(
        "asciinema.html.jinja", url=f"/{hashid}.{extension}", params=params
    )


def _render_docutils(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    parser: str,
    **_: object,
) -> Response:
    if not paste:
        paste = _get_paste(hashid)
    source_path = hashid
    if extension:
        source_path += f".{extension}"
    return Response(
        publish_string(
            _decoded_data(paste["data"]),
            source_path=source_path,
            parser=parser,
            writer="html5",
            settings_overrides={"stylesheet_path": ["minimal.css"]},
        )
    )


def _render_raw(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    **_: object,
) -> Response:
    if not paste:
        paste = _get_paste(hashid)
    mime = _guess_mime(request.url) if extension else paste["mime"]
    return Response(paste["data"], mimetype=mime or "")


def _render_redirect(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    **_: object,
) -> flask.typing.ResponseReturnValue:
    if extension:
        abort(400, "Extensions are not supported for redirects.")
    if not paste:
        paste = _get_paste(hashid)
    return redirect(_decoded_data(paste["data"]), 302)


def _render_text(
    *,
    hashid: str,
    extension: str = "",
    paste: dict[str, Any] | None = None,
    **_: object,
) -> str:
    if not extension:
        mime = (paste or _get_paste(hashid))["mime"]
        extension = (mimetypes.guess_extension(mime, strict=False) or "")[1:]
    return render_template("editor.html.jinja", url=f"/{hashid}.{extension}")


def _renderer_for_mode(
    mode: str,
) -> Callable[..., flask.typing.ResponseReturnValue]:
    try:
        # https://github.com/python/mypy/issues/12053
        return {  # type: ignore
            "cast": _render_asciicast,
            "md": functools.partial(_render_docutils, parser="markdown"),
            "raw": _render_raw,
            "redirect": _render_redirect,
            "rst": functools.partial(_render_docutils, parser="restructuredtext"),
            "text": _render_text,
            "txt": _render_text,  # legacy
        }[mode]
    except KeyError as exc:
        abort(400, f"{exc} is not a recognized rendering mode.")


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
@blueprint.get("/<string:hashid>./<string:mode>")
@blueprint.get("/<string:hashid>.<string:extension>")
def retrieve_paste(
    hashid: str, extension: str = "", mode: str = ""
) -> flask.typing.ResponseReturnValue:
    """Retrieve a paste."""
    paste = _get_paste(hashid)
    if not extension:
        suffix = mimetypes.guess_extension(paste["mime"], strict=False) or ""
        if mode:
            suffix += f"/{mode}"
        if suffix:
            return _redirect(f"/{hashid}{suffix}", 301)
    elif extension == "asciinema":
        # .asciinema is a legacy pbnh thing...
        # asciinema used to use .json (application/asciicast+json),
        # and now it uses .cast (application/x-asciicast).
        return _redirect(f"/{hashid}/cast", 301)
    return _render_raw(hashid=hashid, extension=extension, paste=paste)


@blueprint.get("/<string:hashid>")
@blueprint.get("/<string:hashid>/<string:mode>")
@blueprint.get("/<string:hashid>.<string:extension>/<string:mode>")
def render_paste(
    hashid: str, extension: str = "", mode: str = ""
) -> flask.typing.ResponseReturnValue:
    """Render a paste."""
    paste = None
    if not mode:
        paste = _get_paste(hashid)
        mode = _mode_for_mime(paste["mime"])
    renderer = _renderer_for_mode(mode)
    return renderer(hashid=hashid, extension=extension, paste=paste)


@blueprint.get("/<string:hashid>/")
@blueprint.get("/<string:hashid>.<string:extension>/")
def redirect_to_mode(
    hashid: str, extension: str = ""
) -> flask.typing.ResponseReturnValue:
    """Redirect to a URL with an explicit mode."""
    paste = _get_paste(hashid)
    mime = (_guess_mime(request.url) or "") if extension else paste["mime"]
    mode = _mode_for_mime(mime)
    return _redirect(request.path + mode, 302)

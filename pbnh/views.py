from datetime import datetime, timezone, timedelta
import io
import json
import mimetypes
from pathlib import Path
from typing import Any

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


@blueprint.get("/")
def index() -> str:
    return render_template("index.html")


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
def about() -> str:
    return render_template(
        "markdown.html", url=f"{current_app.static_url_path}/about.md"
    )


def _rendered(paste: dict[str, Any], mime: str) -> Response | str:
    if mime.startswith("text/"):
        try:
            text = paste["data"].decode("utf-8")
        except UnicodeDecodeError as exc:
            abort(422, f"The paste cannot be decoded as text ({exc}).")
        if mime == "text/markdown":
            return render_template("markdown.html", url=f"/{paste['hashid']}.md")
        if mime in {"text/x-rst", "text/prs.fallenstein.rst"}:
            # https://github.com/python/cpython/issues/101137
            return Response(publish_parts(text, writer_name="html")["html_body"])
        return render_template("paste.html", paste=text, mime=mime)
    if mime in {"application/asciicast+json", "application/x-asciicast"}:
        # Prepare query params such that
        # {{params|tojson}} produces a valid JS object:
        params = {}
        for key, value in request.args.items():
            try:
                params[key] = json.loads(value)
            except json.JSONDecodeError:
                params[key] = str(value)
        return render_template(
            "asciinema.html",
            pasteid=paste["hashid"],
            params=params,
        )
    return Response(io.BytesIO(paste["data"]), mimetype=mime)


@blueprint.get("/<string:hashid>")
def view_paste(hashid: str) -> flask.typing.ResponseReturnValue | str:
    """Render according to the MIME type."""
    with db.paster_context() as paster:
        paste = paster.query(hashid=hashid) or abort(404)
    if paste["mime"] in {REDIRECT_MIME, "redirect"}:
        return redirect(paste["data"].decode("utf-8"), 302)
    return _rendered(paste, paste["mime"])


def _guess_type(url: str) -> str:
    suffix = Path(url).suffix
    return (
        mimetypes.guess_type(url, strict=False)[0]
        or {
            ".cast": "application/x-asciicast",
            ".rst": "text/x-rst",
        }.get(suffix)
        or abort(
            422,
            "There is no media type associated with"
            f" the provided extension ({suffix[1:]}).",
        )
    )


@blueprint.get("/<string:hashid>.")
@blueprint.get("/<string:hashid>.<string:extension>")
def view_paste_with_extension(
    hashid: str, extension: str = ""
) -> flask.typing.ResponseReturnValue:
    """Let the browser handle rendering."""
    if hashid == "about" and extension == "md":
        # /about used to be /about.md:
        return redirect("/about", 301)
    if extension == "asciinema":
        # .asciinema is a legacy pbnh thing...
        # asciinema used to use .json (application/asciicast+json),
        # and now it uses .cast (application/x-asciicast).
        return redirect(f"/{hashid}/cast", 301)
    with db.paster_context() as paster:
        paste = paster.query(hashid=hashid) or abort(404)
    if not extension:
        # The user didn't provide an extension. Try to guess it...
        extension = (mimetypes.guess_extension(paste["mime"], strict=False) or "")[1:]
        if extension:
            return redirect(f"/{hashid}.{extension}", 301)
        # No dice, send them to the base paste page
        # (which will probably just return the raw bytes).
        return redirect(f"/{hashid}", 302)
    return Response(
        io.BytesIO(paste["data"]),
        # Response will default to text/html
        # (which is not what the user asked for),
        # so fail if the type cannot be guessed:
        mimetype=_guess_type(request.url),
    )


@blueprint.get("/<string:hashid>/")
@blueprint.get("/<string:hashid>/<string:extension>")
def view_paste_with_highlighting(
    hashid: str, extension: str = ""
) -> Response | flask.typing.ResponseReturnValue | str:
    """Render as a requested type."""
    with db.paster_context() as paster:
        paste = paster.query(hashid=hashid) or abort(404)
    if not extension:
        # The user didn't provide an extension. Try to guess it...
        extension = (mimetypes.guess_extension(paste["mime"], strict=False) or "")[1:]
        if extension:
            return redirect(f"/{hashid}/{extension}", 301)
        # No dice, send them to the base paste page
        # (which will probably just return the raw bytes).
        return redirect(f"/{hashid}", 302)
    return _rendered(paste, _guess_type(f"{hashid}.{extension}"))


@blueprint.errorhandler(404)
def fourohfour(error: Exception) -> tuple[str, int]:
    return render_template("404.html"), 404

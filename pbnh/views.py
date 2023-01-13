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
import magic

from pbnh import db


blueprint = Blueprint("views", __name__)
REDIRECT_MIME = "redirect"  # TODO should probably be "text/x.redirect"
# https://datatracker.ietf.org/doc/html/rfc6838#section-3.4
# https://en.wikipedia.org/wiki/Media_type#Unregistered_tree


@blueprint.get("/")
def index():
    return render_template("index.html")


@blueprint.post("/")
def create_paste() -> tuple[dict[str, str], int]:
    """Create a new paste."""
    # Calculate the expiration.
    try:
        sunset = (request.date or datetime.now(timezone.utc)) + timedelta(
            seconds=int(request.form["sunset"])
        )
    except KeyError:
        sunset = None
    except ValueError:
        abort(400)

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
        abort(400)  # TODO description="redirect/r or content/c not set"

    # Create the paste.
    with db.paster_context() as paster:
        paste = paster.create(
            data,
            mime=mime or magic.from_buffer(data, mime=True),
            # If the request was forwarded from a reverse proxy (e.g. nginx)
            # request.remote_addr is the proxy, not the client:
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            sunset=sunset,
        )

    # Return the paste.
    paste["link"] = request.url + paste["hashid"]
    return paste, 201


@blueprint.get("/about.md")
def about() -> str:
    with open(Path(current_app.static_folder or "static") / "about.md") as about_f:
        return render_template("markdown.html", paste=about_f.read())


def _rendered(paste: dict[str, Any], mime: str) -> Response | str:
    if mime.startswith("text/"):
        try:
            text = paste["data"].decode("utf-8")
        except UnicodeDecodeError:
            # TODO move abort out
            abort(422)  # https://datatracker.ietf.org/doc/html/rfc4918#section-11.2
        if mime == "text/markdown":
            return render_template("markdown.html", paste=text)
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
def view_paste(hashid: str) -> Response | str:
    """Render according to the MIME type."""
    with db.paster_context() as paster:
        paste = paster.query(hashid=hashid) or abort(404)
    if paste["mime"] == REDIRECT_MIME:
        return redirect(paste["data"].decode("utf-8"), 302)
    return _rendered(paste, paste["mime"])


def _guess_type(url: str) -> None | str:
    return mimetypes.guess_type(url, strict=False)[0] or {
        ".cast": "application/x-asciicast",
        ".rst": "text/x-rst",
    }.get(Path(url).suffix)


@blueprint.get("/<string:hashid>.<string:extension>")  # TODO GET /<hashid>.
def view_paste_with_extension(hashid: str, extension: str) -> Response:
    """Let the browser handle rendering."""
    if extension == "asciinema":
        # .asciinema is a legacy pbnh thing...
        # asciinema used to use .json (application/asciicast+json),
        # and now it uses .cast (application/x-asciicast).
        return redirect(f"/{hashid}/cast", 301)
    with db.paster_context() as paster:
        paste = paster.query(hashid=hashid) or abort(404)
    return Response(
        io.BytesIO(paste["data"]),
        # Response will default to text/html
        # (which is not what the user asked for),
        # so fail if the type cannot be guessed:
        mimetype=_guess_type(request.url) or abort(422),
    )


@blueprint.get("/<string:hashid>/<string:extension>")
def view_paste_with_highlighting(hashid: str, extension: str) -> Response | str:
    """Render as a requested type."""
    with db.paster_context() as paster:
        paste = paster.query(hashid=hashid) or abort(404)
    return _rendered(paste, _guess_type(f"{hashid}.{extension}") or abort(422))


@blueprint.errorhandler(404)
def fourohfour(e=None):
    return render_template("404.html"), 404

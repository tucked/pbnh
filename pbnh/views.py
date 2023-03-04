from datetime import datetime, timedelta, timezone
import io
import json
import mimetypes
import os.path

from docutils.core import publish_parts
from flask import (
    abort,
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    Response,
    send_file,
    send_from_directory,
)
import magic
from werkzeug.datastructures import FileStorage

from pbnh import db


def getMime(data=None, mimestr=None):
    if mimestr:
        return mimetypes.guess_type("file.{0}".format(mimestr))[0]
    elif data:
        return magic.from_buffer(data, mime=True)
    return "text/plain"


blueprint = Blueprint("views", __name__)


@blueprint.route("/", methods=["GET"])
def hello():
    return render_template("index.html")


@blueprint.route("/about.md", methods=["GET"])
def about():
    with open(os.path.join(current_app.static_folder, "about.md"), "r") as aboutfile:
        data = aboutfile.read()
    return render_template("markdown.html", paste=data)


@blueprint.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)


@blueprint.route("/", methods=["POST"])
def post_paste():
    if request.headers.getlist("X-Forwarded-For"):
        addr = request.headers.getlist("X-Forwarded-For")[0]
    else:
        addr = request.remote_addr

    # Calculate the expiration.
    try:
        sunset = (request.date or datetime.now(timezone.utc)) + timedelta(
            seconds=int(request.form["sunset"])
        )
    except KeyError:
        sunset = None
    except ValueError:
        abort(400)

    mimestr = request.form.get("mime")
    redirectstr = request.form.get("r") or request.form.get("redirect")
    if redirectstr:
        with db.paster_context() as pstr:
            j = pstr.create(
                redirectstr.encode("utf-8"), mime="redirect", ip=addr, sunset=sunset
            )
        if j:
            if isinstance(j, str):
                return j
            j["link"] = request.url + str(j.get("hashid"))
        return json.dumps(j), 201
    inputstr = request.form.get("content") or request.form.get("c")
    # we got string data
    if inputstr and isinstance(inputstr, str):
        with db.paster_context() as pstr:
            j = pstr.create(
                inputstr.encode("utf-8"), mime=mimestr, ip=addr, sunset=sunset
            )
        if j:
            j["link"] = request.url + str(j.get("hashid"))
        return json.dumps(j), 201
    files = request.files.get("content") or request.files.get("c")
    # we got file data
    if files and isinstance(files, FileStorage):
        data = files.stream.read()
        mime = getMime(data=data, mimestr=mimestr)
        with db.paster_context() as pstr:
            j = pstr.create(data, mime=mime, ip=addr, sunset=sunset)
        if j:
            if isinstance(j, str):
                return j
            j["link"] = request.url + str(j.get("hashid"))
        return json.dumps(j), 201
    abort(400)


@blueprint.route("/<string:paste_id>", methods=["GET"])
def view_paste(paste_id):
    """
    If there are no extensions or slashes check if the mimetype is text, if it
    is text attempt to highlight it. If not return the data and set the
    mimetype so the browser can attempt to render it.
    """
    with db.paster_context() as pstr:
        try:
            query = pstr.query(hashid=paste_id) or abort(404)
        except ValueError:
            abort(404)
    mime = query.get("mime")
    data = query.get("data")
    if mime == "redirect":
        return redirect(data.decode("utf-8"), code=302)
    if mime.startswith("text/"):
        return render_template("paste.html", paste=data.decode("utf-8"), mime=mime)
    else:
        data = io.BytesIO(query.get("data"))
        return send_file(data, mimetype=mime)


@blueprint.route("/<string:paste_id>.<string:filetype>")
def view_paste_with_extension(paste_id, filetype):
    with db.paster_context() as pstr:
        try:
            query = pstr.query(hashid=paste_id)
        except ValueError:
            abort(404)
    if filetype == "md":
        data = query.get("data").decode("utf-8")
        return render_template("markdown.html", paste=data)
    if filetype == "rst":
        data = query.get("data").decode("utf-8")
        return Response(publish_parts(data, writer_name="html")["html_body"])
    if filetype == "asciinema":
        # Prepare query params such that
        # {{params|tojson}} produces a valid JS object:
        params = {}
        for key, value in request.args.to_dict().items():
            try:
                params[key] = json.loads(value)
            except json.JSONDecodeError:
                params[key] = str(value)
        return render_template(
            "asciinema.html",
            pasteid=paste_id,
            params=params,
        )
    data = io.BytesIO(query.get("data"))
    mime = getMime(mimestr=filetype)
    return Response(data, mimetype=mime)


@blueprint.route("/<string:paste_id>/<string:filetype>")
def view_paste_with_highlighting(paste_id, filetype):
    if not filetype:
        filetype = "txt"
    with db.paster_context() as pstr:
        try:
            query = pstr.query(hashid=paste_id)
        except ValueError:
            abort(404)
    return render_template(
        "paste.html", paste=query["data"].decode("utf-8"), mime=filetype
    )


@blueprint.route("/error")
@blueprint.errorhandler(404)
def fourohfour(e=None):
    return render_template("404.html"), 404

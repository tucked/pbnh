import io
import magic
import mimetypes
import tempfile

from flask import current_app

from pbnh.db import Paster
from datetime import datetime, timezone, timedelta


def fileData(files, addr=None, sunset=None, mimestr=None):
    try:
        buf = files.stream
        if (
            buf
            and isinstance(buf, io.BytesIO)
            or isinstance(buf, io.BufferedRandom)
            or isinstance(buf, tempfile.SpooledTemporaryFile)
        ):
            data = buf.read()
            mime = getMime(data=data, mimestr=mimestr)
            with Paster(current_app.config["SQLALCHEMY_DATABASE_URI"]) as pstr:
                j = pstr.create(data, mime=mime, ip=addr, sunset=sunset)
                return j
    except IOError as e:
        return "caught exception in filedata" + str(e)
    return "File save error"


def stringData(inputstr, addr=None, sunset=None, mime=None):
    with Paster(current_app.config["SQLALCHEMY_DATABASE_URI"]) as pstr:
        j = pstr.create(inputstr.encode("utf-8"), mime=mime, ip=addr, sunset=sunset)
        return j
    return "String save error"


def getSunsetFromStr(sunsetstr):
    if sunsetstr:
        try:
            plustime = int(sunsetstr)
            return datetime.now(timezone.utc) + timedelta(seconds=plustime)
        except ValueError:
            return None
    return None


def getMime(data=None, mimestr=None):
    if mimestr:
        return mimetypes.guess_type("file.{0}".format(mimestr))[0]
    elif data:
        return magic.from_buffer(data, mime=True)
    return "text/plain"


def getPaste(paste_id):
    with Paster(current_app.config["SQLALCHEMY_DATABASE_URI"]) as pstr:
        try:
            return pstr.query(hashid=paste_id)
        except ValueError:
            return None
    return None

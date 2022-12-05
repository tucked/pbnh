import io
import magic
import mimetypes
import tempfile

from pbnh.db import paste
from pbnh.app import app
from datetime import datetime, timezone, timedelta


def getConfig():
    if app.config.get("CONFIG"):
        return app.config.get("CONFIG").get("database")
    else:
        return conf.get_config().get("database")


def fileData(files, addr=None, sunset=None, mimestr=None):
    config = getConfig()
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
            with paste.Paster(
                dialect=config.get("dialect"),
                dbname=config.get("dbname"),
                driver=config.get("driver"),
                host=config.get("host"),
                password=config.get("password"),
                port=config.get("port"),
                username=config.get("username"),
            ) as pstr:
                j = pstr.create(data, mime=mime, ip=addr, sunset=sunset)
                return j
    except IOError as e:
        return "caught exception in filedata" + str(e)
    return "File save error"


def stringData(inputstr, addr=None, sunset=None, mime=None):
    config = getConfig()
    with paste.Paster(
        dialect=config.get("dialect"),
        dbname=config.get("dbname"),
        driver=config.get("driver"),
        host=config.get("host"),
        password=config.get("password"),
        port=config.get("port"),
        username=config.get("username"),
    ) as pstr:
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
    config = getConfig()
    with paste.Paster(
        dialect=config.get("dialect"),
        dbname=config.get("dbname"),
        driver=config.get("driver"),
        host=config.get("host"),
        password=config.get("password"),
        port=str(config.get("port")),
        username=config.get("username"),
    ) as pstr:
        try:
            return pstr.query(hashid=paste_id)
        except ValueError:
            return None
    return None

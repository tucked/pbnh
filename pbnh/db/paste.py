import hashlib
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import sessionmaker

from pbnh.db import models
from pbnh.db.connect import DBConnect


class Paster:
    def __init__(
        self,
        dialect="sqlite",
        driver=None,
        username=None,
        password=None,
        host=None,
        port=None,
        dbname="pastedb",
    ):
        """Grab connection information to pass to DBConnect"""
        self.dialect = dialect
        self.dbname = dbname
        self.driver = driver
        self.username = username
        self.password = password
        self.host = host
        self.port = port

    def __enter__(self):
        connection = DBConnect(
            dialect=self.dialect,
            driver=self.driver,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            dbname=self.dbname,
        ).connect
        if self.dialect == "postgresql":
            self.engine = create_engine(connection, pool_size=1)
        else:
            self.engine = create_engine(connection)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.session.close()
        self.engine.dispose()

    def create(self, data, ip=None, mime=None, sunset=None, timestamp=None):
        sha1 = hashlib.sha1(data).hexdigest()
        collision = self.query(hashid=sha1)
        if collision:
            pasteid = collision.get("id")
        else:
            paste = models.Paste(
                hashid=sha1,
                ip=ip,
                mime=mime,
                sunset=sunset,
                timestamp=timestamp,
                data=data,
            )
            try:
                self.session.add(paste)
                self.session.commit()
            except IntegrityError:
                pasteid = "HASH COLLISION"
                self.session.rollback()
            else:
                pasteid = paste.id
        return {"id": pasteid, "hashid": sha1}

    def query(self, id=None, hashid=None):
        result = None
        if id:
            try:
                result = (
                    self.session.query(models.Paste)
                    .filter(models.Paste.id == id)
                    .first()
                )
            except DataError:
                self.session.rollback()
                raise ValueError
        elif hashid:
            try:
                result = (
                    self.session.query(models.Paste)
                    .filter(models.Paste.hashid == hashid)
                    .first()
                )
            except DataError:
                self.session.rollback()
                raise ValueError
        else:
            return None
        if result:
            result = {
                "id": result.id,
                "hashid": result.hashid,
                "ip": result.ip,
                "mime": result.mime,
                "timestamp": result.timestamp,
                "sunset": result.sunset,
                "data": result.data,
            }

        return result

    def delete(self, id=None, hashid=None):
        if id:
            result = (
                self.session.query(models.Paste).filter(models.Paste.id == id).first()
            )
        elif hashid:
            result = (
                self.session.query(models.Paste)
                .filter(models.Paste.hashid == hashid)
                .first()
            )
        else:
            return None
        self.session.delete(result)
        self.session.commit()

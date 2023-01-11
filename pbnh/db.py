import contextlib
import hashlib

from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.sql import func

_Base = declarative_base()


class _Paste(_Base):
    """Class to define the paste table

    paste
    -------------
    id           (PK) int
    hashid       string (hash of data)
    ip           string (will be of "ip address" type in pg)
    mime         string
    timestamp    datetime
    sunset       datetime
    data         blob
    """

    __tablename__ = "paste"

    id = Column(Integer, primary_key=True)
    hashid = Column(String, nullable=False)
    ip = Column(String)
    timestamp = Column(DateTime, default=func.now())
    mime = Column(String, default="text/plain")
    sunset = Column(DateTime)
    data = Column(LargeBinary)

    __table_args__ = (UniqueConstraint("hashid", name="unique_hash"),)


class _Paster:
    def __init__(self, session, /):
        self._session = session

    def create(self, data, ip=None, mime=None, sunset=None, timestamp=None):
        hashid = hashlib.sha1(
            data,
            # If a user has the hash, we will give them the content,
            # so we do not care about the irreversibility of SHA1:
            usedforsecurity=False,
        ).hexdigest()
        paste = _Paste(
            hashid=hashid,
            ip=ip,
            mime=mime,
            sunset=sunset,
            timestamp=timestamp,
            data=data,
        )
        try:
            with self._session.begin():
                self._session.add(paste)
        except IntegrityError:
            pass  # A paste with that hashid already exists.
        # TODO Increase performance by just returning the hashid!
        #      paste.id is no longer public.
        return {
            key: value
            for key, value in self.query(hashid=hashid).items()
            if key in {"id", "hashid"}
        }

    def _query(self, *, id=None, hashid=None):
        if hashid is not None:
            if id is not None:
                raise ValueError("id and hashid are mutually exclusive.")
            filter_ = _Paste.hashid == hashid
        elif id is not None:
            filter_ = _Paste.id == id
        else:
            return None
        # Beware: This autobegins a transaction!
        return self._session.query(_Paste).filter(filter_).first()

    def query(self, *, id=None, hashid=None):
        with self._session.begin():
            result = self._query(id=id, hashid=hashid)
            if result:
                return {
                    "data": result.data,
                    "hashid": result.hashid,
                    "id": result.id,
                    "ip": result.ip,
                    "mime": result.mime,
                    "sunset": result.sunset,
                    "timestamp": result.timestamp,
                }
        return None

    def delete(self, *, id=None, hashid=None):
        with self._session.begin():
            result = self._query(id=id, hashid=hashid)
            if result:
                self._session.delete(result)


def _get_engine():
    try:
        return g.engine
    except AttributeError:
        g.engine = create_engine(current_app.config["SQLALCHEMY_DATABASE_URI"])
        return g.engine


@contextlib.contextmanager
def paster_context():
    with Session(_get_engine()) as session:
        yield _Paster(session)


def init_db():
    _Base.metadata.create_all(_get_engine())


def undo_db():
    _Paste.__table__.drop(_get_engine())

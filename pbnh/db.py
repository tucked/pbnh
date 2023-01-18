import contextlib
from datetime import datetime
import hashlib
from typing import Any, Iterator, Optional

from flask import current_app, g
import magic
from sqlalchemy import create_engine  # type: ignore
from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.engine import Engine  # type: ignore
from sqlalchemy.exc import IntegrityError  # type: ignore
from sqlalchemy.orm import declarative_base, Session  # type: ignore
from sqlalchemy.sql import func  # type: ignore

_Base = declarative_base()


class _Paste(_Base):  # type: ignore
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
    mime = Column(String, default="application/octet-stream")
    sunset = Column(DateTime)
    data = Column(LargeBinary)

    __table_args__ = (UniqueConstraint("hashid", name="unique_hash"),)


class PasteDBError(Exception):
    """There was a DB-related problem."""


class HashCollision(PasteDBError):
    """A paste could not be created because of a SHA1 collision."""


class _Paster:
    def __init__(self, session: Session, /) -> None:
        self._session = session

    def create(
        self,
        data: bytes,
        ip: Optional[str] = None,
        mime: Optional[str] = None,
        sunset: Optional[datetime] = None,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, str]:
        hashid = hashlib.sha1(
            data,
            # If a user has the hash, we will give them the content,
            # so we do not care about the irreversibility of SHA1:
            usedforsecurity=False,
        ).hexdigest()
        paste = _Paste(
            hashid=hashid,
            ip=ip,
            mime=mime or magic.from_buffer(data, mime=True),
            sunset=sunset,
            timestamp=timestamp,
            data=data,
        )
        query = None
        try:
            with self._session.begin():
                self._session.add(paste)
        except IntegrityError as exc:  # A paste with that hashid already exists.
            query = self.query(hashid=hashid) or {}
            if query["data"] != data:
                raise HashCollision(hashid) from exc
        # TODO Increase performance by just returning the hashid!
        #      paste.id is no longer public.
        return {
            key: value
            for key, value in (query or self.query(hashid=hashid) or {}).items()
            if key in {"id", "hashid"}
        }

    def _query(
        self, *, id: Optional[int] = None, hashid: Optional[str] = None
    ) -> Optional[_Paste]:
        if hashid is not None:
            if id is not None:
                raise ValueError("id and hashid are mutually exclusive.")
            filter_ = _Paste.hashid == hashid
        elif id is not None:
            filter_ = _Paste.id == id
        else:
            return None
        # Beware: This autobegins a transaction!
        return self._session.query(_Paste).filter(filter_).first()  # type: ignore

    def query(
        self, *, id: Optional[int] = None, hashid: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
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

    def delete(self, *, id: Optional[int] = None, hashid: Optional[str] = None) -> None:
        with self._session.begin():
            result = self._query(id=id, hashid=hashid)
            if result:
                self._session.delete(result)


def _get_engine() -> Engine:
    try:
        return g.engine
    except AttributeError:
        g.engine = create_engine(current_app.config["SQLALCHEMY_DATABASE_URI"])
        return g.engine


@contextlib.contextmanager
def paster_context() -> Iterator[_Paster]:
    with Session(_get_engine()) as session:
        yield _Paster(session)


def init_db() -> None:
    _Base.metadata.create_all(_get_engine())


def undo_db() -> None:
    _Paste.__table__.drop(_get_engine())

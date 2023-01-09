import argparse
import contextlib
import hashlib

from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.sql import func

Base = declarative_base()


class Paste(Base):
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
    def __init__(self, session):
        self.session = session

    def create(self, data, ip=None, mime=None, sunset=None, timestamp=None):
        sha1 = hashlib.sha1(
            data,
            # If a user has the hash, we will give them the content,
            # so we do not care about the irreversibility of SHA1:
            usedforsecurity=False,
        ).hexdigest()
        paste = Paste(
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
            self.session.rollback()
            pasteid = self.query(hashid=sha1).get("id")
        else:
            pasteid = paste.id
        return {"id": pasteid, "hashid": sha1}

    def query(self, id=None, hashid=None):
        result = None
        if id:
            try:
                result = self.session.query(Paste).filter(Paste.id == id).first()
            except DataError:
                self.session.rollback()
                raise ValueError
        elif hashid:
            try:
                result = (
                    self.session.query(Paste).filter(Paste.hashid == hashid).first()
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
            result = self.session.query(Paste).filter(Paste.id == id).first()
        elif hashid:
            result = self.session.query(Paste).filter(Paste.hashid == hashid).first()
        else:
            return None
        self.session.delete(result)
        self.session.commit()


def get_engine():
    try:
        return g.engine
    except AttributeError:
        g.engine = create_engine(current_app.config["SQLALCHEMY_DATABASE_URI"])
        return g.engine


@contextlib.contextmanager
def paster_context():
    with Session(get_engine()) as session:
        yield _Paster(session)


def init_db(engine=None):
    Base.metadata.create_all(engine or get_engine())


def undo_db(engine=None):
    Paste.__table__.drop(engine or get_engine())


def main():
    parser = argparse.ArgumentParser(description="Initialize a paste db")
    parser.add_argument(
        "url",
        default=current_app.config.get("SQLALCHEMY_DATABASE_URI"),
        help="the database url"
        " (e.g. dialect+driver://username:password@host:port/database)",
    )
    args = parser.parse_args()
    init_db(create_engine(args.url))
    print("Database initialized!")


if __name__ == "__main__":
    main()

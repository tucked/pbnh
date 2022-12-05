import argparse
import hashlib

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker
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


class Paster:
    def __init__(self, url):
        """Grab connection information to pass to DBConnect"""
        self._url = url

    def __enter__(self):
        self.engine = create_engine(self._url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.session.close()
        self.engine.dispose()

    def create(self, data, ip=None, mime=None, sunset=None, timestamp=None):
        sha1 = hashlib.sha1(
            data,
            # If a user has the hash, we will give them the content,
            # so we do not care about the irreversibility of SHA1:
            usedforsecurity=False,
        ).hexdigest()
        collision = self.query(hashid=sha1)
        if collision:
            pasteid = collision.get("id")
        else:
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
                pasteid = "HASH COLLISION"
                self.session.rollback()
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


class CreateDB:
    def __init__(self, url):
        self._url = url
        self.engine = create_engine(str(self))

    def __str__(self):
        return str(self._url)

    def create(self):
        Base.metadata.create_all(self.engine)

    def delete(self):
        Paste.__table__.drop(self.engine)


def main():
    parser = argparse.ArgumentParser(description="Initialize a paste db")
    parser.add_argument(
        "url",
        default=current_app.config.get("SQLALCHEMY_DATABASE_URI"),
        help="the database url"
        " (e.g. dialect+driver://username:password@host:port/database)",
    )
    args = parser.parse_args()
    newdb = CreateDB(args.url)
    print(newdb.create())


if __name__ == "__main__":
    main()

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


class DBConnect:
    """create db connection string"""

    def __init__(
        self,
        dialect=None,
        driver=None,
        username=None,
        password=None,
        host=None,
        port=None,
        dbname=None,
    ):
        self._connect = dialect
        if driver:
            self._connect += "+" + driver
        self._connect += "://"
        if username:
            self._connect += username
            if password:
                self._connect += ":" + password
        if host:
            self._connect += "@"
            self._connect += host
            if port:
                self._connect += ":" + str(port)
        elif dialect == "postgresql" and username:
            self._connect += "@localhost"
        if dbname:
            self._connect += "/" + dbname

    def __repr__(self):
        return self._connect

    @property
    def connect(self):
        """Connection string read-only property"""
        return self._connect


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
    def __init__(self, *args, **kwargs):
        self._dbconnect = DBConnect(*args, **kwargs)
        self.engine = create_engine(str(self))

    def __str__(self):
        return str(self._dbconnect)

    def create(self):
        Base.metadata.create_all(self.engine)

    def delete(self):
        Paste.__table__.drop(self.engine)


def main():
    config = current_app.config["CONFIG"].get("database")
    parser = argparse.ArgumentParser(description="Initialize a paste db")
    parser.add_argument(
        "-t", "--type", default=config.get("dialect"), help="sqlite or postgresql"
    )
    parser.add_argument(
        "-n",
        "--dbname",
        default=config.get("dbname"),
        help="name of the database to be created",
    )
    parser.add_argument(
        "-d",
        "--driver",
        default=config.get("driver"),
        help="database driver for sqlalchemy to use",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=config.get("username"),
        help="username to use for the database connection",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=config.get("password"),
        help="password to use for the database connection",
    )
    parser.add_argument(
        "-s", "--server", default=config.get("host"), help="host of the database"
    )
    parser.add_argument(
        "-P", "--port", default=config.get("port"), help="port the database listens on"
    )
    args = parser.parse_args()
    newdb = CreateDB(
        dialect=args.type,
        driver=args.driver,
        username=args.username,
        password=args.password,
        host=args.server,
        port=args.port,
        dbname=args.dbname,
    )
    print(newdb.create())


if __name__ == "__main__":
    main()

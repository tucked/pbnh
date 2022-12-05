from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
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

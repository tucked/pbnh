from datetime import datetime

import pytest

import pbnh.db


def test_db_config_missing(app, monkeypatch):
    key = "SQLALCHEMY_DATABASE_URI"
    monkeypatch.delitem(app.config, key)
    with app.app_context():
        with pytest.raises(pbnh.db.PasteDBError, match=f"{key}.*not set"):
            with pbnh.db.paster_context():
                pass


@pytest.mark.parametrize(
    "value",
    [
        "1*3451g/1*3/643h3i(&*^%$446",  # sqlalchemy.exc.ArgumentError
        "dialect+driver://username:password@host:port/database",  # ValueError (on port)
    ],
)
def test_db_config_unusable(app, value, monkeypatch):
    key = "SQLALCHEMY_DATABASE_URI"
    monkeypatch.setitem(app.config, key, value)
    with app.app_context():
        with pytest.raises(pbnh.db.PasteDBError, match=f"{key}.*unusable"):
            with pbnh.db.paster_context():
                pass


@pytest.fixture
def paster(app):
    with app.app_context():
        yield pbnh.db.paster_context()


def test_create_new(paster):
    with paster as p:
        assert (
            p.create(b"This is a test paste")
            == "f872a542a8289d2273f6cb455198e06126f4ec30"
        )


def test_create_dupe(paster):
    data = b"This is a test paste"
    with paster as p:
        assert p.create(data) == p.create(data)


def test_create_collision(paster):
    """Collisions cause an exception."""
    with paster as p:
        with open("tests/shattered-1.pdf", mode="rb") as f:
            hashid = p.create(f.read())
        with open("tests/shattered-2.pdf", mode="rb") as f:
            with pytest.raises(pbnh.db.HashCollision, match=f"^{hashid}$"):
                p.create(f.read())


def test_query(paster):
    data = b"This is a test paste"
    timestamp = datetime.now()
    with paster as p:
        assert p.query(hashid=p.create(data, timestamp=timestamp)) == {
            "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30",
            "ip": None,
            "mime": "text/plain",
            "sunset": None,
            "timestamp": timestamp,
            "data": b"This is a test paste",
        }


def test_query_nonexistent(paster):
    with paster as p:
        assert p.query(hashid="nonexistent") is None


def test_delete(paster):
    with paster as p:
        hashid = p.create(b"This is a test paste")
        p.delete(hashid=hashid)
        assert p.query(hashid=hashid) is None


def test_delete_nonexistent(paster):
    with paster as p:
        assert p.delete(hashid="nonexistent") is None

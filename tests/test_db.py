from datetime import datetime

import pytest

import pbnh.db


@pytest.fixture
def paster(app):
    with app.app_context():
        yield pbnh.db.paster_context()


def test_create_new(paster):
    with paster as p:
        created = p.create(b"This is a test paste")
    assert created == {"id": 1, "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30"}


def test_create_dupe(paster):
    with paster as p:
        created = p.create(b"This is a test paste")
        created = p.create(b"This is a test paste")
    assert created == {"id": 1, "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30"}


def test_query_id(paster):
    timestamp = datetime.now()
    with paster as p:
        p.create(b"This is a test paste", timestamp=timestamp)
        lookup = p.query(id=1)
    assert lookup == {
        "id": 1,
        "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30",
        "ip": None,
        "mime": "text/plain",
        "sunset": None,
        "timestamp": timestamp,
        "data": b"This is a test paste",
    }


def test_query_hash(paster):
    timestamp = datetime.now()
    with paster as p:
        p.create(b"This is a test paste", timestamp=timestamp)
        lookup = p.query(hashid="f872a542a8289d2273f6cb455198e06126f4ec30")
    assert lookup == {
        "id": 1,
        "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30",
        "ip": None,
        "mime": "text/plain",
        "sunset": None,
        "timestamp": timestamp,
        "data": b"This is a test paste",
    }


def test_query_none(paster):
    with paster as p:
        p.create(b"This is a test paste")
        lookup = p.query()
    assert lookup is None


def test_delete_id(paster):
    with paster as p:
        p.create(b"This is a test paste")
        p.delete(id=1)
        lookup = p.query(id=1)
    assert lookup is None


def test_delete_hash(paster):
    with paster as p:
        p.create(b"This is a test paste")
        p.delete(hashid="f872a542a8289d2273f6cb455198e06126f4ec30")
        lookup = p.query(id=1)
    assert lookup is None


def test_delete_none(paster):
    timestamp = datetime.now()
    with paster as p:
        p.create(b"This is a test paste", timestamp=timestamp)
        p.delete()
        lookup = p.query(id=1)
    assert lookup == {
        "id": 1,
        "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30",
        "ip": None,
        "mime": "text/plain",
        "sunset": None,
        "timestamp": timestamp,
        "data": b"This is a test paste",
    }
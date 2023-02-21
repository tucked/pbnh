import unittest

from datetime import datetime

from pbnh import create_app
import pbnh.db
from pbnh.db import Paster


class TestPaster(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "DEBUG": True,
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///test_db.sqlite",
            }
        )
        with self.app.app_context():
            pbnh.db.init_db()
            self.paster = Paster()

    def tearDown(self):
        with self.app.app_context():
            pbnh.db.undo_db()

    def test_create_new(self):
        with self.paster as p:
            created = p.create(b"This is a test paste")
        self.assertEqual(
            created, {"id": 1, "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30"}
        )

    def test_create_dupe(self):
        with self.paster as p:
            created = p.create(b"This is a test paste")
            created = p.create(b"This is a test paste")
        self.assertEqual(
            created, {"id": 1, "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30"}
        )

    def test_query_id(self):
        timestamp = datetime.now()
        with self.paster as p:
            p.create(b"This is a test paste", timestamp=timestamp)
            lookup = p.query(id=1)
        self.assertEqual(
            lookup,
            {
                "id": 1,
                "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30",
                "ip": None,
                "mime": "text/plain",
                "sunset": None,
                "timestamp": timestamp,
                "data": b"This is a test paste",
            },
        )

    def test_query_hash(self):
        timestamp = datetime.now()
        with self.paster as p:
            p.create(b"This is a test paste", timestamp=timestamp)
            lookup = p.query(hashid="f872a542a8289d2273f6cb455198e06126f4ec30")
        self.assertEqual(
            lookup,
            {
                "id": 1,
                "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30",
                "ip": None,
                "mime": "text/plain",
                "sunset": None,
                "timestamp": timestamp,
                "data": b"This is a test paste",
            },
        )

    def test_query_disaster(self):
        with self.paster as p:
            p.create(b"This is a test paste")
            lookup = p.query(id="f872a542a8289d2273f6cb455198e06126f4ec30")
        self.assertEqual(lookup, None)

    def test_query_none(self):
        with self.paster as p:
            p.create(b"This is a test paste")
            lookup = p.query()
        self.assertEqual(lookup, None)

    def test_delete_id(self):
        with self.paster as p:
            p.create(b"This is a test paste")
            p.delete(id=1)
            lookup = p.query(id=1)
        self.assertEqual(lookup, None)

    def test_delete_hash(self):
        with self.paster as p:
            p.create(b"This is a test paste")
            p.delete(hashid="f872a542a8289d2273f6cb455198e06126f4ec30")
            lookup = p.query(id=1)
        self.assertEqual(lookup, None)

    def test_delete_none(self):
        timestamp = datetime.now()
        with self.paster as p:
            p.create(b"This is a test paste", timestamp=timestamp)
            p.delete()
            lookup = p.query(id=1)
        self.assertEqual(
            lookup,
            {
                "id": 1,
                "hashid": "f872a542a8289d2273f6cb455198e06126f4ec30",
                "ip": None,
                "mime": "text/plain",
                "sunset": None,
                "timestamp": timestamp,
                "data": b"This is a test paste",
            },
        )

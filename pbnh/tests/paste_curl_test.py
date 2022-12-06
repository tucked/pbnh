#!/usr/bin/python3
import unittest
import json
import hashlib

from pbnh import app
from pbnh.db.createdb import CreateDB
from io import BytesIO


DEFAULTS = {
    "server": {
        "bind_ip": "127.0.0.1",
        "bind_port": 8080,
        "debug": True,
    },
    "database": {
        "dbname": "pastedb",
        "dialect": "sqlite",
        "driver": None,
        "host": None,
        "password": None,
        "port": None,
        "username": None,
    },
}


class TestPost(unittest.TestCase):
    def setUp(self):
        self.newdb = CreateDB(
            dialect=DEFAULTS["database"]["dialect"],
            dbname=DEFAULTS["database"]["dbname"],
        )
        self.newdb.create()
        app.app.config["CONFIG"] = DEFAULTS
        self.app = app.app.test_client()

    def tearDown(self):
        self.newdb.delete()

    def test_home(self):
        response = self.app.get("/")
        self.assertEqual(response.status_code, 200)

    def test_about(self):
        return
        response = self.app.get("/about.md")
        self.assertEqual(response.status_code, 200)

    def test_nopaste(self):
        response = self.app.get("/1")
        self.assertEqual(response.status_code, 404)

    def test_paste_string_c(self):
        response = self.app.post("/", data={"c": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        self.failUnlessEqual(
            j.get("hashid"), "a9993e364706816aba3e25717850c26c9cd0d89d"
        )
        self.assertEqual(response.status_code, 201)
        response = self.app.get("/1")
        self.assertEqual(response.status_code, 200)

    def test_paste_string_content(self):
        response = self.app.post("/", data={"content": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        self.failUnlessEqual(
            j.get("hashid"), "a9993e364706816aba3e25717850c26c9cd0d89d"
        )
        self.assertEqual(response.status_code, 201)
        response = self.app.get("/1")
        self.assertEqual(response.status_code, 200)

    def test_redirect(self):
        response = self.app.post("/", data={"r": "http://www.google.com"})
        j = json.loads(response.data.decode("utf-8"))
        self.failUnlessEqual(
            j.get("hashid"), "738ddf35b3a85a7a6ba7b232bd3d5f1e4d284ad1"
        )
        self.assertEqual(response.status_code, 201)

    def test_follow_redirect(self):
        url = DEFAULTS["server"]["bind_ip"] + ":" + str(DEFAULTS["server"]["bind_port"])
        hashid = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()
        response = self.app.post("/", data={"r": url})
        j = json.loads(response.data.decode("utf-8"))
        self.failUnlessEqual(j.get("hashid"), hashid)
        response = self.app.get("/1")
        self.assertEqual(response.status_code, 302)

    def test_paste_file_c(self):
        response = self.app.post("/", data={"c": (BytesIO(b"contents"), "test")})
        self.assertEqual(response.status_code, 201)
        j = json.loads(response.data.decode("utf-8"))
        self.failUnlessEqual(
            j.get("hashid"), "4a756ca07e9487f482465a99e8286abc86ba4dc7"
        )

    def test_paste_file_content(self):
        response = self.app.post("/", data={"content": (BytesIO(b"contents"), "test")})
        self.assertEqual(response.status_code, 201)
        j = json.loads(response.data.decode("utf-8"))
        self.failUnlessEqual(
            j.get("hashid"), "4a756ca07e9487f482465a99e8286abc86ba4dc7"
        )

    def test_paste_extension(self):
        response = self.app.post("/", data={"content": "abc"})
        response = self.app.get("/1.txt")
        self.assertEqual(response.status_code, 200)

    def test_paste_highlight(self):
        response = self.app.post("/", data={"content": "abc"})
        response = self.app.get("/1/txt")
        self.assertEqual(response.status_code, 200)

    def test_paste_not_text(self):
        response = self.app.post(
            "/", data={"content": (BytesIO(b"contents"), "test"), "mime": "pdf"}
        )
        self.assertEqual(response.status_code, 201)
        j = json.loads(response.data.decode("utf-8"))
        self.failUnlessEqual(
            j.get("hashid"), "4a756ca07e9487f482465a99e8286abc86ba4dc7"
        )
        response = self.app.get("/1")
        self.assertEqual(response.status_code, 200)

    def test_paste_sunset(self):
        response = self.app.post(
            "/", data={"content": (BytesIO(b"contents"), "test"), "sunset": "pdf"}
        )
        response = self.app.post(
            "/", data={"content": (BytesIO(b"contents"), "test"), "sunset": "10"}
        )
        response = self.app.get("/1")
        self.assertEqual(response.status_code, 200)

    def test_get_markdown(self):
        response = self.app.post("/", data={"content": "abc"})
        response = self.app.get("/1.md")
        self.assertEqual(response.status_code, 200)

    def test_get_rst(self):
        response = self.app.post("/", data={"content": "abc"})
        response = self.app.get("/1.rst")
        self.assertEqual(response.status_code, 200)

    def test_get_asciinema(self):
        response = self.app.post("/", data={"content": "abc"})
        response = self.app.get("/1.asciinema")
        self.assertEqual(response.status_code, 200)

    def test_ip_forwarding(self):
        response = self.app.post(
            "/", environ_base={"X-Forwarded-For": "127.0.0.1"}, data={"content": "abc"}
        )
        self.assertEqual(response.status_code, 201)

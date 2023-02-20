import unittest
import json
import hashlib

from pbnh.app import create_app
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
        self.app = create_app({"CONFIG": DEFAULTS})
        self.newdb = CreateDB(**self.app.config["CONFIG"]["database"])
        self.newdb.create()
        self.test_client = self.app.test_client()

    def tearDown(self):
        self.newdb.delete()

    def test_home(self):
        response = self.test_client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_about(self):
        response = self.test_client.get("/about.md")
        self.assertEqual(response.status_code, 200)

    def test_nopaste(self):
        response = self.test_client.get("/1")
        self.assertEqual(response.status_code, 404)

    def test_paste_string_c(self):
        response = self.test_client.post("/", data={"c": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        self.assertEqual(response.status_code, 201)
        hashid = j.get("hashid")
        self.assertEqual(hashid, "a9993e364706816aba3e25717850c26c9cd0d89d")
        response = self.test_client.get(f"/{hashid}")
        self.assertEqual(response.status_code, 200)

    def test_paste_string_content(self):
        response = self.test_client.post("/", data={"content": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        self.assertEqual(response.status_code, 201)
        hashid = j.get("hashid")
        self.assertEqual(hashid, "a9993e364706816aba3e25717850c26c9cd0d89d")
        response = self.test_client.get(f"/{hashid}")
        self.assertEqual(response.status_code, 200)

    def test_redirect(self):
        response = self.test_client.post("/", data={"r": "http://www.google.com"})
        j = json.loads(response.data.decode("utf-8"))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(j.get("hashid"), "738ddf35b3a85a7a6ba7b232bd3d5f1e4d284ad1")

    def test_follow_redirect(self):
        url = DEFAULTS["server"]["bind_ip"] + ":" + str(DEFAULTS["server"]["bind_port"])
        hashid = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()
        response = self.test_client.post("/", data={"r": url})
        j = json.loads(response.data.decode("utf-8"))
        self.assertEqual(j.get("hashid"), hashid)
        response = self.test_client.get(f"/{hashid}")
        self.assertEqual(response.status_code, 302)

    def test_paste_file_c(self):
        response = self.test_client.post(
            "/", data={"c": (BytesIO(b"contents"), "test")}
        )
        self.assertEqual(response.status_code, 201)
        j = json.loads(response.data.decode("utf-8"))
        self.assertEqual(j.get("hashid"), "4a756ca07e9487f482465a99e8286abc86ba4dc7")

    def test_paste_file_content(self):
        response = self.test_client.post(
            "/", data={"content": (BytesIO(b"contents"), "test")}
        )
        self.assertEqual(response.status_code, 201)
        j = json.loads(response.data.decode("utf-8"))
        self.assertEqual(j.get("hashid"), "4a756ca07e9487f482465a99e8286abc86ba4dc7")

    def test_paste_extension(self):
        response = self.test_client.post("/", data={"content": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        hashid = j.get("hashid")
        response = self.test_client.get(f"/{hashid}.txt")
        self.assertEqual(response.status_code, 200)

    def test_paste_highlight(self):
        response = self.test_client.post("/", data={"content": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        hashid = j.get("hashid")
        response = self.test_client.get(f"/{hashid}/txt")
        self.assertEqual(response.status_code, 200)

    def test_paste_not_text(self):
        response = self.test_client.post(
            "/", data={"content": (BytesIO(b"contents"), "test"), "mime": "pdf"}
        )
        self.assertEqual(response.status_code, 201)
        j = json.loads(response.data.decode("utf-8"))
        hashid = j.get("hashid")
        self.assertEqual(hashid, "4a756ca07e9487f482465a99e8286abc86ba4dc7")
        response = self.test_client.get(f"/{hashid}")
        self.assertEqual(response.status_code, 200)

    def test_paste_sunset(self):
        response = self.test_client.post(
            "/", data={"content": (BytesIO(b"contents"), "test"), "sunset": "pdf"}
        )
        response = self.test_client.post(
            "/", data={"content": (BytesIO(b"contents"), "test"), "sunset": "10"}
        )
        j = json.loads(response.data.decode("utf-8"))
        hashid = j.get("hashid")
        response = self.test_client.get(f"/{hashid}")
        self.assertEqual(response.status_code, 200)

    def test_get_markdown(self):
        response = self.test_client.post("/", data={"content": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        hashid = j.get("hashid")
        response = self.test_client.get(f"/{hashid}.md")
        self.assertEqual(response.status_code, 200)

    def test_get_rst(self):
        response = self.test_client.post("/", data={"content": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        hashid = j.get("hashid")
        response = self.test_client.get(f"/{hashid}.rst")
        self.assertEqual(response.status_code, 200)

    def test_get_asciinema(self):
        response = self.test_client.post("/", data={"content": "abc"})
        j = json.loads(response.data.decode("utf-8"))
        hashid = j.get("hashid")
        response = self.test_client.get(f"/{hashid}.asciinema")
        self.assertEqual(response.status_code, 200)

    def test_ip_forwarding(self):
        response = self.test_client.post(
            "/", environ_base={"X-Forwarded-For": "127.0.0.1"}, data={"content": "abc"}
        )
        self.assertEqual(response.status_code, 201)

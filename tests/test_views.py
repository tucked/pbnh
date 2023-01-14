import hashlib
from io import BytesIO
import json

import pytest


@pytest.fixture
def test_client(app):
    """A test client for the app."""
    return app.test_client()


def test_home(test_client):
    response = test_client.get("/")
    assert response.status_code == 200


def test_about(test_client):
    response = test_client.get("/about.md")
    assert response.status_code == 200


def test_nopaste(test_client):
    response = test_client.get("/1")
    assert response.status_code == 404


def test_paste_string_c(test_client):
    response = test_client.post("/", data={"c": "abc"})
    j = json.loads(response.data.decode("utf-8"))
    assert response.status_code == 201
    hashid = j.get("hashid")
    assert hashid == "a9993e364706816aba3e25717850c26c9cd0d89d"
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 200


def test_paste_string_content(test_client):
    response = test_client.post("/", data={"content": "abc"})
    j = json.loads(response.data.decode("utf-8"))
    assert response.status_code == 201
    hashid = j.get("hashid")
    assert hashid == "a9993e364706816aba3e25717850c26c9cd0d89d"
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 200


def test_redirect(test_client):
    response = test_client.post("/", data={"r": "http://www.google.com"})
    j = json.loads(response.data.decode("utf-8"))
    assert response.status_code == 201
    assert j.get("hashid") == "738ddf35b3a85a7a6ba7b232bd3d5f1e4d284ad1"


def test_follow_redirect(test_client):
    url = "localhost:12345"
    hashid = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()
    response = test_client.post("/", data={"r": url})
    j = json.loads(response.data.decode("utf-8"))
    assert j.get("hashid") == hashid
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 302


def test_paste_file_c(test_client):
    response = test_client.post("/", data={"c": (BytesIO(b"contents"), "test")})
    assert response.status_code == 201
    j = json.loads(response.data.decode("utf-8"))
    assert j.get("hashid") == "4a756ca07e9487f482465a99e8286abc86ba4dc7"


def test_paste_file_content(test_client):
    response = test_client.post("/", data={"content": (BytesIO(b"contents"), "test")})
    assert response.status_code == 201
    j = json.loads(response.data.decode("utf-8"))
    assert j.get("hashid") == "4a756ca07e9487f482465a99e8286abc86ba4dc7"


def test_paste_highlight(test_client):
    response = test_client.post("/", data={"content": "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}/txt")
    assert response.status_code == 200


def test_paste_not_text(test_client):
    response = test_client.post(
        "/", data={"content": (BytesIO(b"contents"), "test"), "mime": "pdf"}
    )
    assert response.status_code == 201
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    assert hashid == "4a756ca07e9487f482465a99e8286abc86ba4dc7"
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 200


@pytest.mark.xfail(
    raises=UnicodeDecodeError, reason="Highlighting assumes data is UTF-8."
)
def test_paste_non_utf8(test_client):
    response = test_client.post("/", data={"content": (BytesIO(b"\xff"), "test")})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}/txt")
    assert response.status_code == 200


def test_paste_sunset(test_client):
    response = test_client.post(
        "/", data={"content": (BytesIO(b"contents"), "test"), "sunset": "pdf"}
    )
    response = test_client.post(
        "/", data={"content": (BytesIO(b"contents"), "test"), "sunset": "10"}
    )
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 200


@pytest.mark.parametrize("ext", ["asciinema", "md", "rst", "txt"])
def test_get_ext(test_client, ext):
    response = test_client.post("/", data={"content": "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}.{ext}")
    assert response.status_code == 200


def test_ip_forwarding(test_client):
    response = test_client.post(
        "/", environ_base={"X-Forwarded-For": "127.0.0.1"}, data={"content": "abc"}
    )
    assert response.status_code == 201

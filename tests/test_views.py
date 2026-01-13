import contextlib
import hashlib
import json
from io import BytesIO

import pytest

import pbnh
from pbnh import views


@pytest.fixture(params=["content", "c"])
def content_key(request):
    return request.param


@pytest.fixture(params=["redirect", "r"])
def redirect_key(request):
    return request.param


@pytest.fixture
def test_client(app):
    """A test client for the app."""
    return app.test_client()


def test_home(test_client):
    response = test_client.get("/")
    assert response.status_code == 200


def test_about(test_client):
    response = test_client.get("/about")
    assert response.status_code == 200


def test_about_md(test_client):
    response = test_client.get("/about.md")
    assert response.status_code == 301
    assert response.location == "/about"


def test_static(test_client):
    """Flask handles static files automatically."""
    response = test_client.get("/static/about.md")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "path", ["/nonexistent", "/nonexistent.txt", "nonexistent/txt"]
)
def test_nopaste(path, test_client):
    response = test_client.get(path)
    assert response.status_code == 404
    assert "Paste Not Found" in response.text


@pytest.mark.parametrize("mime", [{}, {"mime": "plain"}])
def test_paste_string_content(content_key, mime, test_client):
    response = test_client.post("/", data={content_key: "abc", **mime})
    j = json.loads(response.data.decode("utf-8"))
    assert response.status_code == 201
    hashid = j.get("hashid")
    assert hashid == "a9993e364706816aba3e25717850c26c9cd0d89d"
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 200


def test_paste_spoofed_x_for(app, monkeypatch):
    class DummyPaster:
        def create(self, *_, **kwargs):
            # Return the sender IP instead of the hashid
            # (so we can see it in the response).
            return kwargs["ip"]

    class DummyDB:
        @contextlib.contextmanager
        def paster_context(self, *_, **__):
            yield DummyPaster()

    monkeypatch.setattr(views, "db", DummyDB())
    spoofed_for = "8.8.8.8"

    def _returned_hashid(app):
        response = app.test_client().post(
            "/",
            data={"content": "does not matter"},
            headers={"X-Forwarded-For": spoofed_for},
        )
        return json.loads(response.data.decode("utf-8"))["hashid"]

    for x_for, hashid in {0: "127.0.0.1", 1: spoofed_for}.items():
        app.config["WERKZEUG_PROXY_FIX"] = {"x_for": x_for}
        assert _returned_hashid(pbnh.create_app(app.config)) == hashid, x_for


def test_paste_empty(test_client):
    response = test_client.post("/", data={})
    assert response.status_code == 400


@pytest.mark.parametrize(
    "url,hashid",
    [
        ("http://www.google.com", "738ddf35b3a85a7a6ba7b232bd3d5f1e4d284ad1"),
        pytest.param(
            "https://www.example.com/#" + ("x" * 4000),
            "65ce13d38a96f835251f9a374891da07d586473c",
            id="longURL",
        ),
    ],
)
def test_redirect(redirect_key, url, hashid, test_client):
    response = test_client.post("/", data={redirect_key: url})
    j = json.loads(response.data.decode("utf-8"))
    assert response.status_code == 201
    assert j.get("hashid") == hashid


@pytest.mark.parametrize("mode", ["", "/redirect"])
def test_follow_redirect(redirect_key, test_client, mode):
    url = "localhost:12345"
    hashid = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()
    response = test_client.post("/", data={redirect_key: url})
    j = json.loads(response.data.decode("utf-8"))
    assert j.get("hashid") == hashid
    response = test_client.get(f"/{hashid}{mode}")
    assert response.status_code == 302
    assert response.location == url


def test_redirect_with_extension(redirect_key, test_client):
    url = "localhost:12345"
    hashid = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()
    response = test_client.post("/", data={redirect_key: url})
    j = json.loads(response.data.decode("utf-8"))
    assert j.get("hashid") == hashid
    response = test_client.get(f"/{hashid}.foo/redirect")
    assert response.status_code == 400


def test_paste_file_content(content_key, test_client):
    response = test_client.post("/", data={content_key: (BytesIO(b"contents"), "test")})
    assert response.status_code == 201
    j = json.loads(response.data.decode("utf-8"))
    assert j.get("hashid") == "4a756ca07e9487f482465a99e8286abc86ba4dc7"


@pytest.mark.parametrize("mode", ["", "/md"])
@pytest.mark.parametrize("suffix", ["", ".md"])
def test_markdown(content_key, test_client, mode, suffix):
    response = test_client.post("/", data={content_key: "abc", "mime": "text/markdown"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}{suffix}{mode}")
    assert response.status_code == 200


@pytest.mark.parametrize("mode", ["", "/rst"])
def test_restructuredtext(content_key, test_client, mode):
    response = test_client.post("/", data={content_key: "abc", "mime": "text/x-rst"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}{mode}")
    assert response.status_code == 200


def test_restructuredtext_with_extension(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc", "mime": "text/x-rst"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}.foo/rst")
    assert response.status_code == 400


def test_bad_mode(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}/foo")
    assert response.status_code == 400


def test_no_mode_redirect(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}.txt/")
    assert response.status_code == 301


def test_raw_mode_redirect(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}./txt")
    assert response.status_code == 301


def test_text_mode_guess_type(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}.md/text")
    assert response.status_code == 200


@pytest.mark.parametrize("ext", ["md", "rst", "txt"])
def test_paste_highlight(content_key, test_client, ext):
    response = test_client.post("/", data={content_key: "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}/{ext}")
    assert response.status_code == 200


def test_paste_not_text(content_key, test_client):
    response = test_client.post(
        "/", data={content_key: (BytesIO(b"contents"), "test"), "mime": "pdf"}
    )
    assert response.status_code == 201
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    assert hashid == "4a756ca07e9487f482465a99e8286abc86ba4dc7"
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 200


def test_paste_non_utf8(content_key, test_client):
    response = test_client.post("/", data={content_key: (BytesIO(b"\xff"), "test")})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}/txt")
    assert response.status_code == 422


def test_paste_sunset(content_key, test_client):
    response = test_client.post(
        "/", data={content_key: (BytesIO(b"contents"), "test"), "sunset": "pdf"}
    )
    response = test_client.post(
        "/", data={content_key: (BytesIO(b"contents"), "test"), "sunset": "10"}
    )
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}")
    assert response.status_code == 200


def test_paste_sunset_immediately(content_key, test_client):
    response = test_client.post("/", data={content_key: b"abc", "sunset": 0})
    assert response.status_code == 400


@pytest.mark.parametrize("ext", ["cast", "md", "rst", "txt"])
def test_get_ext(content_key, test_client, ext):
    response = test_client.post("/", data={content_key: "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(f"/{hashid}.{ext}")
    assert response.status_code == 200


def test_get_asciinema(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    query_string = "theme=solarized"
    response = test_client.get(f"/{hashid}.asciinema?{query_string}")
    assert response.status_code == 301
    assert ".asciinema" not in response.location
    assert query_string in response.location


@pytest.mark.parametrize("suffix", ["", ".cast"])
@pytest.mark.parametrize("mode", ["", "/cast"])
def test_get_asciinema_params(content_key, test_client, suffix, mode):
    response = test_client.post(
        "/", data={content_key: "abc", "mime": "application/x-asciicast"}
    )
    j = json.loads(response.data.decode("utf-8"))
    hashid = j.get("hashid")
    response = test_client.get(
        f"/{hashid}{suffix}{mode}",
        query_string={
            "speed": 10,
            "theme": "solarized-light",
            "poster": "data:text/plain,Prepare to be amazed",
            "startAt": 10,
            "loop": True,
            "fit": "height",
        },
    )
    assert response.status_code == 200


def test_ip_forwarding(content_key, test_client):
    response = test_client.post(
        "/", headers={"X-Forwarded-For": "127.0.0.1"}, data={content_key: "abc"}
    )
    assert response.status_code == 201


def test_post_collision(content_key, test_client):
    with open("tests/shattered-1.pdf", mode="rb") as f:
        response = test_client.post("/", data={content_key: (f, f.name)})
    assert response.status_code == 201
    with open("tests/shattered-2.pdf", mode="rb") as f:
        response = test_client.post("/", data={content_key: (f, f.name)})
    assert response.status_code == 409


def test_get_no_extension_dot(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    hashid = response.json["hashid"]
    response = test_client.get(f"/{hashid}.")
    assert response.status_code == 301
    assert response.location == f"/{hashid}.txt"


def test_get_no_extension_slash(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    hashid = response.json["hashid"]
    response = test_client.get(f"/{hashid}/")
    assert response.status_code == 301
    assert response.location == f"/{hashid}/text"


def test_get_no_extension_unguessable_dot(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc", "mime": "fo/shizzle"})
    hashid = response.json["hashid"]
    response = test_client.get(f"/{hashid}.")
    assert response.status_code == 422


def test_get_no_extension_unguessable_slash(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc", "mime": "fo/shizzle"})
    hashid = response.json["hashid"]
    response = test_client.get(f"/{hashid}/")
    assert response.status_code == 301
    assert response.location == f"/{hashid}/raw"


def test_get_raw_content_length(content_key, test_client):
    response = test_client.post("/", data={content_key: "abc"})
    hashid = response.json["hashid"]
    response = test_client.get(f"/{hashid}/raw")
    assert "Content-Length" in response.headers

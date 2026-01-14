# About

[pbnh](https://github.com/tucked/pbnh) is a [content-addressed](https://en.wikipedia.org/wiki/Content-addressable_storage) [pastebin](https://en.wikipedia.org/wiki/Pastebin).
It supports [anonymous text/file upload](#paste-creation) of data that can then be [downloaded](#raw-retrieval) or [rendered for the Web](#web-rendering).

## Paste Creation

Pastes can be created with the Web UI (on the home page), from a CLI or shell script (e.g. using `curl`), or programmatically (e.g. using `python-requests`).

### API

Any HTTP client may `POST /` with the form inputs described below to create a new paste.

Here's an example in Python:

``` python
import requests

# Text
requests.post("http://pbnh.example.com/", data={"content": "Hello world!"})

# File
with open("/path/to/file.txt") as content_f:
    requests.post("http://pbnh.example.com/", files={"content": content_f})
```

#### `content`/`c` (required)

Associate data with the paste.

``` sh
# Text
curl --form content="Hello world!" pbnh.example.com

# File (by path)
curl --form content=@/path/to/file.txt pbnh.example.com

# File (by pipe)
fortune | curl --form content=@- pbnh.example.com
```

##### `redirect`/`r`

Replace the `content` input with one named `redirect` to create a redirect paste.
The data will be interpreted as a URI target that future clients should be redirected to.

``` sh
curl --form redirect="https://www.example.com/" pbnh.example.com
```

- Note: `redirect` causes the `content` and `mime` inputs to be ignored.

#### `mime`

Specify the [MIME type](https://www.iana.org/assignments/media-types/media-types.xhtml) of the paste's data.
If this is not set, pbnh will attempt to guess it.

``` sh
curl --form content=@/path/to/file.pdf --form mime=application/pdf pbnh.example.com
```

#### `sunset`

Mark the paste for deletion after a certain period of time (in seconds).

``` sh
curl --form content="Burn this after 10 seconds!" --form sunset=10 pbnh.example.com
```

- Note: Currently, there is no automatic mechanism for deleting pastes after their sunset.

## Raw Retrieval

If a file extension is appended to the paste ID in the requested URI (i.e. `GET /<hashid>.<extension>`),
the paste will be returned unmodified with the `Content-Type` header set to the type associated with the extension.
Append a `.` with no extension (i.e. `GET /<hashid>.`) to use the type associated with the paste.

## Web Rendering

If only the paste ID is requested (i.e. `GET /<hashid>` or `GET /<hashid>/`),
the paste will be rendered for a Web browser according to the paste's associated MIME type.
A rendering mode can be explicitly selected by appending `/<mode>` to the URI.

Currently, the following rendering modes are supported:

- [Asciicasts](https://asciinema.org/) (`application/x-asciicast`): `GET /<hashid>/cast`

- [Markdown](https://en.wikipedia.org/wiki/Markdown) (`text/markdown`): `GET /<hashid>/md`

- [reStructuredText](https://en.wikipedia.org/wiki/ReStructuredText) (`text/x-rst`): `GET /<hashid>/rst`

Additionally, syntax highlighting is supported for many other text types: `GET /<hashid>/text`

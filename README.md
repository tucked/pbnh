# pbnh

A [Content-Addressed](https://en.wikipedia.org/wiki/Content-addressable_storage) [Pastebin](https://en.wikipedia.org/wiki/Pastebin) featuring

- Syntax Highlighting by [CodeMirror](https://github.com/codemirror/codemirror)
- Asciicast Rendering with [asciinema player](https://github.com/asciinema/asciinema-player)
- Icons from [Font Awesome](https://github.com/FortAwesome/Font-Awesome)
- and more!

It is highly derived from [silverp1](https://github.com/silverp1)'s and [buhman](https://github.com/buhman)'s project [pb](https://github.com/ptpb/pb), and they deserve recognition for this idea.

## Usage

See [about.md](pbnh/static/about.md) (available at `/about` after Deployment) for usage details.

## Deployment

A pre-built image of the project is [available from Docker Hub](https://hub.docker.com/r/tucked/pbnh):

```sh
docker pull tucked/pbnh:latest
```

Alternatively, it can always be built locally:

``` sh
docker build --tag pbnh:latest .
```

### Configuration

Before deploying, create a configuration file that tells the app _how_ to run:

``` sh
edit sample_config.yml
```

Primarily, `SQLALCHEMY_DATABASE_URI` needs to be set.
Any [dialect supported by SQLAlchemy](https://docs.sqlalchemy.org/en/20/dialects/index.html) should work;
however, only SQLite and PostgreSQL are currently tested.

Note: In-memory databases are NOT supported.

If the server is not configured correctly, it will produce an error like this:

```
[2023-02-28 07:07:03 +0000] [6] [WARNING] [Errno 2] Unable to load configuration file (No such file or directory): '/etc/pbnh.yaml'
[2023-02-28 07:07:03 +0000] [6] [ERROR] SQLALCHEMY_DATABASE_URI is not set in the config.
Failed to find application object: 'create_app(check_db=True)'
[2023-02-28 07:07:03 +0000] [6] [INFO] Worker exiting (pid: 6)
[2023-02-28 07:07:03 +0000] [1] [INFO] Shutting down: Master
[2023-02-28 07:07:03 +0000] [1] [INFO] Reason: App failed to load.
```

#### WSGI

Gunicorn serves the project, and configuration for it can be bind-mounted to `/pbnh/gunicorn.conf.py`.

See https://docs.gunicorn.org/en/20.1.0/configure.html#configuration-file for more information.

### Initialization

For the sake of demonstration, this guide will set up an SQLite database.

Start by setting this in the configuration file: `SQLALCHEMY_DATABASE_URI: sqlite:////pbnh/tmpdb.sqlite`
Then, create a file to use for that database (and make it editable to the container user):

``` sh
touch paste.sqlite
chmod 666 paste.sqlite
```

Next, initialize the database:

``` sh
docker run --interactive --tty \
    --volume "$PWD/sample_config.yml:/etc/pbnh.yaml:ro" \
    --volume "$PWD/paste.sqlite:/pbnh/tmpdb.sqlite" \
    pbnh:latest pipenv run flask --app pbnh db init
```

If the database is not initialized correctly, the server will produce an error like this:

```
[2023-04-16 19:04:25 +0000] [1] [INFO] Starting gunicorn 20.1.0
[2023-04-16 19:04:25 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000 (1)
[2023-04-16 19:04:25 +0000] [1] [INFO] Using worker: sync
[2023-04-16 19:04:25 +0000] [7] [INFO] Booting worker with pid: 7
[2023-04-16 19:04:26 +0000] [7] [INFO] PBNH_CONFIG is not set in the environment. Trying /etc/pbnh.yaml...
[2023-04-16 19:04:26 +0000] [7] [INFO] /etc/pbnh.yaml was loaded successfully.
[2023-04-16 19:04:26 +0000] [7] [ERROR] (sqlite3.OperationalError) no such table: paste
[SQL: SELECT paste.id AS paste_id, paste.hashid AS paste_hashid, paste.ip AS paste_ip, paste.timestamp AS paste_timestamp, paste.mime AS paste_mime, paste.sunset AS paste_sunset, paste.data AS paste_data
FROM paste
WHERE paste.hashid = ?
 LIMIT ? OFFSET ?]
[parameters: ('Has the database been initialized?', 1, 0)]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
[2023-04-16 19:04:26 +0000] [7] [INFO] The database is not usable. Trying again in 10 seconds...
```

Note: If this happens, the container will remain running so that it can be used to initialize the database:

``` sh
docker ps  # Get the container name or ID.
docker exec "$container_name_or_ID" pipenv run flask --app pbnh db init
```

### Execution

Finally, start the app:

``` sh
docker run --interactive --tty \
    --volume "$PWD/sample_config.yml:/etc/pbnh.yaml:ro" \
    --volume "$PWD/paste.sqlite:/pbnh/tmpdb.sqlite" \
    --publish 12345:8000 \
    pbnh:latest
```

Then, open http://localhost:12345/ in a browser.

Note: In a production environment, a reverse proxy (e.g. nginx) should be deployed in front of the app.
See https://flask.palletsprojects.com/en/2.2.x/deploying/ for more information.

## Development

To run the tests, run the `sut` ("System Under Test") service in `docker-compose.test.yml`:

``` sh
docker compose -f docker-compose.test.yml run sut
```

Note: This pattern is meant to be compatible with [automated repository testing on Docker Hub](https://docs.docker.com/docker-hub/builds/automated-testing/).

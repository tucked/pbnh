#!/usr/bin/env sh
[ "$#" = 0 ] || {
    echo "usage: $0" 1>&2
    exit 1
}
set -o errexit
set -o xtrace

# Build:
tag='pbnh:dev'
docker build -t "$tag" .

# Create a database file:
db="/tmp/pbnh-$USER.sqlite"
touch "$db"
chmod 666 "$db"
container_db='/pbnh/tmpdb.sqlite'

# Create a config file, if necessary:
conf="$(dirname "$db")/pbnh-$USER.yaml"
[ -e "$conf" ] || {
    echo "SQLALCHEMY_DATABASE_URI: sqlite:///$container_db"
    echo 'DEBUG: True'
    echo 'TESTING: True'
} > "$conf"

# Create a gunicorn config file, if necessary:
gunicorn_conf="$(dirname "$db")/pbnh-$USER-gunicorn.conf.py"
[ -e "$gunicorn_conf" ] || {
    echo 'loglevel = "debug"'
} > "$gunicorn_conf"

# Clean up any past runs and start the app:
container='pbnh_dev'
docker kill "$container" || true
docker rm "$container" || true
# > If the PORT environment variable is defined, the default is ['0.0.0.0:$PORT'].
# > If it is not defined, the default is ['127.0.0.1:8000'].
export PORT="${PORT:-8000}"
docker run --name "$container" \
    -v "$conf:/etc/pbnh.yaml:ro" \
    -v "$db:$container_db" \
    -v "$gunicorn_conf:/pbnh/gunicorn.conf.py:ro" \
    --env PORT \
    -p "$PORT:$PORT" \
    --detach \
    "$tag"
docker exec "$container" pipenv run flask --app pbnh db init
docker attach "$container"

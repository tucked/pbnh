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

# Clean up any past runs and start the app:
container='pbnh_dev'
docker kill "$container" || true
docker rm "$container" || true
docker run -v "$conf:/etc/pbnh.yaml:ro" -v "$db:$container_db" -p 8000:8000 -d --name "$container" "$tag"
docker exec "$container" pipenv run flask --app pbnh db init
docker attach "$container"

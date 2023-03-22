#!/usr/bin/env bash
set -o errexit
set -o xtrace
docker build -t pbnh:latest .
db="$PWD/paste.sqlite"
touch "$db"
chmod 666 "$db"
container='pbnh_dev'
docker kill "$container" || true
docker rm "$container" || true
docker run -v "$PWD/paste.yaml:/etc/pbnh.yaml:ro" -v "$db:/pbnh/tmpdb.sqlite" -p 8000:8000 -d --name "$container" pbnh:latest
docker exec "$container" pipenv run flask --app pbnh db init

#!/usr/bin/env sh
[ "$#" = 0 ] || {
    echo "usage: $0" 1>&2
    exit 1
}
export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.test.yml}"
docker compose down --remove-orphans
docker compose run sut || exit 1
docker compose down || exit 1

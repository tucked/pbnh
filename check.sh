#!/usr/bin/env bash
files="-f docker-compose.yml"
[ $files ] || files=""
files="$files -f docker-compose.test.yml"
for i in $(seq 1 1)
do
    docker compose $files down --remove-orphans
    docker compose $files run sut || exit 1
    docker compose $files down --remove-orphans || exit 1
done

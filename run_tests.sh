#!/usr/bin/env sh
set -o errexit
set -o xtrace
pipenv install --deploy --dev
# https://github.com/kvesteri/sqlalchemy-utils/issues/166
pipenv check --ignore 42194 --ignore 51668  # https://github.com/sqlalchemy/sqlalchemy/pull/8563

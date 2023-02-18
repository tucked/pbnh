#!/usr/bin/env sh
set -o errexit
set -o xtrace
pipenv install --deploy --dev
pipenv check --ignore 51668  # https://github.com/sqlalchemy/sqlalchemy/pull/8563

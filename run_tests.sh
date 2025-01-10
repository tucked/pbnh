#!/usr/bin/env sh
set -o errexit
set -o xtrace
pipenv install --deploy --dev
pipenv check
pipenv run black --check pbnh tests
pipenv run flake8 pbnh tests
pipenv run mypy --strict pbnh
pipenv run bandit --recursive pbnh
init_config="$(mktemp)"
echo "[run]\ninclude = pbnh/__init__.py\n" > "$init_config"
pipenv run pytest --cov --cov-config "$init_config" --cov-branch --cov-fail-under 100 --cov-report term-missing -v tests/test_init.py
rm "$init_config"
pipenv run pytest --cov-branch --cov-fail-under 100 --cov-report term-missing --cov pbnh.cli -v tests/test_cli.py
pipenv run pytest --cov-branch --cov-fail-under 100 --cov-report term-missing --cov pbnh.db -v tests/test_db.py
pipenv run pytest --cov-branch --cov-fail-under 100 --cov-report term-missing --cov pbnh.views -v tests/test_views.py
pipenv run pytest --cov-branch --cov-fail-under 100 --cov-report term-missing --cov pbnh

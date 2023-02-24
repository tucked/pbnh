import click
from flask import Blueprint

import pbnh.db

blueprint = Blueprint("cli", __name__, cli_group=None)


@blueprint.cli.group()  # type: ignore
def db() -> None:
    pass


@db.command()  # type: ignore
def init() -> None:
    pbnh.db.init_db()
    click.echo("initialized the database successfully")

import click
from flask import Blueprint

import pbnh.db

blueprint = Blueprint("cli", __name__, cli_group=None)


@blueprint.cli.group()
def db():
    pass


@db.command()
def init():
    pbnh.db.init_db()
    click.echo("initialized the database successfully")

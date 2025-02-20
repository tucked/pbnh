import hashlib

import click
from flask import Blueprint

import pbnh.db

blueprint = Blueprint("cli", __name__, cli_group=None)


@blueprint.cli.group()
def db() -> None:
    pass


@db.command()
def init() -> None:
    pbnh.db.init_db()
    click.echo("initialized the database successfully")


@blueprint.cli.group()
@click.pass_context
def paste(ctx: click.Context) -> None:
    ctx.obj.data["paster"] = ctx.with_resource(pbnh.db.paster_context())


@paste.command()
@click.option(
    "--show-data/--no-show-data",
    help="whether to show paste data",
    default=False,
    show_default=True,
)
@click.argument("hashids", type=str, nargs=-1)
@click.pass_context
def info(ctx: click.Context, show_data: bool, hashids: tuple[str]) -> None:
    """Get info on pastes."""
    for multiple_hashids, hashid in enumerate(hashids):
        if multiple_hashids:
            click.echo("=" * 80)
        paste = ctx.obj.data["paster"].query(hashid=hashid)
        if paste is None:
            click.echo(f"{hashid} not found")
            continue
        data_sha1 = hashlib.sha1(paste["data"], usedforsecurity=False).hexdigest()
        for column, value in (
            [
                (
                    "hashid",
                    paste["hashid"]
                    + (
                        click.style(f" (WARNING: expected {data_sha1})", fg="yellow")
                        if data_sha1 != paste["hashid"]
                        else ""
                    ),
                )
            ]
            + [
                (column, value)
                for column, value in paste.items()
                if column not in {"data", "hashid"}
            ]
            + [
                (
                    "data",
                    paste["data"] if show_data else f"({len(paste['data'])} bytes)",
                )
            ]
        ):
            click.echo(f"{column + ':':>15} {value}")


@paste.command()
@click.argument("hashids", type=str, nargs=-1)
@click.pass_context
def remove(ctx: click.Context, hashids: tuple[str]) -> None:
    """Remove pastes."""
    for hashid in hashids:
        removed = ctx.obj.data["paster"].delete(hashid=hashid)
        message = "removed" if removed else "not found"
        click.echo(f"{hashid} {message}")

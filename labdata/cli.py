import click
from sqlalchemy import create_engine

from .util import run_sql_file, working_directory
from .app import app

cli = click.Group()

@cli.command(name='init')
@click.argument('database', type=str)
def init_database(database):

    # TODO: make less sloppy.
    db = create_engine(f"postgresql:///{database}")

    with working_directory(__file__):
        run_sql_file(db, "sql/setup-database.sql")
        run_sql_file(db, "sql/create-tables.sql")

@cli.command(name='serve')
@click.argument('database', type=str) # For testing
def dev_server(database):
    app.run(debug=True)
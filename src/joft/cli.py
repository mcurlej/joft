import click

@click.group()
def main() -> None:
    pass


@click.command(name="run")
@click.option("--template", help="File path to the template file.")
def run():
    print("run")

main.add_command(run)
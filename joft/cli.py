import logging
import sys

import click
import jira

import joft.base
import joft.utils


@click.group()
@click.pass_context
def main(ctx) -> None:
    ctx.obj = joft.utils.load_toml_app_config()


# TODO: refactor th CLI interface so it makes more sense
@main.command(name="validate")
@click.option("--template", help="File path to the template file.")
def validate(template) -> int:
    ret_code = joft.base.validate_template(template)
    sys.exit(ret_code)


@main.command(name="run")
@click.option("--template", help="File path to the template file.")
@click.pass_obj
def run(ctx, template: str) -> int:
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
    logging.info(
        f"Establishing session with jira server: {ctx['jira']['server']['hostname']}:"
    )

    jira_session = jira.JIRA(
        ctx["jira"]["server"]["hostname"], token_auth=ctx["jira"]["server"]["pat_token"]
    )

    logging.info("Session established...")
    logging.info(f"Executing Jira template: {template}")

    ret_code = joft.base.execute_template(template, jira_session)

    sys.exit(ret_code)


@main.command(name="list-issues")
@click.option("--template", help="File path to the template file.")
@click.pass_obj
def list_issues(ctx, template: str) -> None:
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
    logging.info(
        f"Establishing session with jira server: {ctx['jira']['server']['hostname']}:"
    )

    jira_session = jira.JIRA(
        ctx["jira"]["server"]["hostname"], token_auth=ctx["jira"]["server"]["pat_token"]
    )

    logging.info("Session established...")
    logging.info(f"Executing trigger from Jira template: {template}")

    print(joft.base.list_issues(template, jira_session))

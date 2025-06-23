import sys
from typing import Dict, Any, Optional

import click
import jira

import joft.base
import joft.utils
from joft.logger import configure_logger, logger


@click.group()
@click.option("--config", help="Path to the config file.")
@click.pass_context
def main(ctx: click.Context, config: Optional[str] = None) -> None:
    """
    A CLI automation tool which interacts with a Jira instance and automates tasks.
    """
    ctx.obj = joft.utils.load_toml_app_config(config_path=config)
    if "logging" in ctx.obj:
        configure_logger(logging_config=ctx.obj["logging"])


# TODO: refactor th CLI interface so it makes more sense
@main.command(name="validate")
@click.option("--template", help="File path to the template file.")
def validate(template: str) -> int:
    ret_code = joft.base.validate_template(template)
    sys.exit(ret_code)


@main.command(name="run")
@click.option("--template", help="File path to the template file.")
@click.pass_obj
def run(ctx: Dict[str, Dict[str, Any]], template: str) -> int:
    logger.info(
        f"Establishing session with jira server: {ctx['jira']['server']['hostname']}:"
    )

    jira_session = jira.JIRA(
        ctx["jira"]["server"]["hostname"], token_auth=ctx["jira"]["server"]["pat_token"]
    )

    logger.info("Session established...")
    logger.info(f"Executing Jira template: {template}")

    ret_code = joft.base.execute_template(template, jira_session)

    sys.exit(ret_code)


@main.command(name="list-issues")
@click.option("--template", help="File path to the template file.")
@click.pass_obj
def list_issues(ctx: Dict[str, Dict[str, Any]], template: str) -> None:
    logger.info(
        f"Establishing session with jira server: {ctx['jira']['server']['hostname']}:"
    )

    jira_session = jira.JIRA(
        ctx["jira"]["server"]["hostname"], token_auth=ctx["jira"]["server"]["pat_token"]
    )

    logger.info("Session established...")
    logger.info(f"Executing trigger from Jira template: {template}")

    print(joft.base.list_issues(template, jira_session))

import logging

import click
import jira

import joft.base
import joft.utils



@click.group()
@click.pass_context
def main(ctx) -> None:
    ctx.obj = joft.utils.load_toml_app_config("./joft.config.toml")


# TODO: refactor th CLI interface so it makes more sense
@main.command(name="validate")
@click.option("--template", help="File path to the template file.")
def validate(template):
    joft.base.validate_template(template)


@main.command(name="run")
@click.option("--template", help="File path to the template file.")
@click.pass_obj
def run(ctx, template: str) -> None:
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    logging.info(f"Establishing session with jira server: {ctx['jira']['server']['hostname']}:")
    
    jira_session = jira.JIRA(ctx['jira']['server']['hostname'], 
                             ctx['jira']['server']['api_token'])

    logging.info("Session established...")  
    logging.info(f"Executing Jira template: {template}")

    joft.base.execute_template(template, jira_session)


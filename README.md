# Jira Off-load Tool - JOFT

## What is this?

JOFT is a CLI tool for automation of user actions on a [JIRA](https://www.atlassian.com/software/jira) instance. This was created because the build-in automation in JIRA is not sufficient when you want to do complex actions without having the admin rights on the instance.

## How does it work?

To do automation with JOFT you first need to write a yaml template file which will actually hold your actions that you want execute. You can execute actions per issue from a JQL trigger query or without it.

If you provide a specific trigger JQL query in the yaml file, all the described actions defined in a yaml template file will execute once per issue found by the trigger JQL query. A yaml template file can have only JQL trigger query. If you need more create another yaml template file with a different query.

If you don't provide the trigger JQL query, the defined actions will execute once.

## Installation

Clone the repo. Create a virtualenv with the tool of your liking just make sure the Python version is 3.11 and higher.

To install the tool go to the root dir of the project, activate your venv, and run `pip install .`. For development, run `pip install -e .` instead.

To run all tests and type-checker run `tox`.

## Usage

First you need to have a jira instance and an account on that instance. Then you need get personal access token your [PAT token](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html). To be able to work with JOFT create a config for your JIRA instance in the root of the project folder. There is an default config example you can use in the project folder `joft.config.toml.default`. Just remove the `.default` from the end of the file and add your credentials and you are good to go.

To get help run the tool in CLI withou any options: 

`joft`.

To validate your yaml template file run: 

`joft validate --template ./<path to your yaml template>`

To run the actions from your yaml template file run: 

`joft run --template ./<path to your yaml template>`

## Docs

Documentation can be found [here](docs/introduction.md).

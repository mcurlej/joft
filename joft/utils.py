import pathlib
import textwrap
import typing
import tomllib
import sys

import platformdirs
import yaml


def load_and_parse_yaml_file(path: str) -> typing.Dict[str, typing.Any]:
    with open(path) as fp:
        yaml_obj = yaml.safe_load(fp)

    return yaml_obj


def load_toml_app_config() -> typing.Any:
    possible_paths = set()

    possible_paths.add(platformdirs.user_config_dir())
    possible_paths.update(*platformdirs.site_config_dir(multipath=True).split(":"))
    possible_paths.add("/etc")
    possible_paths.add(str(pathlib.Path.cwd()))

    for path in possible_paths:
        config_file_path = pathlib.Path(path) / "joft.config.toml"
        if config_file_path.is_file():
            break
    else:
        err_msg = textwrap.dedent(f"""\
            [ERROR] Cannot find configuration file 'joft.config.toml'.

            Create the file with the following content:

            [jira.server]
            hostname = "<your jira server url>"
            pat_token = "<your jira pat token>"

            in one of the following directories:
            {', '.join(possible_paths)}\
        """)

        print(err_msg)
        sys.exit(1)

    with open(config_file_path, "rb") as fp:
        config = tomllib.load(fp)

    return config

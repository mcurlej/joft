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


def read_and_validate_config(
    path: str | pathlib.Path,
) -> typing.Dict[str, typing.Any] | None:
    """Read and return config file is it's valid. Return None otherwise."""
    with open(path, "rb") as fp:
        config = tomllib.load(fp)

    try:
        config["jira"]["server"]["hostname"]
        config["jira"]["server"]["pat_token"]
    except KeyError:
        return None
    else:
        return config


def load_toml_app_config() -> typing.Any:
    possible_paths = []

    possible_paths.append(str(pathlib.Path.cwd()))
    possible_paths.append(platformdirs.user_config_dir())
    possible_paths.extend(platformdirs.site_config_dir(multipath=True).split(":"))
    possible_paths.append("/etc")

    for path in possible_paths:
        config_file_path = pathlib.Path(path) / "joft.config.toml"
        if config_file_path.is_file():
            if config := read_and_validate_config(config_file_path):
                return config
            else:
                err_msg = textwrap.dedent(f"""\
                    [ERROR] Configuration file {config_file_path} is invalid.

                    Configuration file should have the following content:

                    [jira.server]
                    hostname = "<your jira server url>"
                    pat_token = "<your jira pat token>"

                    and should be stored in one of the following directories:
                    {', '.join(possible_paths)}\
                """)
                print(err_msg)
                sys.exit(1)
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

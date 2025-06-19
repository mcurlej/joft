import pathlib
import textwrap
from typing import Dict, Any, Optional, List, Union, NoReturn
import tomllib
import sys

import platformdirs
import yaml


def load_and_parse_yaml_file(path: str) -> Dict[str, Any]:
    with open(path) as fp:
        yaml_obj = yaml.safe_load(fp)

    return yaml_obj


def read_and_validate_config(
    path: Union[str, pathlib.Path],
) -> Dict[str, Any]:
    """Read and return config file if it's valid. Raises Exception if invalid."""
    with open(path, "rb") as fp:
        config = tomllib.load(fp)

    # Validate required fields exist
    config["jira"]["server"]["hostname"]
    config["jira"]["server"]["pat_token"]

    return config


def load_toml_app_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads the TOML application configuration.

    If a config_path is provided, it will be loaded first. Otherwise, it will search for the config file in the default locations.

    Args:
        config_path: Optional path to the config file.

    Returns:
        The application configuration as a dictionary.

    Raises:
        SystemExit: If the configuration file is invalid or not found.
    """
    possible_paths: List[str] = []
    possible_paths.append(str(pathlib.Path.cwd()))
    possible_paths.append(platformdirs.user_config_dir())
    possible_paths.extend(platformdirs.site_config_dir(multipath=True).split(":"))
    possible_paths.append("/etc")

    if config_path:
        config_file_path = pathlib.Path(config_path)
        try:
            config = read_and_validate_config(config_file_path)
            return config
        except Exception as e:
            _display_error_and_exit(config_file_path, possible_paths, e)

    for path in possible_paths:
        config_file_path = pathlib.Path(path) / "joft.config.toml"
        if config_file_path.is_file():
            try:
                config = read_and_validate_config(config_file_path)
                return config
            except Exception as e:
                _display_error_and_exit(config_file_path, possible_paths, e)

    # If we get here, no valid config was found
    _display_error_and_exit(
        pathlib.Path("joft.config.toml"),  # Default config file name
        possible_paths,
        FileNotFoundError("Configuration file not found"),
    )


def _display_error_and_exit(
    config_file_path: pathlib.Path, possible_paths: List[str], e: Exception
) -> NoReturn:
    """Display error message and exit. This function never returns."""
    err_msg = textwrap.dedent(f"""\
        [ERROR] Configuration file {config_file_path} is invalid:

        {type(e).__name__} - {str(e)}

        Configuration file should have the following content:

        [jira.server]
        hostname = "<your jira server url>"
        pat_token = "<your jira pat token>"

        and should be stored in one of the following directories:
        {", ".join(possible_paths)}\
    """)

    print(err_msg)
    sys.exit(1)

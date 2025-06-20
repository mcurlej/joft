import pathlib
import textwrap
from typing import Dict, Any, Never, Optional
import tomllib
import sys

import platformdirs
import yaml


def load_and_parse_yaml_file(path: str) -> Dict[str, Any]:
    with open(path) as fp:
        yaml_obj = yaml.safe_load(fp)

    return yaml_obj


def read_and_validate_config(
    path: str | pathlib.Path,
) -> Dict[str, Any]:
    """Read and return config file if it's valid.

    Args:
        path: Path to the config file

    Returns:
        Dict containing the validated configuration

    Raises:
        KeyError: If required configuration keys are missing
        tomllib.TOMLDecodeError: If TOML syntax is invalid
        FileNotFoundError: If config file doesn't exist
    """
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
    possible_paths: list[str] = []
    possible_paths.append(str(pathlib.Path.cwd()))
    possible_paths.append(platformdirs.user_config_dir())
    possible_paths.extend(platformdirs.site_config_dir(multipath=True).split(":"))
    possible_paths.append("/etc")

    if config_path:
        config_file_path = pathlib.Path(config_path)
        try:
            return read_and_validate_config(config_file_path)
        except Exception as e:
            _display_error_and_exit(config_file_path, possible_paths, e)
            return {}  # This line is never reached due to sys.exit(1), but satisfies type checker

    # Initialize with a default path in case no config is found
    default_config_path = pathlib.Path(possible_paths[0]) / "joft.config.toml"

    for path in possible_paths:
        config_file_path = pathlib.Path(path) / "joft.config.toml"
        if config_file_path.is_file():
            try:
                return read_and_validate_config(config_file_path)
            except Exception as e:
                _display_error_and_exit(config_file_path, possible_paths, e)
                return {}  # This line is never reached due to sys.exit(1), but satisfies type checker

    # If we get here, no config was found
    _display_error_and_exit(
        default_config_path,
        possible_paths,
        FileNotFoundError("Configuration file not found"),
    )
    return {}  # This line is never reached due to sys.exit(1), but satisfies type checker


def _display_error_and_exit(
    config_file_path: pathlib.Path, possible_paths: list[str], e: Exception
) -> Never:
    """Display a formatted error message and exit the program.

    Args:
        config_file_path: Path to the config file that caused the error
        possible_paths: List of paths where config file can be stored
        e: Exception that was raised

    Note:
        This function always exits the program with status code 1
    """
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

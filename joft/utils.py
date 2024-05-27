import typing
import tomllib

import yaml

def load_and_parse_yaml_file(path: str) -> typing.Dict[str, typing.Any]:
    with open(path) as fp:
        yaml_obj = yaml.safe_load(fp)

    return yaml_obj


def load_toml_app_config(path: str) -> typing.Any:
    
    with open(path, "rb") as fp:
        config = tomllib.load(fp)

    return config
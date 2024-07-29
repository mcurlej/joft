import pytest

import joft.utils

def test_load_valid_yaml() -> None:
    """ Quick test to check the loading of yaml files. """

    yaml_obj = joft.utils.load_and_parse_yaml_file("./tests/mock_data/valid.yaml")
    assert type(yaml_obj) is dict
    assert "kind" in yaml_obj.keys()
    assert "metadata" in yaml_obj.keys()
    assert "triggers" in yaml_obj.keys()
    assert "apiVersion" in yaml_obj.keys()

def test_load_invalid_yaml_raise() -> None:
    """ The function should raise if the yaml file is invalid. """

    with pytest.raises(Exception):
        joft.utils.load_and_parse_yaml_file("./tests/mock_data/invalid.yaml")
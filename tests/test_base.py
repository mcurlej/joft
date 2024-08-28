import unittest
import unittest.mock
import typing

import pytest

import joft.base
import joft.models


def _setup_jira_template_yaml(
    duplicate_id: bool = False,
    invalid_action: bool = False,
    no_object_ids: bool = False,
) -> dict[str, typing.Any]:
    """Setup function that provides different types of yaml structures"""

    # TODO use the specs defined in the specs directory for testing
    jira_template_yaml = {
        "api_version": 1,
        "kind": "jira-template",
        "metadata": {"name": "test", "description": "test"},
        "trigger": {
            "type": "jira-jql-search",
            "object_id": "issue",
            "jql": "test test",
        },
        "actions": [
            {
                "object_id": "ticket",
                "type": "create-ticket",
                "reuse_data": [
                    {
                        "reference_id": "issue",
                        "fields": ["key", "summary", "description"],
                    },
                ],
                "fields": {
                    "project": {"key": "TEST"},
                    "issuetype": {"name": "Story"},
                    "summary": "${issue.key} - ${issue.summary}",
                    "description": "${issue.description}",
                },
            },
            {
                "object_id": "another_ticket",
                "type": "create-ticket",
                "reuse_data": [
                    {"reference_id": "ticket", "fields": ["key", "summary"]},
                ],
                "fields": {
                    "project": {"key": "TEST"},
                    "issuetype": {"name": "Story"},
                    "summary": "${ticket.key} - ${ticket.summary}",
                    "description": "${issue.description}",
                },
            },
        ],
    }

    if duplicate_id:
        for action in jira_template_yaml["actions"]:
            action["object_id"] = "ticket"

    if invalid_action:
        jira_template_yaml["actions"][0]["type"] = "invalid_action"

    if no_object_ids:
        for action in jira_template_yaml["actions"]:
            action.pop("object_id", None)

    return jira_template_yaml


def test_validate_uniqueness_of_object_ids_raise() -> None:
    """All the object_ids need to be unique. If it is not the case we need to raise."""

    duplicate_id = "ticket"

    jira_template_yaml = _setup_jira_template_yaml(duplicate_id=True)
    jira_template = joft.models.JiraTemplate(**jira_template_yaml)

    with pytest.raises(Exception) as ex:
        joft.base.validate_uniqueness_of_object_ids(jira_template)

    assert "has failed" in ex.value.args[0].lower()
    assert duplicate_id in ex.value.args[0].lower()
    assert "2 or more objects" in ex.value.args[0].lower()


def test_update_reference_pool() -> None:
    """Test if the reference_pool is updated with correct references"""

    create_ticket_template = {
        "object_id": "ticket",
        "type": "create-ticket",
        "reuse_data": [
            {
                "reference_id": "issue",
                "fields": [
                    "key",
                    "summary",
                    "description",
                    "id",
                    "project",
                    "link",
                    "url",
                    "permalink",
                    "components",
                    "priority",
                ],
            },
        ],
        "fields": {
            "project": {"key": "TEST"},
            "issuetype": {"name": "Story"},
            "summary": "${issue.key} - ${issue.summary}",
            "description": "${issue.description}",
        },
    }
    mock_reference_pool = {}

    mock_reference_issue = unittest.mock.MagicMock()
    mock_reference_issue.key = "TEST-123"
    mock_reference_issue.id = "TEST-123"
    mock_reference_issue.fields.summary = "Hello from referenced issue summary"
    mock_reference_issue.fields.description = "Hello from referenced issue description"
    mock_comp_1 = unittest.mock.MagicMock()
    mock_comp_1.name = "Test 1"
    mock_comp_2 = unittest.mock.MagicMock()
    mock_comp_2.name = "Test 2"
    mock_reference_issue.fields.components = [mock_comp_1, mock_comp_2]
    mock_reference_issue.fields.project.key = "TEST"
    mock_reference_issue.permalink.return_value = "http://mock_url.com"
    mock_reference_issue.fields.priority.name = "Critical"

    mock_reference_pool["issue"] = mock_reference_issue

    jira_template = joft.models.CreateTicketAction(**create_ticket_template)

    joft.base.update_reference_pool(jira_template.reference_data, mock_reference_pool)

    assert "issue.key" in mock_reference_pool
    assert "issue.summary" in mock_reference_pool
    assert "issue.description" in mock_reference_pool
    assert "issue.priority" in mock_reference_pool
    assert "issue.components" in mock_reference_pool
    assert "issue.id" in mock_reference_pool
    assert "issue.project" in mock_reference_pool
    assert "issue.link" in mock_reference_pool
    assert "issue.url" in mock_reference_pool
    assert "issue.permalink" in mock_reference_pool
    assert mock_reference_pool["issue.key"] == mock_reference_issue.key
    assert mock_reference_pool["issue.id"] == mock_reference_issue.id
    assert mock_reference_pool["issue.summary"] == mock_reference_issue.fields.summary
    assert (
        mock_reference_pool["issue.description"]
        == mock_reference_issue.fields.description
    )
    assert (
        mock_reference_pool["issue.project"] == mock_reference_issue.fields.project.key
    )
    assert mock_reference_pool["issue.url"] == mock_reference_issue.permalink()
    assert mock_reference_pool["issue.link"] == mock_reference_issue.permalink()
    assert mock_reference_pool["issue.permalink"] == mock_reference_issue.permalink()
    assert type(mock_reference_pool["issue.components"]) is list
    component_names = [c["name"] for c in mock_reference_pool["issue.components"]]
    for c in mock_reference_issue.components:
        assert c.name in component_names


def test_fail_update_reference_pool_when_reference_not_exist() -> None:
    """
    Test if we raise, when a reference_id is used without defining the object_id in a previous
    action .
    """
    not_yet_referenced = "not_yet_referenced"

    create_ticket_template = {
        "object_id": "ticket",
        "type": "create-ticket",
        "reuse_data": [
            {"reference_id": not_yet_referenced, "fields": ["key"]},
            {"reference_id": "issue", "fields": ["priority"]},
        ],
        "fields": {
            "project": {"key": "TEST"},
            "issuetype": {"name": "Story"},
            "summary": "${issue.key} - ${issue.summary}",
            "description": "${issue.description}",
        },
    }

    mock_reference_pool = {}

    mock_reference_issue = unittest.mock.MagicMock()
    mock_reference_issue.key = "TEST-123"
    mock_reference_issue.fields.summary = "Hello from referenced issue summary"
    mock_reference_issue.fields.description = "Hello from referenced issue description"

    mock_reference_pool["issue"] = mock_reference_issue

    jira_template = joft.models.CreateTicketAction(**create_ticket_template)

    with pytest.raises(Exception) as ex:
        joft.base.update_reference_pool(
            jira_template.reference_data, mock_reference_pool
        )

    assert "used before it was declared" in ex.value.args[0].lower()
    assert not_yet_referenced in ex.value.args[0].lower()


def test_replace_ref() -> None:
    """Test the the function replaces text as expected."""
    field = "This is ${issue.priority}"
    reference_id = "issue.priority"
    value = "Critical"

    assert joft.base.replace_ref(field, reference_id, value) == f"This is {value}"


def test_apply_reference_pool_to_payload() -> None:
    """Test if references are replaced with actual values."""

    mock_reference_pool = {}

    mock_reference_pool["issue.key"] = "TEST-123"
    mock_reference_pool["issue.summary"] = "This is a summary field."

    mock_fields = {
        "project": {"name": "${issue.key}"},
        "issuetype": {"name": "Story"},
        "summary": "${issue.summary}",
    }
    joft.base.apply_reference_pool_to_payload(mock_reference_pool, mock_fields)

    assert mock_fields["project"]["name"] == mock_reference_pool["issue.key"]
    assert mock_fields["summary"] == mock_reference_pool["issue.summary"]


def test_multiple_references_in_str_field() -> None:
    """Test if multiple references are replaced in one field."""

    mock_reference_pool = {}

    mock_reference_pool["issue.key"] = "TEST-123"
    mock_reference_pool["issue.summary"] = "This is a summary field."

    mock_fields = {
        "project": {"name": "${issue.key}"},
        "issuetype": {"name": "Story"},
        "summary": "${issue.summary} with key ${issue.key}",
    }
    joft.base.apply_reference_pool_to_payload(mock_reference_pool, mock_fields)

    assert mock_reference_pool["issue.summary"] in mock_fields["summary"]
    assert mock_reference_pool["issue.key"] in mock_fields["summary"]


@unittest.mock.patch("logging.info")
@unittest.mock.patch("joft.utils.load_and_parse_yaml_file")
@unittest.mock.patch("joft.base.execute_actions_per_trigger_ticket")
@unittest.mock.patch("joft.base.execute_actions")
def test_execute_template_with_trigger(
    mock_execute_actions,
    mock_execute_actions_per_trigger_ticket,
    mock_load_and_parse_yaml,
    mock_log_info,
) -> None:
    """Comprehensive test that loads the whole yaml template. Checks if the functions
    returns correct CLI codes."""

    jira_template_yaml = _setup_jira_template_yaml()
    mock_load_and_parse_yaml.return_value = jira_template_yaml

    mock_jira_session = unittest.mock.MagicMock()
    trigger_result = [{"ticket_id": 1}, {"ticket_id": 2}]
    mock_jira_session.search_issues.return_value = trigger_result
    yaml_file_path = "./jira_template.yaml"
    jira_template = joft.models.JiraTemplate(**jira_template_yaml)

    with unittest.mock.patch("joft.models.JiraTemplate") as mock_jira_template:
        mock_jira_template.return_value = jira_template

        ret_code = joft.base.execute_template(yaml_file_path, mock_jira_session)

    assert ret_code == 0

    mock_load_and_parse_yaml.assert_called_once_with(yaml_file_path)
    mock_jira_session.search_issues.assert_called_once_with(
        jira_template_yaml["trigger"]["jql"]
    )
    assert mock_execute_actions.call_count == 0
    mock_execute_actions_per_trigger_ticket.assert_called_once_with(
        trigger_result, jira_template, mock_jira_session
    )
    mock_log_info.assert_called_once_with("Yaml file loaded...")


@unittest.mock.patch("logging.info")
@unittest.mock.patch("joft.utils.load_and_parse_yaml_file")
@unittest.mock.patch("joft.base.execute_actions_per_trigger_ticket")
@unittest.mock.patch("joft.base.execute_actions")
def test_execute_template_exit_no_tickets(
    mock_execute_actions,
    mock_execute_actions_per_trigger_ticket,
    mock_load_and_parse_yaml,
    mock_log_info,
) -> None:
    """If there are no tickets returned from a JQL query the program should exit
    as soon as possible."""

    jira_template_yaml = _setup_jira_template_yaml()

    mock_load_and_parse_yaml.return_value = jira_template_yaml

    mock_jira_session = unittest.mock.MagicMock()
    trigger_result = []
    mock_jira_session.search_issues.return_value = trigger_result
    yaml_file_path = "./jira_template.yaml"
    jira_template = joft.models.JiraTemplate(**jira_template_yaml)

    with unittest.mock.patch("joft.models.JiraTemplate") as mock_jira_template:
        mock_jira_template.return_value = jira_template

        ret_code = joft.base.execute_template(yaml_file_path, mock_jira_session)

    assert ret_code == 1

    assert mock_execute_actions_per_trigger_ticket.call_count == 0
    assert mock_execute_actions.call_count == 0
    assert mock_log_info.call_count == 2
    assert mock_log_info.mock_calls[0].args[0] == "Yaml file loaded..."
    assert jira_template.jira_search.jql in mock_log_info.mock_calls[1].args[0]


@unittest.mock.patch("joft.base.validate_uniqueness_of_object_ids")
@unittest.mock.patch("joft.utils.load_and_parse_yaml_file")
def test_validate_template_success(
    mock_load_and_parse_yaml, mock_validate_uniqueness_object_ids
) -> None:
    """Quick test to find out if all the necessary functions are called when
    validation is invoked by the user."""

    yaml_file_path = "./jira_template.yaml"
    jira_template_yaml = _setup_jira_template_yaml()
    mock_load_and_parse_yaml.return_value = jira_template_yaml

    jira_template = joft.models.JiraTemplate(**jira_template_yaml)

    with unittest.mock.patch("joft.models.JiraTemplate") as mock_jira_template:
        mock_jira_template.return_value = jira_template
        ret_code = joft.base.validate_template(yaml_file_path)

    assert ret_code == 0
    mock_load_and_parse_yaml.assert_called_once_with(yaml_file_path)
    mock_validate_uniqueness_object_ids.assert_called_once_with(jira_template)


def test_object_id_not_present() -> None:
    """Test that Object IDs are optional, but still present in the dataclasses with
    None value"""

    jira_template_yaml = _setup_jira_template_yaml(no_object_ids=True)
    jira_template = joft.models.JiraTemplate(**jira_template_yaml)

    for action in jira_template.jira_actions:
        assert not action.object_id

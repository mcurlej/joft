import pytest

import joft.models


def test_jira_template_post_init():
    """Test the post init method of a dataclass. All the correct types
    should be assigned."""

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
                "type": "update-ticket",
                "reference_id": "issue",
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
            {
                "type": "link-issues",
                "object_id": "link-bug-and-epic",
                "fields": {
                    "type": "causes",
                    "inward_issue": "${issue.key}",
                    "outward_issue": "${ticket.key}",
                },
            },
        ],
    }

    jira_template = joft.models.JiraTemplate(**jira_template_yaml)
    action_types = [
        joft.models.CreateTicketAction,
        joft.models.UpdateTicketAction,
        joft.models.LinkIssuesAction,
    ]

    assert len(jira_template.jira_actions) == 3
    for action in jira_template.jira_actions:
        assert type(action) in action_types

    assert jira_template.jira_search
    assert type(jira_template.jira_search) is joft.models.Trigger


def test_reuse_data_must_be_list():
    """Raise if the reuse_data property is something else than a list."""

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
                "reuse_data": {
                    "reference_id": "issue",
                    "fields": ["key"],
                },
                "fields": {
                    "project": {"key": "TEST"},
                    "issuetype": {"name": "Story"},
                    "summary": "${issue.key} - ${issue.summary}",
                    "description": "${issue.description}",
                },
            },
        ],
    }

    with pytest.raises(Exception) as ex:
        joft.models.JiraTemplate(**jira_template_yaml)

    assert "must be a list" in ex.value.args[0].lower()
    assert "'dict'" in ex.value.args[0].lower()


# test the invalid action here
def test_execute_actions_invalid_action_raise() -> None:
    """We check if we will raise if a invalid action is defined in the
    initial yaml file."""

    bad_type = "new-ticket"
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
                "type": bad_type,
                "reuse_data": [
                    {
                        "reference_id": "issue",
                        "field": ["key", "summary", "description"],
                    },
                ],
                "fields": {
                    "project": {"key": "TEST"},
                    "issuetype": {"name": "Story"},
                    "summary": "${issue.key} - ${issue.summary}",
                    "description": "${issue.description}",
                },
            },
        ],
    }

    with pytest.raises(Exception) as ex:
        joft.models.JiraTemplate(**jira_template_yaml)

    assert "unknown action" in ex.value.args[0].lower()
    assert bad_type in ex.value.args[0].lower()

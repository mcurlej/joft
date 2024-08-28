import logging
import typing

import jira

import joft.models
import joft.base


def create_ticket(
    action: joft.models.CreateTicketAction,
    jira_session: jira.JIRA,
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue | str | typing.List[str]]
    ],
):
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)
    logging.debug(f"Creating new ticket of type: {action.fields['issuetype']['name']}")
    logging.debug(f"Payload:\n{action.fields}")

    new_issue: jira.Issue = jira_session.create_issue(action.fields)

    logging.info(f"New Jira ticket created: {new_issue.permalink()}")

    if action.object_id:
        reference_pool[action.object_id] = new_issue


# TODO jira_session is not needed here. Maybe remove?
def update_ticket(
    action: joft.models.UpdateTicketAction,
    jira_session: jira.JIRA,
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue | str | typing.List[str]]
    ],
):
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    if action.reference_id not in reference_pool:
        raise Exception(
            (
                f"Invalid reference id '{action.reference_id}'! "
                "You are referencing something that does not exist!"
            )
        )

    ticket_to: jira.Issue = typing.cast(jira.Issue, reference_pool[action.reference_id])

    logging.debug(f"Updating ticket '{ticket_to.key}'")
    logging.debug(f"Payload:\n{action.fields}")
    ticket_to.update(action.fields)

    logging.info(f"Ticket '{ticket_to.key}' updated.")

    if action.object_id:
        reference_pool[action.object_id] = ticket_to


def link_issues(
    action: joft.models.LinkIssuesAction,
    jira_session: jira.JIRA,
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue | str | typing.List[str]]
    ],
):
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    logging.info("Linking issues...")
    logging.info(f"Link type: {action.fields['type']}")
    logging.info(f"Linking From Issue: {action.fields['inward_issue']}")
    logging.info(f"Linking To Issue: {action.fields['outward_issue']}")

    jira_session.create_issue_link(
        action.fields["type"],
        action.fields["inward_issue"],
        action.fields["outward_issue"],
    )


def transition_issue(
    action: joft.models.TransitionAction,
    jira_session: jira.JIRA,
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue | str | typing.List[str]]
    ],
):
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    if action.reference_id not in reference_pool:
        raise Exception(
            (
                f"Invalid reference id '{action.reference_id}'! "
                "You are referencing something that does not exist!"
            )
        )

    ticket_to: jira.Issue = typing.cast(jira.Issue, reference_pool[action.reference_id])

    logging.info(f"Transitioning issue '{ticket_to.key}'...")
    logging.info(
        f"Changing status from '{ticket_to.fields.status}' to '{action.transition}'"
    )
    logging.info(f"With comment: \n{action.comment}")

    jira_session.transition_issue(
        ticket_to, action.transition, action.fields, action.comment
    )

    if action.object_id:
        reference_pool[action.object_id] = ticket_to

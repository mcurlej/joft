from joft.logger import logger
from typing import Dict, Union, List, cast, Any

import jira

import joft.models
import joft.base

# Type aliases for better readability
ReferencePoolType = Dict[str, Union[str, jira.Issue, List[Any]]]


def create_ticket(
    action: joft.models.CreateTicketAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Create a new JIRA ticket based on the action configuration.

    Args:
        action: The create ticket action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        jira.exceptions.JIRAError: If ticket creation fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)
    logger.debug(f"Creating new ticket of type: {action.fields['issuetype']['name']}")
    logger.debug(f"Payload:\n{action.fields}")

    new_issue: jira.Issue = jira_session.create_issue(action.fields)

    logger.info(f"New Jira ticket created: {new_issue.permalink()}")

    if action.object_id:
        reference_pool[action.object_id] = new_issue


def update_ticket(
    action: joft.models.UpdateTicketAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Update an existing JIRA ticket based on the action configuration.

    Args:
        action: The update ticket action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        Exception: If referenced ticket doesn't exist
        jira.exceptions.JIRAError: If ticket update fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    if action.reference_id not in reference_pool:
        raise Exception(
            (
                f"Invalid reference id '{action.reference_id}'! "
                "You are referencing something that does not exist!"
            )
        )

    ticket_to: jira.Issue = cast(jira.Issue, reference_pool[action.reference_id])

    logger.debug(f"Updating ticket '{ticket_to.key}'")
    logger.debug(f"Payload:\n{action.fields}")
    ticket_to.update(action.fields)

    logger.info(f"Ticket '{ticket_to.key}' updated.")

    if action.object_id:
        reference_pool[action.object_id] = ticket_to


def link_issues(
    action: joft.models.LinkIssuesAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Create a link between two JIRA issues.

    Args:
        action: The link issues action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        jira.exceptions.JIRAError: If link creation fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    logger.info("Linking issues...")
    logger.info(f"Link type: {action.fields['type']}")
    logger.info(f"Linking From Issue: {action.fields['inward_issue']}")
    logger.info(f"Linking To Issue: {action.fields['outward_issue']}")

    jira_session.create_issue_link(
        action.fields["type"],
        action.fields["inward_issue"],
        action.fields["outward_issue"],
    )


def transition_issue(
    action: joft.models.TransitionAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Transition a JIRA issue to a new status.

    Args:
        action: The transition action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        Exception: If referenced ticket doesn't exist
        jira.exceptions.JIRAError: If transition fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    if action.reference_id not in reference_pool:
        raise Exception(
            (
                f"Invalid reference id '{action.reference_id}'! "
                "You are referencing something that does not exist!"
            )
        )

    ticket_to: jira.Issue = cast(jira.Issue, reference_pool[action.reference_id])

    logger.info(f"Transitioning issue '{ticket_to.key}'...")
    logger.info(
        f"Changing status from '{ticket_to.fields.status}' to '{action.transition}'"
    )
    logger.info(f"With comment: \n{action.comment}")

    jira_session.transition_issue(
        ticket_to, action.transition, action.fields, action.comment
    )

    if action.object_id:
        reference_pool[action.object_id] = ticket_to

import copy
from typing import Dict, Union, List, Any, cast

import jira
import jira.client
import tabulate

import joft.actions
from joft.logger import logger
import joft.models
import joft.utils

# Type aliases for better readability
ReferencePoolType = Dict[str, Union[str, jira.Issue, List[Any]]]
ComponentType = Dict[str, str]


def load_and_validate_template(template_file_path: str) -> joft.models.JiraTemplate:
    """Load and validate a JIRA template file.

    This function performs the following operations:
    1. Loads the YAML template file from the specified path
    2. Parses and validates the YAML structure
    3. Validates the template against the JiraTemplate model schema
    4. Ensures all object_ids in the template are unique across actions and triggers
    5. Logs a confirmation message when the YAML file is successfully loaded

    Args:
        template_file_path (str): Path to the YAML template file to load and validate

    Returns:
        joft.models.JiraTemplate: A validated JiraTemplate object containing the template configuration

    Raises:
        yaml.YAMLError: If the template file contains invalid YAML syntax
        pydantic.ValidationError: If the template structure doesn't match JiraTemplate model
        Exception: If duplicate object_ids are found in the template
        FileNotFoundError: If the template file doesn't exist
    """
    template: Dict[str, Any] = joft.utils.load_and_parse_yaml_file(template_file_path)
    jira_template = joft.models.JiraTemplate(**template)

    logger.info("Yaml file loaded...")
    # we validate if the user entered unique object_ids for different actions in the
    # template. Each object_id references a action or a trigger, which in turn references
    # their results (a ticket or a results of a search)
    validate_uniqueness_of_object_ids(jira_template)

    return jira_template


def search_issues(
    jira_template: joft.models.JiraTemplate, jira_session: jira.JIRA
) -> jira.client.ResultList[jira.Issue]:
    if not jira_template.jira_search:
        raise ValueError("No search query defined in template")
    return cast(
        jira.client.ResultList[jira.Issue],
        jira_session.search_issues(jira_template.jira_search.jql),
    )


def list_issues(template_file_path: str, jira_session: jira.JIRA) -> str:
    jira_template = load_and_validate_template(template_file_path)

    trigger_result = search_issues(jira_template, jira_session)

    if not trigger_result:
        return "No issues found."

    table_result = [[issue.key, issue.permalink()] for issue in trigger_result]

    return tabulate.tabulate(table_result, ["Key", "URL"])


def execute_template(template_file_path: str, jira_session: jira.JIRA) -> int:
    """Execute a JIRA template file, processing all defined actions.

    This function handles two main execution modes:
    1. Triggered execution: If the template contains a jira_search (trigger),
       the actions are executed once for each JIRA issue found by the search query.
    2. Direct execution: If no trigger is defined, the actions are executed once.

    The execution process:
    1. Loads and validates the template file
    2. If a trigger is present:
       - Executes the JIRA search query
       - For each matching issue, executes all actions with the issue as context
       - If no issues are found, logs a message and exits
    3. If no trigger is present:
       - Executes all actions once without any trigger context

    Args:
        template_file_path (str): Path to the YAML template file to execute
        jira_session (jira.JIRA): Active JIRA client session for making API calls

    Returns:
        int: Returns 0 on successful execution

    Raises:
        yaml.YAMLError: If the template file contains invalid YAML syntax
        pydantic.ValidationError: If the template structure doesn't match JiraTemplate model
        Exception: If duplicate object_ids are found in the template
        jira.exceptions.JIRAError: If JIRA API operations fail
    """

    jira_template = load_and_validate_template(template_file_path)

    # the trigger is not mandatory for action execution. This means that you dont need to
    # start your jira template with a trigger. If no trigger is present the actions will be
    # executed only once.
    if jira_template.jira_search:
        trigger_result = search_issues(jira_template, jira_session)

        if not trigger_result:
            logger.info(
                (
                    "No tickets found according to the provided jira query "
                    f"'{jira_template.jira_search.jql}'!"
                )
            )
            return 0

        # when the jira query is successfull the actions of template will be then executed
        # for each ticket in the query
        execute_actions_per_trigger_ticket(trigger_result, jira_template, jira_session)
        return 0

    # if there is no trigger defined the actions are executed once
    execute_actions(jira_template, jira_session)
    return 0


def execute_actions(
    jira_template: joft.models.JiraTemplate,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType = {},
) -> None:
    """Execute a sequence of JIRA actions defined in the template.

    This function processes each action in the template sequentially, executing them based on their type.
    For each action, a deep copy is created to ensure references are properly maintained between runs.

    Supported action types:
    - create-ticket: Creates a new JIRA issue
    - update-ticket: Updates an existing JIRA issue
    - link-issues: Creates links between JIRA issues
    - transition: Performs a workflow transition on a JIRA issue

    The reference_pool is used to store and share data between actions, allowing actions to reference
    results from previous actions or trigger data.

    Args:
        jira_template (joft.models.JiraTemplate): Template containing the actions to execute
        jira_session (jira.JIRA): Active JIRA client session for making API calls
        reference_pool (ReferencePoolType, optional): Dictionary storing shared data between actions.
            Maps reference IDs to their values. Defaults to empty dict.

    Raises:
        jira.exceptions.JIRAError: If any JIRA API operation fails
        ValueError: If action references are invalid or missing
        Exception: If action execution fails for any other reason

    Note:
        Unknown action types are logged as warnings and skipped.
    """
    for action in jira_template.jira_actions:
        # we deep copy each action from the template
        # each run of all the actions needs each action to retain its references
        # the references are replaced and filled in when the action is executed
        match action.type:
            case "create-ticket":
                joft.actions.create_ticket(
                    cast(joft.models.CreateTicketAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )
            case "update-ticket":
                joft.actions.update_ticket(
                    cast(joft.models.UpdateTicketAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )
            case "link-issues":
                joft.actions.link_issues(
                    cast(joft.models.LinkIssuesAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )
            case "transition":
                joft.actions.transition_issue(
                    cast(joft.models.TransitionAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )
            case _:
                logger.warning(f"Unknown action type: {action.type}")


def execute_actions_per_trigger_ticket(
    trigger_result: List[jira.Issue],
    jira_template: joft.models.JiraTemplate,
    jira_session: jira.JIRA,
) -> None:
    """Function which executes the action for each ticket found in a trigger query."""

    if not jira_template.jira_search:
        raise ValueError("No search query defined in template")

    # reference_pool holds information about data which was referenced by object ids in the
    # current run.
    # A trigger object_id references the current processed ticket of a jql query.
    # A action object_id references the result of an action. For example the result
    # of a create-ticket action is the created ticket.
    # The reference pool should be shared between all actions so they can reference data
    # from it through 'reuse-data' sections and reuse the data from the referenced objects
    reference_pool: ReferencePoolType = {}

    for ticket in trigger_result:
        reference_pool[jira_template.jira_search.object_id] = ticket
        execute_actions(jira_template, jira_session, reference_pool)
        reference_pool = {}


def validate_uniqueness_of_object_ids(jira_template: joft.models.JiraTemplate) -> None:
    """Validate check if the object ids defined by the user are unique."""

    object_ids: List[str] = []

    if jira_template.jira_search:
        object_ids.append(jira_template.jira_search.object_id)

    for action in jira_template.jira_actions:
        if action.object_id:
            object_ids.append(action.object_id)

    # check if all the object ids are unique
    if len(object_ids) != len(set(object_ids)):
        duplicate_id: str = max(object_ids, key=object_ids.count)
        err_msg = (
            "The validation of the property 'object_id' has failed. "
            f"The object_id with the value '{duplicate_id}' has been "
            "defined as the 'object_id' for 2 or more objects!"
        )
        raise Exception(err_msg)


def validate_template(template_file_path: str) -> int:
    """Validate a JIRA template file for correct structure and unique object IDs.

    This function loads and validates a YAML template file to ensure it:
    1. Has valid YAML syntax
    2. Matches the expected JiraTemplate structure
    3. Contains unique object_ids across all actions and triggers

    Args:
        template_file_path (str): Path to the YAML template file to validate

    Returns:
        int: Returns 0 if validation succeeds

    Raises:
        Exception: If duplicate object_ids are found in the template
        yaml.YAMLError: If the template file contains invalid YAML syntax
        pydantic.ValidationError: If the template structure doesn't match JiraTemplate model
    """
    template: Dict[str, Any] = joft.utils.load_and_parse_yaml_file(template_file_path)
    jira_template = joft.models.JiraTemplate(**template)
    validate_uniqueness_of_object_ids(jira_template)
    return 0


def update_reference_pool(
    reference_data: List[joft.models.ReferenceData],
    reference_pool: ReferencePoolType,
) -> None:
    """Update the reference pool with field values from referenced JIRA issues.

    This function processes a list of reference data specifications and updates the reference pool
    with values extracted from JIRA issues. It handles various JIRA fields differently based on
    their data structure:
    - Simple fields (id, key): Direct attribute access
    - URL fields (link, url, permalink): Uses permalink() method
    - Complex fields (priority, components): Extracts specific nested attributes
    - Project field: Extracts project key
    - Other fields: Accessed through issue.fields

    Args:
        reference_data (List[joft.models.ReferenceData]): List of reference specifications
            defining which fields to extract from which referenced issues
        reference_pool (ReferencePoolType): Dictionary storing referenced values, mapping
            reference IDs to their corresponding values (str, jira.Issue, or List)

    Raises:
        Exception: If a reference_id is used before it was declared in the reference pool
        AttributeError: If a specified field doesn't exist on the JIRA issue
    """
    for ref in reference_data:
        if ref.reference_id not in reference_pool:
            raise Exception(
                f"The reference id '{ref.reference_id}' is used before it was declared."
            )

        ref_object = cast(jira.Issue, reference_pool[ref.reference_id])

        # different fields have a different location in the jira issue object
        # we need to appropriate this when extracting the values
        for field in ref.fields:
            match field:
                case "id" | "key":
                    reference_pool[f"{ref.reference_id}.{field}"] = getattr(
                        ref_object, field
                    )
                case "link" | "url" | "permalink":
                    reference_pool[f"{ref.reference_id}.{field}"] = (
                        ref_object.permalink()
                    )
                case "priority":
                    reference_pool[f"{ref.reference_id}.{field}"] = (
                        ref_object.fields.priority.name
                    )
                case "components":
                    components: List[ComponentType] = []
                    for component in ref_object.fields.components:
                        components.append({"name": component.name})
                    reference_pool[f"{ref.reference_id}.{field}"] = components
                case "project":
                    reference_pool[f"{ref.reference_id}.{field}"] = getattr(
                        ref_object.fields.project, "key"
                    )
                case _:
                    reference_pool[f"{ref.reference_id}.{field}"] = getattr(
                        ref_object.fields, field
                    )


def apply_reference_pool_to_payload(
    reference_pool: Dict[str, Union[str, jira.Issue | str | List[str]]],
    fields: Any,
) -> None:
    """Apply referenced values from the reference pool to a JIRA payload's fields.

    This function processes a JIRA payload's fields and replaces references (in ${reference} format)
    with their corresponding values from the reference pool. It handles different field types specially:

    Special field handling:
    - components: Replaces entire field value if reference matches
    - project: Handles both 'key' and 'name' subfields
    - issuetype: Updates the 'name' subfield
    - assignee: Updates the 'name' subfield
    - priority: Updates the 'name' subfield
    - labels: Processes each label in the list individually

    For all other fields, direct string replacement of ${reference} patterns is performed.
    Primitive types (int, float, bool) are skipped.

    Args:
        reference_pool (Dict[str, Union[str, jira.Issue | str | List[str]]]): Dictionary containing
            reference IDs mapped to their values. Values can be strings, JIRA issues, or lists.
        fields (Any): Dictionary containing JIRA fields to be updated. Fields may contain
            references in ${reference} format that will be replaced with values from reference_pool.

    Note:
        The function modifies the fields dictionary in-place. References in the format ${reference}
        are replaced with their corresponding values from the reference pool.
    """

    for field in fields:
        # if the value is an simple value (string, int, float, bool) we skip it
        if type(fields[field]) in (int, float, bool):
            continue

        for ref, v in reference_pool.items():
            # TODO: write tests about replacing values and refactor this
            if not isinstance(v, (str, list)):
                continue

            if type(v) is list:
                if field == "components":
                    if f"${{{ref}}}" in fields[field]:
                        fields[field] = v
                        continue

            if type(v) is str:
                # there can be multiple references in one field
                if field == "project":
                    if "key" in fields[field]:
                        fields[field]["key"] = replace_ref(fields[field]["key"], ref, v)
                    elif "name" in fields[field]:
                        fields[field]["name"] = replace_ref(
                            fields[field]["name"], ref, v
                        )
                    continue
                if field == "issuetype":
                    fields[field]["name"] = replace_ref(fields[field]["name"], ref, v)
                    continue
                if field == "assignee":
                    fields[field]["name"] = replace_ref(fields[field]["name"], ref, v)
                    continue
                if field == "priority":
                    fields[field]["name"] = replace_ref(fields[field]["name"], ref, v)
                    continue
                if field == "labels":
                    fields[field] = list(
                        map(
                            lambda label: replace_ref(label, ref, cast(str, v)),
                            fields[field],
                        )
                    )
                    continue

                if ref in fields[field]:
                    fields[field] = replace_ref(fields[field], ref, v)


def replace_ref(field: str, ref: str, value: str) -> str:
    return field.replace("${" + ref + "}", value)

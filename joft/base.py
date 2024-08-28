import copy
import logging
import typing

import jira
import jira.client
import jira.resources
import tabulate

import joft.actions
import joft.models
import joft.utils


def load_and_validate_template(template_file_path: str) -> joft.models.JiraTemplate:
    template: typing.Dict[str, typing.Any] = joft.utils.load_and_parse_yaml_file(
        template_file_path
    )
    jira_template = joft.models.JiraTemplate(**template)

    logging.info("Yaml file loaded...")
    # we validate if the user entered unique object_ids for different actions in the
    # template. Each object_id references a action or a trigger, which in turn references
    # their results (a ticket or a results of a search)
    validate_uniqueness_of_object_ids(jira_template)

    return jira_template


def search_issues(jira_template: joft.models.JiraTemplate, jira_session: jira.JIRA):
    return typing.cast(
        jira.client.ResultList[jira.Issue],
        jira_session.search_issues(jira_template.jira_search.jql),
    )


def list_issues(template_file_path: str, jira_session: jira.JIRA):
    jira_template = load_and_validate_template(template_file_path)

    trigger_result = search_issues(jira_template, jira_session)

    if not trigger_result:
        return "No issues found."

    table_result = [[issue.key, issue.permalink()] for issue in trigger_result]

    return tabulate.tabulate(table_result, ["Key", "URL"])


def execute_template(template_file_path: str, jira_session: jira.JIRA) -> int:
    """Function which starts the whole process of jira template execution"""

    jira_template = load_and_validate_template(template_file_path)

    # the trigger is not mandatory for action execution. This means that you dont need to
    # start your jira template with a trigger. If no trigger is present the actions will be
    # executed only once.
    if jira_template.jira_search:
        trigger_result = search_issues(jira_template, jira_session)

        if not trigger_result:
            logging.info(
                (
                    "No tickets found according to the provided jira query "
                    f"'{jira_template.jira_search.jql}'!"
                )
            )
            return 1

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
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue | str | typing.List[str]]
    ] = {},
) -> None:
    for action in jira_template.jira_actions:
        # we deep copy each action from the template
        # each run of all the actions needs each action to retain its references
        # the references are replaced and filled in when the action is executed
        match action.type:
            case "create-ticket":
                joft.actions.create_ticket(
                    typing.cast(joft.models.CreateTicketAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )
            case "update-ticket":
                joft.actions.update_ticket(
                    typing.cast(joft.models.UpdateTicketAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )
            case "link-issues":
                joft.actions.link_issues(
                    typing.cast(joft.models.LinkIssuesAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )
            case "transition":
                joft.actions.transition_issue(
                    typing.cast(joft.models.TransitionAction, copy.deepcopy(action)),
                    jira_session,
                    reference_pool,
                )


def execute_actions_per_trigger_ticket(
    trigger_result: typing.List[jira.Issue],
    jira_template: joft.models.JiraTemplate,
    jira_session: jira.JIRA,
) -> None:
    """Function which executes the action for each ticket found in a trigger query."""

    # reference_pool holds information about data which was referenced by object ids in the
    # current run.
    # A trigger object_id references the current processed ticket of a jql query.
    # A action object_id references the result of an action. For example the result
    # of a create-ticket action is the created ticket.
    # The reference pool should be shared between all actions so they can reference data
    # from it through 'reuse-data' sections and reuse the data from the referenced objects
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue | str | typing.List[str]]
    ] = {}

    for ticket in trigger_result:
        reference_pool[jira_template.jira_search.object_id] = ticket
        execute_actions(jira_template, jira_session, reference_pool)
        reference_pool = {}


def validate_uniqueness_of_object_ids(jira_template: joft.models.JiraTemplate) -> None:
    """Validate check if the object ids defined by the user are unique."""

    object_ids: typing.List[str] = []

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
    template: typing.Dict[str, typing.Any] = joft.utils.load_and_parse_yaml_file(
        template_file_path
    )
    jira_template = joft.models.JiraTemplate(**template)
    validate_uniqueness_of_object_ids(jira_template)
    return 0


def update_reference_pool(
    reference_data: typing.List[joft.models.ReferenceData],
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue, typing.List[typing.Any]]
    ],
):
    """We update the reference_pool with the references from the reuse_data section"""

    for ref in reference_data:
        if ref.reference_id not in reference_pool:
            raise Exception(
                f"The reference id '{ref.reference_id}' is used before it was declared."
            )

        ref_object = typing.cast(jira.Issue, reference_pool[ref.reference_id])

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
                    reference_pool[f"{ref.reference_id}.{field}"] = []
                    for component in ref_object.fields.components:
                        typing.cast(
                            list, reference_pool[f"{ref.reference_id}.{field}"]
                        ).append({"name": component.name})
                case "project":
                    reference_pool[f"{ref.reference_id}.{field}"] = getattr(
                        ref_object.fields.project, "key"
                    )
                case _:
                    reference_pool[f"{ref.reference_id}.{field}"] = getattr(
                        ref_object.fields, field
                    )


def apply_reference_pool_to_payload(
    reference_pool: typing.Dict[
        str, typing.Union[str, jira.Issue | str | typing.List[str]]
    ],
    fields: typing.Any,
) -> None:
    """
    Apply the reference_pool to the payload that will be sent to Jira via REST request.
    It means each reference which is found in the 'fields' section of an action, will be
    replaced by the value which is referenced by the same reference in the reference_pool
    """

    for field in fields:
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
                            lambda label: replace_ref(label, ref, typing.cast(str, v)),
                            fields[field],
                        )
                    )
                    continue

                if ref in fields[field]:
                    fields[field] = replace_ref(fields[field], ref, v)


def replace_ref(field: str, ref: str, value: str) -> str:
    return field.replace("${" + ref + "}", value)

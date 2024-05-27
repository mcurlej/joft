import copy
import logging
import typing

import jira
import jira.client
import jira.resources

import joft.actions
import joft.models
import joft.utils


def execute_template(template_file_path: str, jira_session: jira.JIRA) -> None:
    """ Function which starts the whole process of jira template execution """

    template: typing.Dict[str, typing.Any] = joft.utils.load_and_parse_yaml_file(template_file_path)
    jira_template = joft.models.JiraTemplate(**template)
    
    logging.info("Yaml file loaded...")
    # we validate if the user entered unique object_ids for different actions in the 
    # template. Each object_id references a action or a trigger, which in turn references
    # their results (a ticket or a results of a search)
    validate_uniqueness_of_object_ids(jira_template) 

    # the trigger is not mandatory for action execution. This means that you dont need to
    # start your jira template with a trigger. If no trigger is present the actions will be
    # executed only once.
    if jira_template.jira_search:
        trigger_result = typing.cast(jira.client.ResultList[jira.Issue],
                                     jira_session.search_issues(jira_template.jira_search.jql))

        if not trigger_result:
            # TODO: dont raise but log error and exit the script
            raise Exception("No tickets found!")

        # when the jira query is successfull the actions of template will be then executed
        # for each ticket in the query
        execute_actions_per_trigger_ticket(trigger_result, jira_template, jira_session)

    # if there is no trigger defined the actions are executed once
    execute_actions(jira_template, jira_session)


def execute_actions(jira_template: joft.models.JiraTemplate, 
                    jira_session: jira.JIRA,
                    reference_pool: typing.Dict[str, typing.Union[str, jira.Issue | str | typing.List[str]]] = {}):
    
    for action in jira_template.jira_actions:
        # we deep copy each action from the template
        # each run of all the actions needs each action to retain its references
        # the references are replaced and filled in when the action is executed
        if action.type == "create-ticket":
            joft.actions.create_ticket(typing.cast(joft.models.CreateTicketAction, copy.deepcopy(action)), 
                                           jira_session, reference_pool)
        elif action.type == "update-ticket":
            joft.actions.update_ticket(typing.cast(joft.models.UpdateTicketAction, copy.deepcopy(action)),
                                           jira_session, reference_pool)
        elif action.type == "link-issues":
            joft.actions.link_issues(typing.cast(joft.models.LinkIssuesAction, copy.deepcopy(action)), 
                                         jira_session, reference_pool)
        else:
            raise Exception(f"Undocumented action type '{action.type}' aborting!")



def execute_actions_per_trigger_ticket(trigger_result: typing.List[jira.Issue], 
                                       jira_template: joft.models.JiraTemplate,
                                       jira_session: jira.JIRA):
    """ Function which executes the action for each ticket found in a trigger query. """
    
    # reference_pool holds information about data which was referenced by object ids in the
    # current run.
    # A trigger object_id references the current processed ticket of a jql query.
    # A action object_id references the result of an action. For example the result 
    # of a create-ticket action is the created ticket.
    # The reference pool should be shared between all actions so they can reference data
    # from it through 'reuse-data' sections and reuse the data from the referenced objects
    reference_pool: typing.Dict[str, typing.Union[str, jira.Issue | str | typing.List[str]]] = {}

    for ticket in trigger_result:
        reference_pool[jira_template.jira_search.object_id] = ticket
        execute_actions(jira_template, jira_session, reference_pool)
        reference_pool = {}
        import pdb; pdb.set_trace()


def validate_uniqueness_of_object_ids(jira_template: joft.models.JiraTemplate):
    """ Validate check if the object ids defined by the user are unique. """

    object_ids: typing.List[str] = []

    if jira_template.jira_search:
        object_ids.append(jira_template.jira_search.object_id)

    for action in jira_template.jira_actions:
        object_ids.append(action.object_id)

    # check if all the object ids are unique
    if len(object_ids) != len(set(object_ids)):
        duplicate_id: str = max(object_ids, key = object_ids.count)
        raise Exception((f"The validation of the property 'object_id' has failed. "
                         "The object_id with the value '{duplicate_id}' has been "
                         "defined as the 'object_id' for 2 or more objects!"))
    

def validate_template(template_file_path: str):
    template: typing.Dict[str, typing.Any] = joft.utils.load_and_parse_yaml_file(template_file_path)
    jira_template = joft.models.JiraTemplate(**template)
    validate_uniqueness_of_object_ids(jira_template)


def update_reference_pool(reuse_data: typing.List[joft.models.ReferenceData], 
                          reference_pool: typing.Dict[str, typing.Union[str, jira.Issue, typing.List[typing.Any]]]):
    """ We update the reference_pool with the references from the reuse_data section """

    for data in reuse_data:
        if data.reference_id not in reference_pool:
            raise Exception(f"The reference id '{data.reference_id}' is used before it was declared.")
        
        ref_object = typing.cast(jira.Issue, reference_pool[data.reference_id])

        # different fields have a different location in the jira issue object
        # we need to appropriate this when extracting the values
        if data.field in ["id", "key"]:
            reference_pool[f"{data.reference_id}.{data.field}"] = getattr(ref_object, data.field)
        elif data.field in ["link", "url", "permalink"]:
            reference_pool[f"{data.reference_id}.{data.field}"] = ref_object.permalink()
        elif data.field in ["priority"]:
            reference_pool[f"{data.reference_id}.{data.field}"] = ref_object.fields.priority.name
        elif data.field in ["components"]:
            reference_pool[f"{data.reference_id}.{data.field}"] = []
            for component in ref_object.fields.components:
                typing.cast(list, reference_pool[f"{data.reference_id}.{data.field}"]).append({"name": component.name})
        else:
            reference_pool[f"{data.reference_id}.{data.field}"] = getattr(ref_object.fields, data.field)


def apply_reference_pool_to_payload(reference_pool: typing.Dict[str, typing.Union[str, jira.Issue | str | typing.List[str]]],
                                    fields: typing.Any):
    for field in fields:
        for ref, v in reference_pool.items():
            # TODO: write tests about replacing values and refactor this
            if not type(v) in [str, list]:
                continue

            if type(v) is list:
                if field == "components":
                    if f"${{{ref}}}" in fields[field]:
                        fields[field] = v
                        continue

            if type(v) is str:
                if field == "project":
                    fields[field]["key"] = replace_ref(fields[field]["key"], ref, v)
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
                    fields[field] = list(map(lambda label: replace_ref(label, ref, v), fields[field]))
                    continue
                
                # replace if there is a reference there. If not the fields
                # was alredy updated
                if ref in fields[field]:
                    fields[field] = replace_ref(fields[field], ref, v)


def replace_ref(field, ref, value):
    return field.replace("${" + ref + "}", value)
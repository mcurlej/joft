### Table of contents

1. [Yaml template file introductory example](introduction.md)
2. [Actions YAML API](actions.md)

# Yaml template file introductory example

This example creates an epic for each found bug by the JQL query. Then it links the two tickets through a "is caused by"/"causes" link.

```
api_version: 1
kind: jira-template
metadata:
  name: "Create Epic for each bug found in project"
  description: "TBA"
trigger:
  type: jira-jql-search
  object_id: "issue"
  jql: >
    project in (Project1) AND issuetype in (Bug) AND status in ("New")
actions:
- object_id: "bug-epic"
  type: create-ticket
  reuse_data:
    - reference_id: "issue"
      fields: 
      - "priority"
      - "components"
      - "summary"
      - "key"
  fields:
    project: 
      key: "Project2"
    issuetype:
      name: "Epic"
    description: "Original bug: ${issue.link}"
    summary: "${issue.summary}"
    labels: 
      - "bug-epic"
    components: "${issue.components}"
    priority: 
      name: "${issue.priority}"
    customfield_12311141: "${issue.summary}" # Epic name custom field
- type: link-issues
  object_id: "link-bug-and-epic"
  reuse_data:
    - reference_id: "bug-epic"
      fields: 
      - "key"
  fields:
    type: "causes"
    inward_issue: "${issue.key}"
    outward_issue: "${bug-epic.key}"
```

## Trigger section

The `trigger` section describes the JQL query that will find the issues in a Jira instance you want to execute your actions on. `trigger` has an `object_id` property which holds the value of reference for each issue found by the JQL query. Each `object_id` can be then used as a reference in the `reuse_data` section of each action. The `trigger` does not have a `reuse_data` of `fields` section. All the `object_id` property values need to be unique in the whole yaml file. There is only one trigger per YAML file. The trigger is not mandatory, but then all the actions will be executed once.

```
trigger:
  type: jira-jql-search
  object_id: "issue"
  jql: >
    project in (Project1) AND issuetype in (Bug) AND status in ("New")
```

## Action section

The `actions` section holds all the actions that will be executed for each issue found by the JQL query. Actions are executed from top to bottom by the order as they are written in the YAML file. Each action will be executed once. An action can have a `object_id`. If an action does not have a `object_id` it can not be referenced in the `reuse_data` section.

## Reuse Data section

The `reuse_data` section is a place where you can reference values from issues that you are currently working with in the current execution run of the template.

For example, the `trigger` section has the `object_id` value set to `issue`. This value is arbitrary and can be a string of your choosing. This value will represent one of the issues that the JQL query has found. All actions defined in the `actions` section will execute once for each such issue. So the `issue` id will always hold the data about the current issue from the JQL query the actions are executing for. 

In each action we can then access this data through a `reference_id` in the `reuse_data` section. Each reference in the `reuse_data` section consists of a `reference_id` and `field` property. The `reference_id` represents an `object_id` defined on a trigger JQL query or on another action. The `field` property represents the name of field on and issue referenced by the `reference_id`. When you look at the example below, you can see how we are referencing values from the current issue from the JQL query and reusing them in the `fields` section. You can NOT reference an `object_id` before it was declared. Defined `object_id` can be only referenced in `reuse_data` section of the next actions that comes after the action/trigger query where the `object_id` was declared.

```
actions:
- object_id: "bug-epic"
  type: create-ticket
  reuse_data:
    - reference_id: "issue"
      fields: 
      - "priority"
      - "components"
      - "summary"
      - "key"
  fields:
    project: 
      key: "Project2"
    issuetype:
      name: "Epic"
    description: "Original bug: ${issue.link}"
    summary: "${issue.summary}"
    labels: 
      - "bug-epic"
    components: "${issue.components}"
    priority: 
      name: "${issue.priority}"
    customfield_12311141: "${issue.summary}" # Epic name custom field
- type: link-issues
  object_id: "link-bug-and-epic"
  reuse_data:
    - reference_id: "bug-epic"
      fields: 
      - "key"
  fields:
    type: "causes"
    inward_issue: "${issue.key}"
    outward_issue: "${bug-epic.key}"
```

## Fields section

The `fields` section represents the values (payload) we are sending to the Jira server through the REST API. We are using the official Jira python module for accesing the Jira REST API. The `fields` section is modeled according to the Jira python API the module is using. (Here can find the [API docs](https://jira.readthedocs.io/api.html)) Not all fields are the same in Jira. They have different types and structures. The `fields` section is one big dictionary which represents the REST request data being sent through the Jira python plugin to the server.

If we have something referenced in the `reuse_data` section, we can reference it the `fields` section as described below in the YAML example. When a template is executed the `fields` section can reference only data which is already present in the `reuse_data` section of the current or previous actions. If current or any previous action has already some data referenced in its `reuse_data` section this data can be referenced in the current or future actions without having the need to reference it again in future actions. Everywhere the the tool finds `${...}` tags in the `fields` section it will convert it to its value which is referenced from an issue. 

The first action is `create-ticket` action it creates an `epic` for each bug the JQL query founds. When you look at the `fields` section you see that we want that the `summary` of the new Jira Epic will be the same as the bug we reference from the JQL query.

The second action which links the epic and the bug through a Jira "causes" link. As you can see in the `fields` section we are referencing values from the current issue (with `object_id` "issue") from the JQL query and the newly created epic for that issue (with `object_id` "bug-epic"). The "key" value of the issue `issue.key` is referenced in the first action's `reuse_data` section and the Epic's "key" value `bug-epic.key` is referenced in the second action's `reuse_data` section





### Table of contents

1. [Yaml template file introductory example](introduction.md)
2. [Actions](actions.md)

# Actions

Small examples of the actions available. Keep in mind that all the `object_id` properties in a YAML template file need to be unique.

NOTE: Just keep in mind that the fields and values can change or be different. Your Jira instance can be different then mine Jira instance.

## create-ticket

The `create-ticket` action will create a ticket in your Jira instance. The action can have a `object_id`. If the `object` is not present the newly created issue can not be referenced in future actions.

The payload in the `fields` section is modeled after the input dict the Jira python API requires. More on this [here](https://jira.readthedocs.io/api.html)

The `create-ticket` has mandatory fields that need to be present in the `fields` section:

```
    project: 
      key: "<key of your project>"
    issuetype:
      name: "<type of the issue>"
    description: "<description of issue>"
    summary: "<summary of issue>"
```

Example of `create-ticket` action:

```
- object_id: "bug-epic"
  type: create-ticket
  reuse_data:
    - reference_id: "issue"
      fields: 
      - "link"
      - "components"
      - "summary"
      - "key"
  fields:
    project: 
      key: "Project"
    issuetype:
      name: "Epic"
    description: "Original bug: ${issue.link}"
    summary: "${issue.summary}"
    labels: 
      - "bug-epic"
    components: "${issue.components}"
    priority: 
      name: "${issue.priority}"
    customfield_12311141: "${issue.summary}" # Epic Name Custom Field
```

## update-ticket

An `update-ticket` action has a special property called `reference_id` which references an issue from the trigger or a previous action. The `update-action` does not have mandatory fields in the `fields` section but the section can not be empty. The action can have a `reuse-data` section but the updated ticket should be already referenced previously, because without a reference you can not update it in the first place.


Example of `update-action`.

```
- object_id: "update-story-build"
  type: update-ticket
  reference_id: "story-build"
  fields:
    customfield_12311140: "${bug-epic.key}"
```

## link-issues

Link action links 2 issues together. You need to reference both ids of the issues you want to link. The `inward_issue` is the issue you want to link from and the `outward_issue` represents the issue you want to link to. The `type` defines the type of the nature of the link. You can find those in your Jira instance.

Example of `link-issues` action.

```
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

## transition

The `transition` action changes the status of the issue and adds a comment to that issue. The `reference_id` represents a referenced issue from previous actions/trigger. The `transition` field represents the name or id of the desired status you want this issue to be transitioned to.

Example of `transition` action

```
api_version: 1
kind: jira-template
metadata:
  name: "Close a bug with comment"
  description: "TBA"
trigger:
  type: jira-jql-search
  object_id: "issue"
  jql: project = Project and issuetype = bug
actions:
- object_id: "close-bug" 
  type: transition
  reference_id: "issue"
  transition: "Closed"
  comment: "Closed by joft with the transition action with this comment!"
  fields:
    resolution:
      name: "Not a Bug"
```
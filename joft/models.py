import dataclasses
from typing import Dict, Any, List, Optional


@dataclasses.dataclass
class Trigger:
    type: str
    object_id: str
    jql: str


@dataclasses.dataclass
class ReferenceData:
    reference_id: str
    fields: List[str]


@dataclasses.dataclass(kw_only=True)
class Action:
    # required fields
    type: str
    fields: Dict[str, Any]

    def reuse_data_must_be_list(
        self, reuse_data: Dict[str, Any] | List[Dict[str, Any]]
    ) -> None:
        """Validate that reuse_data is a list.

        Args:
            reuse_data: The data to validate

        Raises:
            Exception: If reuse_data is not a list
        """
        reuse_data_type = type(reuse_data)

        if reuse_data_type is not list:
            raise Exception(
                f"Reuse data is a '{reuse_data_type}' type, must be a list."
            )


@dataclasses.dataclass(kw_only=True)
class CreateTicketAction(Action):
    reuse_data: dataclasses.InitVar[Optional[List[Dict[str, Any]]]] = None
    object_id: Optional[str] = None

    reference_data: List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data: Optional[List[Dict[str, Any]]]) -> None:
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass(kw_only=True)
class UpdateTicketAction(Action):
    reference_id: str
    object_id: Optional[str] = None
    reuse_data: dataclasses.InitVar[Optional[List[Dict[str, Any]]]] = None

    reference_data: List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data: Optional[List[Dict[str, Any]]]) -> None:
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass(kw_only=True)
class LinkIssuesAction(Action):
    reuse_data: dataclasses.InitVar[Optional[List[Dict[str, Any]]]] = None
    object_id: Optional[str] = None

    reference_data: List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data: Optional[List[Dict[str, Any]]]) -> None:
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass(kw_only=True)
class TransitionAction(Action):
    reference_id: str
    transition: str
    comment: str
    object_id: Optional[str] = None
    reuse_data: dataclasses.InitVar[Optional[List[Dict[str, Any]]]] = None

    reference_data: List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data: Optional[List[Dict[str, Any]]]) -> None:
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass
class JiraTemplate:
    api_version: int
    kind: str

    # initvars
    actions: dataclasses.InitVar[List[Dict[str, Any]]]
    trigger: dataclasses.InitVar[Dict[str, Any]]

    # with default values processed in __post_init__
    jira_actions: List[
        CreateTicketAction | UpdateTicketAction | LinkIssuesAction | TransitionAction
    ] = dataclasses.field(default_factory=list)

    metadata: Optional[Dict[str, str]] = None
    jira_search: Optional[Trigger] = None

    def __post_init__(
        self, actions: List[Dict[str, Any]], trigger: Optional[Dict[str, Any]]
    ) -> None:
        if trigger:
            self.jira_search = Trigger(**trigger)

        # TODO: all init vars need to be checked for correct types and raise if it is not so.
        for action in actions:
            match action["type"]:
                case "create-ticket":
                    self.jira_actions.append(CreateTicketAction(**action))
                case "update-ticket":
                    self.jira_actions.append(UpdateTicketAction(**action))
                case "link-issues":
                    self.jira_actions.append(LinkIssuesAction(**action))
                case "transition":
                    self.jira_actions.append(TransitionAction(**action))
                case _:
                    raise Exception(f"Unknown Action '{action['type']}'! Aborting...")

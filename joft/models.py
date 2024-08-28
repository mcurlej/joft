import dataclasses
import typing


@dataclasses.dataclass
class Trigger:
    type: str
    object_id: str
    jql: str


@dataclasses.dataclass
class ReferenceData:
    reference_id: str
    fields: list[str]


@dataclasses.dataclass(kw_only=True)
class Action:
    # required fields
    type: str
    fields: typing.Dict[str, typing.Any]

    def reuse_data_must_be_list(self, reuse_data):
        reuse_data_type = type(reuse_data)

        if reuse_data_type is not list:
            raise Exception(
                f"Reuse data is a '{reuse_data_type}' type, must be a list."
            )


@dataclasses.dataclass(kw_only=True)
class CreateTicketAction(Action):
    reuse_data: dataclasses.InitVar[typing.List[ReferenceData] | None] = None
    object_id: str | None = None

    reference_data: typing.List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data):
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass(kw_only=True)
class UpdateTicketAction(Action):
    reference_id: str
    object_id: str | None = None
    reuse_data: dataclasses.InitVar[typing.List[ReferenceData] | None] = None

    reference_data: typing.List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data):
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass(kw_only=True)
class LinkIssuesAction(Action):
    reuse_data: dataclasses.InitVar[typing.List[ReferenceData] | None] = None
    object_id: str | None = None

    reference_data: typing.List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data):
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass(kw_only=True)
class TransitionAction(Action):
    reference_id: str
    transition: str
    comment: str
    object_id: str | None = None
    reuse_data: dataclasses.InitVar[typing.List[ReferenceData] | None] = None

    reference_data: typing.List[ReferenceData] = dataclasses.field(default_factory=list)

    def __post_init__(self, reuse_data):
        if reuse_data:
            self.reuse_data_must_be_list(reuse_data)

            for data in reuse_data:
                self.reference_data.append(ReferenceData(**data))


@dataclasses.dataclass
class JiraTemplate:
    api_version: int
    kind: str

    # initvars
    actions: dataclasses.InitVar[typing.List[typing.Dict[str, typing.Any]]]
    trigger: dataclasses.InitVar[Trigger]

    # with default values procesed in __post_init__
    jira_actions: list[
        CreateTicketAction | UpdateTicketAction | LinkIssuesAction | TransitionAction
    ] = dataclasses.field(default_factory=list)

    metadata: typing.Dict[str, str] | None = None

    def __post_init__(self, actions, trigger) -> None:
        if trigger:
            self.jira_search: Trigger = Trigger(**trigger)

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

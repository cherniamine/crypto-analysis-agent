from typing import TypedDict, Any
class AgentState(TypedDict, total=False):
    question: str
    history: list[dict]
    tools_needed: list[str]
    observations: dict[str, Any]
    answer: str
    evidence: list[dict]
    activity: list[dict]

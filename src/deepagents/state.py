from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import NotRequired, Annotated, Dict, Any, List
from typing import Literal
from typing_extensions import TypedDict


class Todo(TypedDict):
    """Todo to track."""

    content: str
    status: Literal["pending", "in_progress", "completed"]


class PlanInfo(TypedDict):
    """Information about a plan."""
    
    id: str
    type: str
    title: str
    description: str
    sections: List[Dict[str, Any]]
    status: Literal["pending", "approved", "rejected", "modified"]
    feedback: NotRequired[str]


def file_reducer(l, r):
    if l is None:
        return r
    elif r is None:
        return l
    else:
        return {**l, **r}


def plan_reducer(l, r):
    """Reducer for plans - combines and deduplicates by ID."""
    if l is None:
        return r
    elif r is None:
        return l
    else:
        # Merge plans, with right side taking precedence for duplicates
        combined = {plan['id']: plan for plan in l}
        combined.update({plan['id']: plan for plan in r})
        return list(combined.values())


class DeepAgentState(AgentState):
    todos: NotRequired[list[Todo]]
    files: Annotated[NotRequired[dict[str, str]], file_reducer]
    pending_plans: Annotated[NotRequired[List[PlanInfo]], plan_reducer]
    pending_plan: NotRequired[PlanInfo]
    approved_plan: NotRequired[PlanInfo]
    current_plan: NotRequired[PlanInfo]
    plan_review_data: NotRequired[Dict[str, Any]]
    analysis_results: NotRequired[Dict[str, Any]]
    documentation_requirements: NotRequired[List[str]]
    target_audience: NotRequired[str]

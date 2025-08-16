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


class ContextMetrics(TypedDict):
    """Metriche del contesto conversazionale."""
    tokens_used: int
    max_context_window: int
    utilization_percentage: float
    trigger_threshold: float
    mcp_noise_percentage: float
    deduplication_potential: float


class CleaningResult(TypedDict):
    """Risultato di un'operazione di pulizia."""
    original_size: int
    cleaned_size: int
    reduction_percentage: float
    strategy_used: str
    cleaning_status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    preserved_fields: List[str]
    removed_fields: List[str]
    timestamp: str
    metadata: Dict[str, Any]


class ContextInfo(TypedDict):
    """Informazioni storiche sul contesto."""
    session_id: str
    operation_type: str  # "cleaning", "compaction", "deduplication"
    before_metrics: ContextMetrics
    after_metrics: ContextMetrics
    cleaning_results: List[CleaningResult]
    timestamp: str


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


def context_history_reducer(l, r):
    """Reducer for context history - appends new entries."""
    if l is None:
        return r
    elif r is None:
        return l
    else:
        # Combine context history lists
        return l + r


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
    
    # Context Management Fields
    context_history: Annotated[NotRequired[List[ContextInfo]], context_history_reducer]
    cleaned_context: NotRequired[Dict[str, Any]]
    context_metrics: NotRequired[ContextMetrics]
    mcp_tool_results: NotRequired[Dict[str, Any]]
    context_cleaning_enabled: NotRequired[bool]
    context_session_id: NotRequired[str]

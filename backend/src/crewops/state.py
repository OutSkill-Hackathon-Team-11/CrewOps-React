"""
CrewOps State Schema.

Uses TypedDict (NOT Pydantic BaseModel) because LangGraph requires
TypedDict for Annotated[list, operator.add] reducers to work correctly
in parallel fan-out branches.
"""
from typing import TypedDict, Annotated
from operator import add


def _merge_pipeline_status(a: dict, b: dict) -> dict:
    """
    Reducer for pipeline_status: merge two dicts so parallel nodes
    (e.g. jira + notification) can both write their status without conflict.
    Later keys win (b overrides a on collision).
    """
    merged = dict(a)
    merged.update(b)
    return merged


class CrewOpsState(TypedDict):
    """
    Shared state passed between all LangGraph agent nodes.
    List fields use `operator.add` reducer to safely merge
    results from parallel branches without data loss.
    """
    # ── Input ──────────────────────────────────────────────
    raw_logs: str                              # Original log content (text/file)
    metadata: dict                             # File info, upload timestamp, user

    # ── Classification (Classifier Agent) ──────────────────
    log_summary: str                           # Structured analysis report
    log_type: str                              # k8s, nginx, cloudwatch, application, mixed

    # ── Severity (Severity Agent) ───────────────────────────
    severity: str                              # P1, P2, P3, P4
    severity_rationale: str                    # Why this severity was assigned
    critical_issues: Annotated[list, add]      # Issues flagged as P1/P2

    # ── Root Cause (RCA Agent + RAG) ───────────────────────
    rag_context: Annotated[list, add]          # Retrieved KB documents
    root_cause_analysis: str                   # Full RCA report

    # ── Remediation (Remediation Agent) ────────────────────
    remediation_plan: str                      # Detailed remediation report

    # ── Cookbook (Cookbook Agent) ───────────────────────────
    cookbook: str                              # Operational runbook/SOP

    # ── Human Approval ─────────────────────────────────────
    approval_required: bool                    # True for P1/P2
    approval_status: str                       # pending | approved | auto_approved | rejected

    # ── JIRA (JIRA Agent) ──────────────────────────────────
    jira_tickets: Annotated[list, add]         # Created ticket references

    # ── Notifications (Notification Agent) ─────────────────
    notifications_sent: Annotated[list, add]   # Delivery receipts

    # ── Pipeline Metadata ──────────────────────────────────
    pipeline_status: Annotated[dict, _merge_pipeline_status]  # Per-agent timing + status
    errors: Annotated[list, add]               # Error accumulator (non-fatal)


# ── Required state fields (must be present at graph entry) ──
REQUIRED_INPUT_FIELDS = {"raw_logs", "metadata"}

# ── All state field names ──
ALL_STATE_FIELDS = set(CrewOpsState.__annotations__.keys())

# ── List fields that use operator.add reducer ──
LIST_FIELDS_WITH_REDUCERS = {
    "critical_issues",
    "rag_context",
    "jira_tickets",
    "notifications_sent",
    "errors",
}

# ── Dict fields that use custom merge reducer ──
DICT_FIELDS_WITH_REDUCERS = {"pipeline_status"}

# ── All fields with any reducer ──
FIELDS_WITH_REDUCERS = LIST_FIELDS_WITH_REDUCERS | DICT_FIELDS_WITH_REDUCERS

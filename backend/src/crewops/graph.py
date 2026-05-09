"""
CrewOps LangGraph StateGraph Builder.

Builds and compiles the 7-agent orchestration graph.
Separated here so it can be tested independently without LLMs.
"""
from __future__ import annotations
from typing import Literal

from langgraph.graph import StateGraph, START, END

from crewops.state import CrewOpsState


# ════════════════════════════════════════════════════════════════
# CONDITIONAL ROUTER
# ════════════════════════════════════════════════════════════════

def severity_router(state: CrewOpsState) -> Literal["full_pipeline", "summary_only"]:
    """
    Routes the pipeline after severity assessment:
      P1/P2  → full_pipeline  (RCA + Remediation + JIRA + Notification)
      P3/P4  → summary_only  (Cookbook + Notification only)
    """
    severity = state.get("severity", "P2")
    if severity in ("P1", "P2"):
        print(f"   🔀 Router: {severity} → full pipeline (RCA + JIRA + Notification)")
        return "full_pipeline"
    print(f"   🔀 Router: {severity} → summary only (Cookbook + Notification)")
    return "summary_only"


# ════════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ════════════════════════════════════════════════════════════════

def build_graph(
    classifier_fn=None,
    severity_fn=None,
    root_cause_fn=None,
    remediation_fn=None,
    cookbook_fn=None,
    jira_fn=None,
    notification_fn=None,
):
    """
    Build and compile the CrewOps LangGraph StateGraph.

    Node functions default to the production implementations from
    crewops.agents. Pass custom functions for testing/mocking.

    Returns:
        Compiled LangGraph (CompiledGraph) ready for .invoke() or .stream().
    """
    # Default to production implementations
    if classifier_fn is None:
        from crewops.agents import classifier_node as classifier_fn
    if severity_fn is None:
        from crewops.agents import severity_node as severity_fn
    if root_cause_fn is None:
        from crewops.agents import root_cause_node as root_cause_fn
    if remediation_fn is None:
        from crewops.agents import remediation_node as remediation_fn
    if cookbook_fn is None:
        from crewops.agents import cookbook_node as cookbook_fn
    if jira_fn is None:
        from crewops.agents import jira_node as jira_fn
    if notification_fn is None:
        from crewops.agents import notification_node as notification_fn

    builder = StateGraph(CrewOpsState)

    # Register all 7 agent nodes
    builder.add_node("classifier",   classifier_fn)
    builder.add_node("severity",     severity_fn)
    builder.add_node("root_cause",   root_cause_fn)
    builder.add_node("remediation",  remediation_fn)
    builder.add_node("cookbook",     cookbook_fn)
    builder.add_node("jira",         jira_fn)
    builder.add_node("notification", notification_fn)

    # ── Linear start ──
    builder.add_edge(START, "classifier")
    builder.add_edge("classifier", "severity")

    # ── Conditional branch after severity assessment ──
    builder.add_conditional_edges(
        "severity",
        severity_router,
        {
            "full_pipeline": "root_cause",
            "summary_only":  "cookbook",
        },
    )

    # ── Full pipeline: sequential data dependency chain ──
    builder.add_edge("root_cause",  "remediation")
    builder.add_edge("remediation", "cookbook")

    # ── Parallel fan-out: cookbook feeds both JIRA and Notification ──
    builder.add_edge("cookbook", "jira")
    builder.add_edge("cookbook", "notification")

    # ── Both parallel branches terminate at END ──
    builder.add_edge("jira",         END)
    builder.add_edge("notification", END)

    return builder.compile()


# ════════════════════════════════════════════════════════════════
# GRAPH TOPOLOGY CONSTANTS (used in tests)
# ════════════════════════════════════════════════════════════════

EXPECTED_NODES = {
    "classifier",
    "severity",
    "root_cause",
    "remediation",
    "cookbook",
    "jira",
    "notification",
}

EXPECTED_NODE_COUNT = len(EXPECTED_NODES)   # 7

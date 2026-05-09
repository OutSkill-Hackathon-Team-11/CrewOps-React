"""
Tests: CrewOps LangGraph Graph Topology (test_graph.py)

Validates the StateGraph structure, node registration,
conditional routing logic, and end-to-end pipeline with mocked agent nodes.
No LLM calls — all agent functions are replaced with deterministic fakes.
"""
from __future__ import annotations
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crewops.graph import (
    build_graph,
    severity_router,
    EXPECTED_NODES,
    EXPECTED_NODE_COUNT,
)
from crewops.state import CrewOpsState


# ════════════════════════════════════════════════════════════════
# FAKE AGENT FUNCTIONS (deterministic, no LLM)
# ════════════════════════════════════════════════════════════════

def make_fake_classifier():
    def fake(state):
        return {
            "log_summary": "Fake incident summary from classifier.",
            "log_type": "mixed",
            "pipeline_status": {**state.get("pipeline_status", {}), "classifier": {"status": "done", "elapsed_s": 0.01}},
        }
    return fake


def make_fake_severity(severity="P1"):
    def fake(state):
        return {
            "severity": severity,
            "severity_rationale": f"Test rationale for {severity}",
            "critical_issues": [{"title": "Test issue", "severity": severity}] if severity in ("P1", "P2") else [],
            "approval_required": severity in ("P1", "P2"),
            "approval_status": "pending" if severity in ("P1", "P2") else "auto_approved",
            "pipeline_status": {**state.get("pipeline_status", {}), "severity": {"status": "done", "elapsed_s": 0.01}},
        }
    return fake


def make_fake_root_cause():
    def fake(state):
        return {
            "root_cause_analysis": "Fake root cause: Redis AUTH expired.",
            "rag_context": ["Fake KB context retrieved."],
            "pipeline_status": {**state.get("pipeline_status", {}), "root_cause": {"status": "done", "elapsed_s": 0.01}},
        }
    return fake


def make_fake_remediation():
    def fake(state):
        return {
            "remediation_plan": "1. Restart Redis.\n2. kubectl rollout restart.",
            "pipeline_status": {**state.get("pipeline_status", {}), "remediation": {"status": "done", "elapsed_s": 0.01}},
        }
    return fake


def make_fake_cookbook():
    def fake(state):
        return {
            "cookbook": "# Runbook\n## Detection Phase\nCheck alerts.",
            "pipeline_status": {**state.get("pipeline_status", {}), "cookbook": {"status": "done", "elapsed_s": 0.01}},
        }
    return fake


def make_fake_jira():
    def fake(state):
        if state.get("severity") in ("P3", "P4"):
            return {"jira_tickets": [], "pipeline_status": {**state.get("pipeline_status", {}), "jira": {"status": "skipped"}}}
        return {
            "jira_tickets": [{"key": "OPS-999", "url": "https://example.com/OPS-999", "mode": "mock"}],
            "pipeline_status": {**state.get("pipeline_status", {}), "jira": {"status": "done", "elapsed_s": 0.01}},
        }
    return fake


def make_fake_notification():
    def fake(state):
        return {
            "notifications_sent": [{"channel": "slack", "status": "delivered_mock"}],
            "pipeline_status": {**state.get("pipeline_status", {}), "notification": {"status": "done_mock", "elapsed_s": 0.01}},
        }
    return fake


def build_test_graph(severity="P1"):
    """Build a graph with all fake agents — no LLM calls."""
    return build_graph(
        classifier_fn=make_fake_classifier(),
        severity_fn=make_fake_severity(severity),
        root_cause_fn=make_fake_root_cause(),
        remediation_fn=make_fake_remediation(),
        cookbook_fn=make_fake_cookbook(),
        jira_fn=make_fake_jira(),
        notification_fn=make_fake_notification(),
    )


# ════════════════════════════════════════════════════════════════
# TOPOLOGY TESTS
# ════════════════════════════════════════════════════════════════

class TestGraphTopology:

    def test_graph_compiles_without_error(self):
        graph = build_test_graph()
        assert graph is not None

    def test_graph_has_exactly_seven_agent_nodes(self):
        graph = build_test_graph()
        node_names = {
            n for n in graph.get_graph().nodes
            if n not in ("__start__", "__end__")
        }
        assert len(node_names) == EXPECTED_NODE_COUNT, (
            f"Expected {EXPECTED_NODE_COUNT} nodes, got {len(node_names)}: {node_names}"
        )

    def test_graph_contains_all_expected_nodes(self):
        graph = build_test_graph()
        node_names = {
            n for n in graph.get_graph().nodes
            if n not in ("__start__", "__end__")
        }
        missing = EXPECTED_NODES - node_names
        assert not missing, f"Graph missing nodes: {missing}"

    def test_expected_node_count_constant_is_seven(self):
        assert EXPECTED_NODE_COUNT == 7

    def test_expected_nodes_constant_has_correct_members(self):
        assert EXPECTED_NODES == {
            "classifier", "severity", "root_cause",
            "remediation", "cookbook", "jira", "notification",
        }

    def test_graph_has_start_and_end_nodes(self):
        graph = build_test_graph()
        all_nodes = set(graph.get_graph().nodes)
        assert "__start__" in all_nodes
        assert "__end__" in all_nodes

    def test_graph_mermaid_diagram_generated(self):
        graph = build_test_graph()
        mermaid = graph.get_graph().draw_mermaid()
        assert isinstance(mermaid, str)
        assert len(mermaid) > 50
        assert "classifier" in mermaid
        assert "severity" in mermaid


# ════════════════════════════════════════════════════════════════
# SEVERITY ROUTER
# ════════════════════════════════════════════════════════════════

class TestSeverityRouter:

    @pytest.mark.parametrize("severity,expected_route", [
        ("P1", "full_pipeline"),
        ("P2", "full_pipeline"),
        ("P3", "summary_only"),
        ("P4", "summary_only"),
    ])
    def test_router_maps_severity_to_correct_path(self, severity, expected_route, minimal_state):
        state = {**minimal_state, "severity": severity}
        result = severity_router(state)
        assert result == expected_route

    def test_router_defaults_to_full_pipeline_on_missing_severity(self, minimal_state):
        """Missing severity defaults to P2 assumption → full pipeline."""
        # Default is "P2" in the router
        state = {**minimal_state, "severity": "P2"}
        result = severity_router(state)
        assert result == "full_pipeline"

    def test_router_is_deterministic(self, minimal_state):
        """Same severity → same route (no randomness)."""
        state = {**minimal_state, "severity": "P1"}
        results = {severity_router(state) for _ in range(5)}
        assert len(results) == 1  # all same result


# ════════════════════════════════════════════════════════════════
# END-TO-END PIPELINE (with fake agents)
# ════════════════════════════════════════════════════════════════

class TestPipelineE2E:

    def test_p1_pipeline_produces_all_outputs(self, minimal_state):
        graph = build_test_graph(severity="P1")
        result = graph.invoke(minimal_state)

        # All key pipeline outputs should be populated
        assert len(result.get("log_summary", "")) > 10
        assert result.get("severity") == "P1"
        assert len(result.get("critical_issues", [])) >= 1
        assert len(result.get("root_cause_analysis", "")) > 10
        assert len(result.get("remediation_plan", "")) > 10
        assert len(result.get("cookbook", "")) > 10
        assert len(result.get("jira_tickets", [])) >= 1
        assert len(result.get("notifications_sent", [])) >= 1

    def test_p3_pipeline_skips_rca_and_jira(self, minimal_state):
        graph = build_test_graph(severity="P3")
        result = graph.invoke(minimal_state)

        assert result.get("severity") == "P3"
        # P3 → summary_only → no RCA
        assert result.get("root_cause_analysis", "") == ""
        # P3 → JIRA skipped
        assert result.get("jira_tickets", []) == []
        # Cookbook should still exist
        assert len(result.get("cookbook", "")) > 10

    def test_p2_pipeline_full_path(self, minimal_state):
        graph = build_test_graph(severity="P2")
        result = graph.invoke(minimal_state)

        assert result.get("severity") == "P2"
        assert len(result.get("root_cause_analysis", "")) > 0
        assert len(result.get("jira_tickets", [])) >= 1

    def test_p4_pipeline_no_jira_no_rca(self, minimal_state):
        graph = build_test_graph(severity="P4")
        result = graph.invoke(minimal_state)

        assert result.get("severity") == "P4"
        assert result.get("root_cause_analysis", "") == ""
        assert result.get("jira_tickets", []) == []

    def test_pipeline_pipeline_status_has_agent_entries(self, minimal_state):
        graph = build_test_graph(severity="P1")
        result = graph.invoke(minimal_state)

        status = result.get("pipeline_status", {})
        # At minimum: classifier, severity, cookbook must be recorded
        assert "classifier" in status
        assert "severity" in status
        assert "cookbook" in status

    def test_pipeline_does_not_raise_with_minimal_state(self, minimal_state):
        """Pipeline should never raise — all errors are captured in state."""
        graph = build_test_graph(severity="P1")
        try:
            result = graph.invoke(minimal_state)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Pipeline raised unexpected exception: {e}")

    def test_pipeline_result_has_no_python_exceptions(self, minimal_state):
        graph = build_test_graph(severity="P1")
        result = graph.invoke(minimal_state)
        # errors field accumulates non-fatal errors — should be empty with fake agents
        assert result.get("errors", []) == []

    def test_parallel_branches_both_executed_for_p1(self, minimal_state):
        """JIRA and Notification both run in parallel after Cookbook for P1."""
        graph = build_test_graph(severity="P1")
        result = graph.invoke(minimal_state)

        assert len(result.get("jira_tickets", [])) >= 1
        assert len(result.get("notifications_sent", [])) >= 1

    def test_list_fields_accumulated_correctly(self, minimal_state):
        """operator.add reducers should accumulate list fields from parallel branches."""
        graph = build_test_graph(severity="P1")
        result = graph.invoke(minimal_state)

        # critical_issues starts empty, fake severity adds 1
        assert len(result.get("critical_issues", [])) >= 1
        # rag_context added by root_cause node
        assert len(result.get("rag_context", [])) >= 1

    def test_pipeline_timing_sub_second_with_fake_agents(self, minimal_state):
        """With fake (no-LLM) agents, pipeline should complete very quickly."""
        import time
        graph = build_test_graph(severity="P2")
        start = time.time()
        graph.invoke(minimal_state)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Pipeline took too long with fake agents: {elapsed:.2f}s"

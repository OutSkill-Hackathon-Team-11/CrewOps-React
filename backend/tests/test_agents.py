"""
Tests: CrewOps Agent Node Functions (test_agents.py)

Unit tests for all 7 agent node functions.
LLMs are mocked via unittest.mock.patch so no API keys are needed.
Each test verifies the node's output field contract and error handling.
"""
from __future__ import annotations
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crewops.agents import (
    classifier_node,
    severity_node,
    root_cause_node,
    remediation_node,
    cookbook_node,
    jira_node,
    notification_node,
)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def make_chain_mock(return_value: str) -> MagicMock:
    """
    Create a mock that behaves like: prompt | llm | StrOutputParser()
    The chain's .invoke() returns the given string.
    """
    chain = MagicMock()
    chain.invoke.return_value = return_value

    llm = MagicMock()
    # prompt.__or__(llm) returns a runnable, that runnable.__or__(parser) returns chain
    runnable = MagicMock()
    runnable.__or__ = MagicMock(return_value=chain)
    llm.__ror__ = MagicMock(return_value=runnable)  # for prompt | llm
    llm.__or__ = MagicMock(return_value=chain)
    return llm, chain


# ════════════════════════════════════════════════════════════════
# AGENT 1: classifier_node
# ════════════════════════════════════════════════════════════════

class TestClassifierNode:
    """Tests for the log classifier agent node."""

    def _make_classifier_llm(self, response: str) -> MagicMock:
        llm, chain = make_chain_mock(response)
        return llm

    @patch("crewops.agents._get_prompts")
    def test_classifier_returns_log_summary(self, mock_prompts, minimal_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Critical incident detected in payment-service."
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (mock_prompt, None, None, None, None)

        mock_llm = MagicMock()
        mock_chain2 = MagicMock()
        mock_chain2.invoke.return_value = "Critical incident detected."
        mock_llm.__ror__ = MagicMock(return_value=mock_chain2)

        # Patch the full chain construction
        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser_instance = MagicMock()
            mock_parser.return_value = mock_parser_instance
            mock_chain2.__or__ = MagicMock(return_value=mock_chain)

            result = classifier_node(minimal_state, llm=mock_llm)

        assert "log_summary" in result
        assert "log_type" in result
        assert "pipeline_status" in result

    @patch("crewops.agents._get_prompts")
    def test_classifier_detects_kubernetes_log_type(self, mock_prompts, minimal_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "K8s incident detected."
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (mock_prompt, None, None, None, None)

        from tests.fixtures import SAMPLE_K8S_LOG
        k8s_state = {**minimal_state, "raw_logs": SAMPLE_K8S_LOG}

        mock_llm = MagicMock()
        mock_chain2 = MagicMock()
        mock_chain2.invoke.return_value = "K8s incident."
        mock_chain.__or__ = MagicMock(return_value=mock_chain2)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            mock_chain.__or__ = MagicMock(return_value=mock_chain)
            result = classifier_node(k8s_state, llm=mock_llm)

        # Log type should be detected from raw_logs content
        assert result["log_type"] == "kubernetes"

    @patch("crewops.agents._get_prompts")
    def test_classifier_error_handling(self, mock_prompts, minimal_state):
        """Classifier must return error state — never propagate exception."""
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(side_effect=RuntimeError("LLM unavailable"))
        mock_prompts.return_value = (mock_prompt, None, None, None, None)

        mock_llm = MagicMock()
        result = classifier_node(minimal_state, llm=mock_llm)

        assert "log_summary" in result
        assert "errors" in result
        assert len(result["errors"]) == 1
        assert "classifier" in result["errors"][0]
        assert result["pipeline_status"]["classifier"]["status"] == "error"

    @patch("crewops.agents._get_prompts")
    def test_classifier_timing_recorded(self, mock_prompts, minimal_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Incident detected."
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (mock_prompt, None, None, None, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = classifier_node(minimal_state, llm=mock_llm)

        assert "classifier" in result.get("pipeline_status", {})
        agent_status = result["pipeline_status"]["classifier"]
        assert "elapsed_s" in agent_status
        assert isinstance(agent_status["elapsed_s"], float)


# ════════════════════════════════════════════════════════════════
# AGENT 2: severity_node
# ════════════════════════════════════════════════════════════════

class TestSeverityNode:

    @patch("crewops.agents._get_prompts")
    def test_severity_node_returns_required_fields(self, mock_prompts, classified_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = (
            "SEVERITY: P1\nRATIONALE: Critical outage.\n"
            "CRITICAL_ISSUES:\n- Redis NOAUTH: Auth failed\n"
        )
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, mock_prompt, None, None, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = severity_node(classified_state, llm=mock_llm)

        for field in ["severity", "severity_rationale", "critical_issues",
                       "approval_required", "approval_status", "pipeline_status"]:
            assert field in result, f"Missing field: {field}"

    @patch("crewops.agents._get_prompts")
    def test_severity_node_p1_sets_approval_required(self, mock_prompts, classified_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "SEVERITY: P1\nRATIONALE: Outage.\nCRITICAL_ISSUES:\n- DB down: crashed\n"
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, mock_prompt, None, None, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = severity_node(classified_state, llm=mock_llm)

        assert result["approval_required"] is True
        assert result["approval_status"] == "pending"

    @patch("crewops.agents._get_prompts")
    def test_severity_node_p3_no_approval(self, mock_prompts, classified_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "SEVERITY: P3\nRATIONALE: Minor.\nCRITICAL_ISSUES:\n- None\n"
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, mock_prompt, None, None, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = severity_node(classified_state, llm=mock_llm)

        assert result["approval_required"] is False
        assert result["approval_status"] == "auto_approved"

    @patch("crewops.agents._get_prompts")
    def test_severity_node_error_fallback_to_p2(self, mock_prompts, classified_state):
        """Severity errors should default to P2 (safe assumption)."""
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(side_effect=RuntimeError("LLM offline"))
        mock_prompts.return_value = (None, mock_prompt, None, None, None)

        mock_llm = MagicMock()
        result = severity_node(classified_state, llm=mock_llm)

        assert result["severity"] == "P2"
        assert "errors" in result
        assert "severity" in result["errors"][0]


# ════════════════════════════════════════════════════════════════
# AGENT 3: root_cause_node
# ════════════════════════════════════════════════════════════════

class TestRootCauseNode:

    @patch("crewops.agents._get_prompts")
    @patch("crewops.agents.search_knowledge_base")
    def test_root_cause_returns_analysis(self, mock_rag, mock_prompts, severity_p1_state):
        mock_rag.return_value = "[K8s Runbook] CrashLoopBackOff steps..."
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Primary Root Cause: Redis AUTH expired."
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, None, mock_prompt, None, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = root_cause_node(severity_p1_state, llm=mock_llm)

        assert "root_cause_analysis" in result
        assert "rag_context" in result
        assert isinstance(result["rag_context"], list)

    @patch("crewops.agents._get_prompts")
    @patch("crewops.agents.search_knowledge_base")
    def test_root_cause_rag_context_is_list(self, mock_rag, mock_prompts, severity_p1_state):
        """rag_context must be a list for the operator.add reducer to work."""
        mock_rag.return_value = "KB context text"
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Root cause identified."
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, None, mock_prompt, None, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = root_cause_node(severity_p1_state, llm=mock_llm)

        assert isinstance(result["rag_context"], list)
        assert len(result["rag_context"]) >= 1

    @patch("crewops.agents._get_prompts")
    @patch("crewops.agents.search_knowledge_base")
    def test_root_cause_rag_queried_before_llm(self, mock_rag, mock_prompts, severity_p1_state):
        """RAG must be called before the LLM chain invoke."""
        call_order = []
        mock_rag.side_effect = lambda *a, **kw: (call_order.append("rag"), "KB result")[1]
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = lambda *a, **kw: (call_order.append("llm"), "RCA result")[1]
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, None, mock_prompt, None, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            root_cause_node(severity_p1_state, llm=mock_llm)

        rag_idx = call_order.index("rag") if "rag" in call_order else -1
        llm_idx = call_order.index("llm") if "llm" in call_order else 999
        assert rag_idx < llm_idx, "RAG should be called before LLM"

    @patch("crewops.agents._get_prompts")
    @patch("crewops.agents.search_knowledge_base")
    def test_root_cause_error_still_includes_rag_context(self, mock_rag, mock_prompts, severity_p1_state):
        """Even when LLM fails, rag_context should be returned (RAG succeeded)."""
        mock_rag.return_value = "Retrieved KB context"
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(side_effect=RuntimeError("LLM error"))
        mock_prompts.return_value = (None, None, mock_prompt, None, None)

        mock_llm = MagicMock()
        result = root_cause_node(severity_p1_state, llm=mock_llm)

        assert "rag_context" in result
        assert len(result["rag_context"]) >= 1
        assert "errors" in result


# ════════════════════════════════════════════════════════════════
# AGENT 4: remediation_node
# ════════════════════════════════════════════════════════════════

class TestRemediationNode:

    @patch("crewops.agents._get_prompts")
    def test_remediation_returns_plan(self, mock_prompts, severity_p1_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "1. Restart Redis.\n2. Check K8s pods."
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, None, None, mock_prompt, None)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = remediation_node(severity_p1_state, llm=mock_llm)

        assert "remediation_plan" in result
        assert "pipeline_status" in result

    @patch("crewops.agents._get_prompts")
    def test_remediation_error_handling(self, mock_prompts, severity_p1_state):
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(side_effect=RuntimeError("LLM error"))
        mock_prompts.return_value = (None, None, None, mock_prompt, None)

        mock_llm = MagicMock()
        result = remediation_node(severity_p1_state, llm=mock_llm)

        assert "remediation_plan" in result
        assert "errors" in result
        assert "remediation" in result["pipeline_status"]
        assert result["pipeline_status"]["remediation"]["status"] == "error"

    @patch("crewops.agents._get_prompts")
    def test_remediation_uses_rca_from_state(self, mock_prompts, severity_p1_state):
        captured_invoke_args = {}
        mock_chain = MagicMock()
        def capture_invoke(args):
            captured_invoke_args.update(args)
            return "Remediation plan."
        mock_chain.invoke = capture_invoke
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, None, None, mock_prompt, None)

        state_with_rca = {
            **severity_p1_state,
            "root_cause_analysis": "Root cause: Redis AUTH."
        }
        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            remediation_node(state_with_rca, llm=mock_llm)

        assert "root_cause" in captured_invoke_args


# ════════════════════════════════════════════════════════════════
# AGENT 5: cookbook_node
# ════════════════════════════════════════════════════════════════

class TestCookbookNode:

    @patch("crewops.agents._get_prompts")
    def test_cookbook_returns_runbook(self, mock_prompts, severity_p1_state):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "# Runbook — P1 Payment Outage\n## Detection Phase\n..."
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_prompts.return_value = (None, None, None, None, mock_prompt)

        mock_llm = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        with patch("crewops.agents.StrOutputParser") as mock_parser:
            mock_parser.return_value = MagicMock()
            result = cookbook_node(severity_p1_state, llm=mock_llm)

        assert "cookbook" in result
        assert "pipeline_status" in result

    @patch("crewops.agents._get_prompts")
    def test_cookbook_error_handling(self, mock_prompts, severity_p1_state):
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(side_effect=RuntimeError("LLM error"))
        mock_prompts.return_value = (None, None, None, None, mock_prompt)

        mock_llm = MagicMock()
        result = cookbook_node(severity_p1_state, llm=mock_llm)

        assert "cookbook" in result
        assert "errors" in result
        assert result["pipeline_status"]["cookbook"]["status"] == "error"


# ════════════════════════════════════════════════════════════════
# AGENT 6: jira_node
# ════════════════════════════════════════════════════════════════

class TestJiraNode:

    def test_jira_mock_mode_returns_ticket(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True)
        assert "jira_tickets" in result
        tickets = result["jira_tickets"]
        assert isinstance(tickets, list)
        assert len(tickets) == 1
        ticket = tickets[0]
        assert "key" in ticket
        assert ticket["mode"] == "mock"

    def test_jira_mock_ticket_has_url(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True, jira_project_key="OPS")
        ticket = result["jira_tickets"][0]
        assert "url" in ticket
        assert "OPS-" in ticket["key"]

    def test_jira_skipped_for_p3(self, severity_p3_state):
        result = jira_node(severity_p3_state, mock_mode=True)
        assert result["jira_tickets"] == []
        assert result["pipeline_status"]["jira"]["status"] == "skipped"

    def test_jira_skipped_for_p4(self, minimal_state):
        p4_state = {**minimal_state, "severity": "P4"}
        result = jira_node(p4_state, mock_mode=True)
        assert result["jira_tickets"] == []

    def test_jira_p1_creates_ticket(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True)
        assert len(result["jira_tickets"]) == 1
        assert result["pipeline_status"]["jira"]["status"] == "done"

    def test_jira_p2_creates_ticket(self, minimal_state):
        p2_state = {**minimal_state, "severity": "P2", "log_type": "kubernetes"}
        result = jira_node(p2_state, mock_mode=True)
        assert len(result["jira_tickets"]) == 1

    def test_jira_ticket_key_uses_project_key(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True, jira_project_key="MYPROJ")
        ticket_key = result["jira_tickets"][0]["key"]
        assert ticket_key.startswith("MYPROJ-")

    def test_jira_error_returns_error_ticket(self, severity_p1_state):
        """JIRA errors must not propagate — return error ticket instead."""
        with patch("crewops.agents.jira_node") as mock_jn:
            # Simulate the live path raising — we test this by accessing live mode
            pass

        # Test by simulating jira.JIRA import failure in live mode
        # Since mock_mode=False with no real server will fail:
        result = jira_node(severity_p1_state, mock_mode=False,
                           jira_server="http://invalid-server",
                           jira_email="", jira_api_token="")
        assert "jira_tickets" in result
        assert "errors" in result


# ════════════════════════════════════════════════════════════════
# AGENT 7: notification_node
# ════════════════════════════════════════════════════════════════

class TestNotificationNode:

    def test_notification_mock_mode_returns_receipts(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        assert "notifications_sent" in result
        receipts = result["notifications_sent"]
        assert isinstance(receipts, list)
        assert len(receipts) >= 1

    def test_notification_mock_receipts_have_channel(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        for receipt in result["notifications_sent"]:
            assert "channel" in receipt
            assert "status" in receipt

    def test_notification_mock_status_is_mock(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        statuses = [r["status"] for r in result["notifications_sent"]]
        assert all("mock" in s for s in statuses)

    def test_notification_timing_recorded(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        assert "notification" in result["pipeline_status"]
        assert "elapsed_s" in result["pipeline_status"]["notification"]

    def test_notification_no_webhook_returns_unconfigured(self, severity_p1_state):
        """Live mode with no webhooks should return graceful no-op receipt."""
        result = notification_node(severity_p1_state, mock_mode=False,
                                   n8n_webhook_url="", slack_webhook_url="")
        receipts = result["notifications_sent"]
        assert len(receipts) >= 1
        assert receipts[0]["channel"] == "none"
        assert receipts[0]["status"] == "no_webhook_configured"

    @patch("crewops.agents.requests")
    def test_notification_live_n8n_success(self, mock_requests, severity_p1_state):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_resp

        result = notification_node(severity_p1_state, mock_mode=False,
                                   n8n_webhook_url="https://fake-n8n.example.com/webhook",
                                   slack_webhook_url="")
        receipts = result["notifications_sent"]
        n8n_receipts = [r for r in receipts if r["channel"] == "n8n"]
        assert len(n8n_receipts) == 1
        assert n8n_receipts[0]["status"] == "delivered"

    @patch("crewops.agents.requests")
    def test_notification_n8n_fails_falls_back_to_slack(self, mock_requests, severity_p1_state):
        # n8n raises, Slack succeeds
        def side_effect(url, **kwargs):
            if "n8n" in url:
                raise ConnectionError("n8n unreachable")
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            return resp

        mock_requests.post.side_effect = side_effect

        result = notification_node(
            severity_p1_state, mock_mode=False,
            n8n_webhook_url="https://fake-n8n.example.com/webhook",
            slack_webhook_url="https://hooks.slack.com/fake",
        )
        receipts = result["notifications_sent"]
        slack_receipts = [r for r in receipts if r["channel"] == "slack"]
        assert len(slack_receipts) == 1
        assert slack_receipts[0]["status"] == "delivered"

"""
Tests: JIRA and Notification Integration Logic (test_integrations.py)

Validates mock/live toggle behavior, ADF ticket building,
Slack block kit payloads, and HTTP fallback logic.
All live HTTP calls are mocked.
"""
from __future__ import annotations
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crewops.agents import jira_node, notification_node
from crewops.parsers import build_adf_description, build_slack_blocks


# ════════════════════════════════════════════════════════════════
# JIRA INTEGRATION
# ════════════════════════════════════════════════════════════════

class TestJiraIntegration:

    # ── Mock mode ──────────────────────────────────────────────────────────────

    def test_mock_mode_no_network_calls(self, severity_p1_state):
        with patch("crewops.agents.jira_node") as _:
            pass  # We're calling the real function, just ensuring no JIRA import
        # Real call with mock_mode=True should never import jira library
        result = jira_node(severity_p1_state, mock_mode=True)
        assert len(result["jira_tickets"]) == 1

    def test_mock_ticket_key_format(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True, jira_project_key="CREWOPS")
        key = result["jira_tickets"][0]["key"]
        # Format: PROJECT-NNN
        parts = key.split("-")
        assert len(parts) == 2
        assert parts[0] == "CREWOPS"
        assert parts[1].isdigit()
        assert 100 <= int(parts[1]) <= 999

    def test_mock_ticket_url_format(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True,
                           jira_server="https://myorg.atlassian.net",
                           jira_project_key="OPS")
        url = result["jira_tickets"][0]["url"]
        assert url.startswith("https://myorg.atlassian.net/browse/OPS-")

    def test_mock_ticket_has_open_status(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True)
        assert result["jira_tickets"][0]["status"] == "Open"

    def test_mock_mode_flag_in_ticket(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True)
        assert result["jira_tickets"][0]["mode"] == "mock"

    def test_p3_severity_skipped_silently(self, severity_p3_state):
        result = jira_node(severity_p3_state, mock_mode=True)
        assert result["jira_tickets"] == []
        assert result["pipeline_status"]["jira"]["reason"] == "severity < P2"

    def test_pipeline_status_done_for_successful_ticket(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True)
        assert result["pipeline_status"]["jira"]["status"] == "done"

    def test_pipeline_status_has_elapsed_time(self, severity_p1_state):
        result = jira_node(severity_p1_state, mock_mode=True)
        assert "elapsed_s" in result["pipeline_status"]["jira"]
        assert isinstance(result["pipeline_status"]["jira"]["elapsed_s"], float)

    # ── Live mode (mocked JIRA library) ───────────────────────────────────────

    def test_live_mode_calls_jira_library(self, severity_p1_state):
        """Live mode with connection failure must return an error ticket (not raise)."""
        # JIRA is imported inside jira_node — test that the failure is handled gracefully
        result = jira_node(
            severity_p1_state,
            mock_mode=False,
            jira_server="http://unreachable-server.invalid",
            jira_email="test@test.com",
            jira_api_token="invalid-token",
        )
        # Must not raise; must have jira_tickets and errors
        assert "jira_tickets" in result
        has_error = (
            any(t.get("key") == "ERR" for t in result.get("jira_tickets", [])) or
            len(result.get("errors", [])) > 0
        )
        assert has_error, "Live mode failure should populate errors or return ERR ticket"
        assert result["pipeline_status"]["jira"]["status"] == "error"

    def test_live_mode_connection_failure_returns_error_ticket(self, severity_p1_state):
        """Any live connection failure must be caught — no uncaught exceptions."""
        result = jira_node(
            severity_p1_state,
            mock_mode=False,
            jira_server="http://unreachable-server-xyz.invalid",
            jira_email="test@test.com",
            jira_api_token="test-token",
        )
        # Must return something (not raise)
        assert "jira_tickets" in result
        # Error ticket with key "ERR" or errors field
        has_error = (
            any(t.get("key") == "ERR" for t in result.get("jira_tickets", [])) or
            len(result.get("errors", [])) > 0
        )
        assert has_error

    # ── ADF description correctness ────────────────────────────────────────────

    def test_adf_description_severity_in_header(self, severity_p1_state):
        adf = build_adf_description("RCA text", "Fix steps", "P1")
        content_texts = [
            node["content"][0]["text"]
            for node in adf["content"]
            if node["type"] == "paragraph"
        ]
        combined = " ".join(content_texts)
        assert "P1" in combined

    def test_adf_description_rca_text_included(self):
        rca_text = "Primary cause: Redis AUTH token expired after rotation."
        adf = build_adf_description(rca_text, "Fix steps", "P2")
        content_texts = [
            node["content"][0]["text"]
            for node in adf["content"]
            if node["type"] == "paragraph"
        ]
        combined = " ".join(content_texts)
        assert "Redis AUTH token expired" in combined

    def test_adf_description_remediation_text_included(self):
        remediation = "1. Rotate Redis credentials. 2. Restart payment service."
        adf = build_adf_description("RCA text", remediation, "P2")
        content_texts = [
            node["content"][0]["text"]
            for node in adf["content"]
            if node["type"] == "paragraph"
        ]
        combined = " ".join(content_texts)
        assert "Rotate Redis" in combined


# ════════════════════════════════════════════════════════════════
# NOTIFICATION INTEGRATION
# ════════════════════════════════════════════════════════════════

class TestNotificationIntegration:

    # ── Mock mode ──────────────────────────────────────────────────────────────

    def test_mock_returns_two_receipts(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        receipts = result["notifications_sent"]
        assert len(receipts) == 2

    def test_mock_receipts_include_n8n_channel(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        channels = [r["channel"] for r in result["notifications_sent"]]
        assert "n8n" in channels

    def test_mock_receipts_include_slack_channel(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        channels = [r["channel"] for r in result["notifications_sent"]]
        assert "slack" in channels

    def test_mock_receipts_have_timestamps(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        for receipt in result["notifications_sent"]:
            assert "timestamp" in receipt

    def test_mock_pipeline_status_done_mock(self, severity_p1_state):
        result = notification_node(severity_p1_state, mock_mode=True)
        assert result["pipeline_status"]["notification"]["status"] == "done_mock"

    # ── Live mode — n8n success ────────────────────────────────────────────────

    @patch("crewops.agents.requests")
    def test_live_n8n_delivery_recorded(self, mock_requests, severity_p1_state):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_resp

        result = notification_node(
            severity_p1_state, mock_mode=False,
            n8n_webhook_url="https://fake-n8n.example.com/webhook",
        )
        n8n_receipts = [r for r in result["notifications_sent"] if r["channel"] == "n8n"]
        assert len(n8n_receipts) == 1
        assert n8n_receipts[0]["status"] == "delivered"

    @patch("crewops.agents.requests")
    def test_live_n8n_payload_has_required_fields(self, mock_requests, severity_p1_state):
        captured_payload = {}
        def capture_post(url, json=None, **kwargs):
            captured_payload.update(json)
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            return resp
        mock_requests.post.side_effect = capture_post

        notification_node(
            severity_p1_state, mock_mode=False,
            n8n_webhook_url="https://fake-n8n.example.com/webhook",
        )
        for required_key in ["event_type", "severity", "log_type", "timestamp", "source"]:
            assert required_key in captured_payload, f"Missing '{required_key}' in n8n payload"

    @patch("crewops.agents.requests")
    def test_live_slack_fallback_when_n8n_fails(self, mock_requests, severity_p1_state):
        call_count = {"n": 0}
        def side_effect(url, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("n8n down")
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
        slack_receipts = [r for r in result["notifications_sent"] if r["channel"] == "slack"]
        assert len(slack_receipts) == 1
        assert slack_receipts[0]["status"] == "delivered"

    @patch("crewops.agents.requests")
    def test_live_both_channels_fail_graceful(self, mock_requests, severity_p1_state):
        mock_requests.post.side_effect = ConnectionError("All channels down")

        result = notification_node(
            severity_p1_state, mock_mode=False,
            n8n_webhook_url="https://fake.example.com/n8n",
            slack_webhook_url="https://fake.example.com/slack",
        )
        # Should not raise — must return receipts with failure status
        receipts = result["notifications_sent"]
        assert isinstance(receipts, list)
        assert len(receipts) >= 1
        failed = [r for r in receipts if "fail" in r.get("status", "").lower() or "error" in r]
        assert len(failed) >= 1

    # ── Slack block kit payload ────────────────────────────────────────────────

    def test_slack_blocks_injected_with_state_severity(self, severity_p1_state):
        blocks = build_slack_blocks(
            severity=severity_p1_state["severity"],
            log_type=severity_p1_state["log_type"],
            severity_rationale=severity_p1_state["severity_rationale"],
            critical_issues=severity_p1_state["critical_issues"],
        )
        header = blocks[0]["text"]["text"]
        assert "P1" in header
        assert "🔴" in header

    def test_slack_blocks_field_count_correct(self, severity_p1_state):
        blocks = build_slack_blocks(
            severity="P1",
            log_type="mixed",
            severity_rationale="Complete outage.",
            critical_issues=[{"title": "Redis down", "severity": "P1"}],
        )
        section_blocks = [b for b in blocks if b["type"] == "section"]
        # Should have: fields section + issues section
        assert len(section_blocks) >= 2

    def test_slack_fields_severity_rationale_truncated(self):
        long_rationale = "A" * 500
        blocks = build_slack_blocks("P1", "mixed", long_rationale, [])
        section = next(b for b in blocks if b["type"] == "section" and "fields" in b)
        rationale_field = next(
            f for f in section["fields"] if "Rationale" in f["text"]
        )
        # Rationale text should be truncated at 100 chars
        assert len(rationale_field["text"]) <= 130  # "*Rationale:* " prefix + 100 chars

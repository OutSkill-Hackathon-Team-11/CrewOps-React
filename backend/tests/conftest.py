"""
Shared pytest fixtures for all CrewOps test suites.

All fixtures are designed to work without real API keys, LLM calls,
or network access. LLMs are always mocked here.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

import pytest

# ── Ensure src/ is on sys.path for all tests ──────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import (
    SAMPLE_K8S_LOG,
    SAMPLE_NGINX_LOG,
    SAMPLE_MIXED_LOG,
    SAMPLE_APP_LOG,
)


# ════════════════════════════════════════════════════════════════
# STATE FIXTURES
# ════════════════════════════════════════════════════════════════

@pytest.fixture
def minimal_state() -> dict:
    """Minimal valid initial state for LangGraph invocation."""
    return {
        "raw_logs": SAMPLE_MIXED_LOG,
        "metadata": {"source": "test", "timestamp": "2025-01-15T08:00:00Z"},
        "log_summary": "",
        "log_type": "",
        "severity": "",
        "severity_rationale": "",
        "critical_issues": [],
        "rag_context": [],
        "root_cause_analysis": "",
        "remediation_plan": "",
        "cookbook": "",
        "approval_required": False,
        "approval_status": "",
        "jira_tickets": [],
        "notifications_sent": [],
        "pipeline_status": {},
        "errors": [],
    }


@pytest.fixture
def classified_state(minimal_state) -> dict:
    """State after classifier_node has run."""
    return {
        **minimal_state,
        "log_summary": "Critical payment service incident detected with Redis and K8s failures.",
        "log_type": "mixed",
    }


@pytest.fixture
def severity_p1_state(classified_state) -> dict:
    """State after severity_node has assigned P1."""
    return {
        **classified_state,
        "severity": "P1",
        "severity_rationale": "Complete payment service outage with cascading Redis and K8s failures.",
        "critical_issues": [
            {"title": "Redis connection refused: NOAUTH authentication failure", "severity": "P1"},
            {"title": "Postgres connection pool exhausted", "severity": "P1"},
        ],
        "approval_required": True,
        "approval_status": "pending",
    }


@pytest.fixture
def severity_p3_state(classified_state) -> dict:
    """State after severity_node has assigned P3."""
    return {
        **classified_state,
        "log_type": "application",
        "severity": "P3",
        "severity_rationale": "Non-critical application warning, no direct user impact.",
        "critical_issues": [],
        "approval_required": False,
        "approval_status": "auto_approved",
    }


@pytest.fixture
def full_pipeline_state(severity_p1_state) -> dict:
    """State representing a fully processed P1 incident."""
    return {
        **severity_p1_state,
        "rag_context": ["[K8s CrashLoop Runbook]\nkubectl describe pod, check OOMKilled events..."],
        "root_cause_analysis": "Primary cause: Redis AUTH failure cascaded to K8s pod restarts.",
        "remediation_plan": "1. Restart Redis with correct auth. 2. kubectl rollout restart deployment/payment.",
        "cookbook": "# Incident Runbook — Payment Service Outage\n## Detection Phase\n...",
        "jira_tickets": [{"key": "OPS-123", "url": "https://example.com/OPS-123", "mode": "mock"}],
        "notifications_sent": [{"channel": "slack", "status": "delivered_mock"}],
        "pipeline_status": {
            "classifier": {"status": "done", "elapsed_s": 1.2},
            "severity": {"status": "done", "elapsed_s": 0.9},
            "root_cause": {"status": "done", "elapsed_s": 3.1},
            "remediation": {"status": "done", "elapsed_s": 2.8},
            "cookbook": {"status": "done", "elapsed_s": 2.1},
            "jira": {"status": "done", "elapsed_s": 0.5},
            "notification": {"status": "done_mock", "elapsed_s": 0.1},
        },
    }


# ════════════════════════════════════════════════════════════════
# MOCK LLM FIXTURES
# ════════════════════════════════════════════════════════════════

def make_mock_llm(response_text: str) -> MagicMock:
    """
    Create a MagicMock LLM that returns a fixed string response.
    Compatible with LangChain LCEL pipe (|) operator.
    """
    mock = MagicMock()
    # Support LCEL chain: prompt | llm | parser
    # The llm.__or__ creates a chain, so we mock the invoke path directly.
    mock_response = MagicMock()
    mock_response.content = response_text
    mock.invoke.return_value = mock_response
    # LCEL pipe (__or__) returns a runnable that .invoke() calls the chain
    # We simulate by making the LLM itself return a runnable-like object.
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = response_text
    mock.__or__ = MagicMock(return_value=mock_chain)
    return mock


@pytest.fixture
def mock_llm_classifier():
    return make_mock_llm(
        "Executive Summary: Critical payment service incident.\n"
        "Log type: mixed\nIssues: Redis NOAUTH, Postgres exhausted, K8s CrashLoop."
    )


@pytest.fixture
def mock_llm_severity_p1():
    return make_mock_llm(
        "SEVERITY: P1\n"
        "RATIONALE: Complete payment outage with cascading failures.\n"
        "CRITICAL_ISSUES:\n"
        "- Redis NOAUTH: Authentication failure blocking all payments\n"
        "- K8s CrashLoop: Payment pod restarting continuously\n"
    )


@pytest.fixture
def mock_llm_severity_p3():
    return make_mock_llm(
        "SEVERITY: P3\n"
        "RATIONALE: Minor application warning with no user impact.\n"
        "CRITICAL_ISSUES:\n"
        "- None\n"
    )


@pytest.fixture
def mock_llm_rca():
    return make_mock_llm(
        "Primary Root Cause: Redis AUTH token expired causing NOAUTH errors.\n"
        "Cascading Failures: Redis failure → payment service crash → K8s CrashLoop.\n"
    )


@pytest.fixture
def mock_llm_remediation():
    return make_mock_llm(
        "1. Renew Redis AUTH token immediately.\n"
        "2. kubectl rollout restart deployment/payment-service\n"
        "3. Verify PostgreSQL connection pool settings.\n"
    )


@pytest.fixture
def mock_llm_cookbook():
    return make_mock_llm(
        "# Incident Runbook — Payment Service P1\n"
        "## Detection Phase\nCheck Redis AUTH: redis-cli AUTH <token>\n"
        "## Containment Phase\nTemporarily route traffic away from payment service.\n"
        "## Resolution Phase\nRenew creds, restart pods, verify health checks.\n"
    )

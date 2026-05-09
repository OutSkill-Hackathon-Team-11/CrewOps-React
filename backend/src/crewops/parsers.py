"""
CrewOps Pure Parsing Functions.

All functions here are I/O-free pure transformations — no LLM calls,
no network, no disk. Testable without any mocking.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional


# ════════════════════════════════════════════════════════════════
# LOG TYPE DETECTION
# ════════════════════════════════════════════════════════════════

_LOG_TYPE_RULES: list[tuple[list[str], str]] = [
    (["crashloopbackoff", "kubelet", "kubernetes", "kubectl", "k8s", "pod/", "evicted", "livenessProbe", "readinessprobe", "replicaset", "statefulset", "daemonset", "kube-apiserver"], "kubernetes"),
    (["nginx", "upstream timed out", "upstream server", "no live upstreams", "502 bad gateway", "location /", "access.log", "error.log", "client_max_body", "proxy_pass", "proxy_read_timeout"], "nginx"),
    (["cloudwatch", "cloudwatch alarm", "alarm state change", "alarmname", "metricname", "awslogs", "aws/lambda", "loggroup", "logstream", "aws/rds", "aws/ec2", "aws/ecs", "cloudtrail"], "cloudwatch"),
    (["traceback", "exception", "assertionerror", "typeerror", "valueerror", "nullpointerexception", "stacktrace", "at com.", "at org.", "django", "flask", "fastapi", "rails", "unhandled"], "application"),
    (["fatal:", "deadlock", "lock wait timeout", "too many connections", "pg_wal", "postgresql", "mysql error", "sqlite", "ora-", "sql error", "replication lag", "database error", "pg_hba"], "database"),
    (["mixed", "multiple services", "cross-service"], "mixed"),
]


# Known valid log types — anything outside this set becomes "other"
KNOWN_LOG_TYPES = frozenset({"kubernetes", "nginx", "cloudwatch", "application", "database", "mixed"})


def detect_log_type(logs: str) -> str:
    """
    Heuristic log-type classification based on keyword presence.

    Evaluates rules in priority order (kubernetes → nginx → cloudwatch →
    application → database → mixed) and returns the FIRST matching category.
    Returns 'other' when input is empty or no known pattern is detected;
    the workflow continues normally for 'other' with low-priority (P4) handling.
    """
    if not logs:  # None or empty string "" only → unknown
        return "unknown"
    logs_lower = logs.lower()
    for keywords, label in _LOG_TYPE_RULES:
        if any(kw in logs_lower for kw in keywords):
            return label
    return "mixed"


# ════════════════════════════════════════════════════════════════
# SEVERITY RESPONSE PARSER
# ════════════════════════════════════════════════════════════════

def parse_severity_response(response_text: str) -> dict:
    """
    Parse the structured text output from the Severity Agent LLM response.

    Expected format:
        SEVERITY: P1
        RATIONALE: <text>
        CRITICAL_ISSUES:
        - Issue title: one line description
        - Another issue: description

    Returns a dict with keys: severity, rationale, critical_issues (list[dict]).
    Falls back gracefully on malformed input.
    """
    severity = "P3"
    rationale = "Unable to determine"
    critical_issues: list[dict] = []

    if not response_text:
        return {"severity": severity, "rationale": rationale, "critical_issues": critical_issues}

    lines = response_text.strip().split("\n")
    parsing_issues = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("SEVERITY:"):
            raw = stripped.split(":", 1)[1].strip()
            # Accept "P1", "P2", "P3", "P4" — strip extra noise
            for candidate in ("P1", "P2", "P3", "P4"):
                if candidate in raw.upper():
                    severity = candidate
                    break
        elif stripped.startswith("RATIONALE:"):
            rationale = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("CRITICAL_ISSUES:"):
            parsing_issues = True
        elif parsing_issues and stripped.startswith("-"):
            issue = stripped.lstrip("- ").strip()
            if issue and issue.lower() != "none":
                critical_issues.append({"title": issue, "severity": severity})

    return {
        "severity": severity,
        "rationale": rationale,
        "critical_issues": critical_issues,
    }


def severity_requires_approval(severity: str) -> tuple[bool, str]:
    """
    Determine whether a severity level requires human approval.

    Returns (approval_required: bool, approval_status: str).
    """
    requires = severity in ("P1", "P2")
    status = "pending" if requires else "auto_approved"
    return requires, status


# ════════════════════════════════════════════════════════════════
# JIRA ADF DESCRIPTION BUILDER
# ════════════════════════════════════════════════════════════════

def _adf_para(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _adf_heading(text: str, level: int = 2) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def build_adf_description(
    root_cause: str,
    remediation: str,
    severity: str,
    max_chars: int = 1500,
) -> dict:
    """
    Build an Atlassian Document Format (ADF) description body for JIRA API v3.

    Args:
        root_cause:   Root cause analysis text.
        remediation:  Remediation plan text.
        severity:     Incident severity (P1–P4).
        max_chars:    Maximum chars per text block to avoid JIRA limits.

    Returns:
        ADF document dict ready to pass as JIRA `description` field.
    """
    ts = datetime.utcnow().isoformat() + "Z"
    return {
        "type": "doc",
        "version": 1,
        "content": [
            _adf_heading("Incident Details"),
            _adf_para(f"Severity: {severity} | Auto-created by CrewOps AI Agent | {ts}"),
            _adf_heading("Root Cause Analysis", 3),
            _adf_para((root_cause or "See attached logs.")[:max_chars]),
            _adf_heading("Remediation Plan", 3),
            _adf_para((remediation or "See agent analysis output.")[:max_chars]),
            _adf_heading("Created By", 3),
            _adf_para("CrewOps Multi-Agent Incident Analysis Suite — Automated ticket creation"),
        ],
    }


# ════════════════════════════════════════════════════════════════
# SLACK BLOCK KIT BUILDER
# ════════════════════════════════════════════════════════════════

_SEVERITY_EMOJI = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}
_SEVERITY_COLOR = {"P1": "#FF0000", "P2": "#FF8800", "P3": "#FFD700", "P4": "#00AA00"}


def build_slack_blocks(
    severity: str,
    log_type: str,
    severity_rationale: str,
    critical_issues: list,
    max_issues: int = 5,
) -> list[dict]:
    """
    Build a Slack Block Kit block array for the incident notification.

    Args:
        severity:           Incident severity (P1-P4).
        log_type:           Detected log type.
        severity_rationale: One-line rationale for triage.
        critical_issues:    List of issue dicts or strings.
        max_issues:         Maximum issues to list in Slack message.

    Returns:
        List of Slack Block Kit block dicts.
    """
    emoji = _SEVERITY_EMOJI.get(severity, "🔴")
    ts_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    issues_text = "\n".join([
        f"• {i.get('title', i) if isinstance(i, dict) else str(i)}"
        for i in (critical_issues or [])[:max_issues]
    ]) or "See full analysis for details."

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} CrewOps Incident Alert — {severity}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Severity:* {severity}"},
                {"type": "mrkdwn", "text": f"*Log Type:* {log_type.upper()}"},
                {"type": "mrkdwn", "text": f"*Time:* {ts_str}"},
                {"type": "mrkdwn", "text": f"*Rationale:* {(severity_rationale or 'N/A')[:100]}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Critical Issues:*\n{issues_text}"},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "🤖 Auto-generated by *CrewOps* Multi-Agent Incident Suite"}
            ],
        },
    ]

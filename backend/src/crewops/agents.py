"""
CrewOps Agent Node Functions.

Each function is a LangGraph node:
  - Accepts a CrewOpsState dict
  - Returns a PARTIAL dict (only the fields it updates)
  - LangGraph merges partial updates into shared state via reducers

LLMs are injected via parameters (default to module-level globals set by
notebook/app startup) to enable unit testing without real API calls.
"""
from __future__ import annotations

import time
import requests  # module-level import so patch("crewops.agents.requests") works
from typing import Any, Optional

from langchain_core.output_parsers import StrOutputParser

from crewops.state import CrewOpsState
from crewops.parsers import (
    detect_log_type,
    parse_severity_response,
    severity_requires_approval,
    build_adf_description,
    build_slack_blocks,
)
from crewops.rag import search_knowledge_base

# ── Module-level LLM placeholders (set at notebook/app startup) ──
# Tests override these via the `llm_*` keyword arguments.
_llm_fast: Optional[Any] = None
_llm_reasoning: Optional[Any] = None
_llm_generation: Optional[Any] = None


def configure_llms(fast: Any, reasoning: Any, generation: Any) -> None:
    """Set module-level LLM instances (call this at notebook startup)."""
    global _llm_fast, _llm_reasoning, _llm_generation
    _llm_fast = fast
    _llm_reasoning = reasoning
    _llm_generation = generation


# ════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════════

def _elapsed(start: float) -> float:
    return round(time.time() - start, 2)


def _get_prompts():
    """Import prompts lazily to avoid circular imports."""
    from crewops.prompts import (
        classifier_prompt,
        severity_prompt,
        root_cause_prompt,
        remediation_prompt,
        cookbook_prompt,
    )
    return classifier_prompt, severity_prompt, root_cause_prompt, remediation_prompt, cookbook_prompt


# ════════════════════════════════════════════════════════════════
# AGENT 1: LOG CLASSIFIER
# ════════════════════════════════════════════════════════════════

def classifier_node(
    state: CrewOpsState,
    llm: Optional[Any] = None,
) -> dict:
    """
    Analyzes raw logs, produces a structured incident report (log_summary)
    and detects the log type (kubernetes/nginx/cloudwatch/application/mixed).
    """
    print("🔍 [1/7] Classifier Agent — parsing and analyzing logs...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_fast

    try:
        cp, *_ = _get_prompts()
        chain = cp | llm | StrOutputParser()
        result = chain.invoke({"log_content": state["raw_logs"]})
        log_type = detect_log_type(state["raw_logs"])

        elapsed = _elapsed(start)
        status["classifier"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   ✅ Done in {elapsed}s — detected log type: {log_type}")
        return {"log_summary": result, "log_type": log_type, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["classifier"] = {"status": "error", "elapsed_s": elapsed, "error": str(e)}
        print(f"   ❌ Classifier error: {e}")
        return {
            "log_summary": f"Log analysis completed with partial results. The system will proceed with best-effort analysis.\n\nNote: {e}",
            "log_type": "other",
            "errors": [f"classifier: {e}"],
            "pipeline_status": status,
        }


# ════════════════════════════════════════════════════════════════
# AGENT 2: SEVERITY CLASSIFIER
# ════════════════════════════════════════════════════════════════

def severity_node(
    state: CrewOpsState,
    llm: Optional[Any] = None,
) -> dict:
    """
    Assigns P1–P4 severity, extracts critical issues, and determines
    whether human approval is required.
    """
    print("🎯 [2/7] Severity Agent — assigning P1-P4 severity...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_fast

    try:
        _, sp, *_ = _get_prompts()
        chain = sp | llm | StrOutputParser()
        result_text = chain.invoke({"log_summary": state["log_summary"]})

        parsed = parse_severity_response(result_text)
        approval_required, approval_status = severity_requires_approval(parsed["severity"])

        elapsed = _elapsed(start)
        status["severity"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   ✅ Done in {elapsed}s — Severity: {parsed['severity']} | Issues: {len(parsed['critical_issues'])}")
        return {
            "severity": parsed["severity"],
            "severity_rationale": parsed["rationale"],
            "critical_issues": parsed["critical_issues"],
            "approval_required": approval_required,
            "approval_status": approval_status,
            "pipeline_status": status,
        }

    except Exception as e:
        elapsed = _elapsed(start)
        status["severity"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   ❌ Severity error: {e}")
        return {
            "severity": "P2",
            "severity_rationale": f"Default P2 assigned due to error: {e}",
            "critical_issues": [],
            "approval_required": True,
            "approval_status": "auto_approved",
            "errors": [f"severity: {e}"],
            "pipeline_status": status,
        }


# ════════════════════════════════════════════════════════════════
# AGENT 3: ROOT CAUSE ANALYSIS (with RAG)
# ════════════════════════════════════════════════════════════════

def root_cause_node(
    state: CrewOpsState,
    llm: Optional[Any] = None,
    query_engine: Optional[Any] = None,
) -> dict:
    """
    Root Cause Analysis agent enhanced with RAG retrieval.
    Queries knowledge base BEFORE invoking the LLM.
    """
    print("🔬 [3/7] Root Cause Agent — querying knowledge base then analyzing...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_reasoning

    # Step 1: Build RAG query from available state
    log_type = state.get("log_type", "incident")
    issues = state.get("critical_issues") or []
    issue_titles = " ".join([
        i.get("title", i) if isinstance(i, dict) else str(i)
        for i in issues[:3]
    ])
    rag_query = f"{log_type} {issue_titles} {state['log_summary'][:200]}"

    # Step 2: Retrieve context (keyword fallback if no query_engine)
    print(f"   🔍 RAG query: {rag_query[:80]}...")
    rag_result = search_knowledge_base(rag_query, query_engine=query_engine)
    print(f"   📚 Retrieved {len(rag_result)} chars from knowledge base")

    try:
        _, _, rca_p, *_ = _get_prompts()
        chain = rca_p | llm | StrOutputParser()

        issues_text = "\n".join([
            f"- {i.get('title', i) if isinstance(i, dict) else i}"
            for i in issues
        ]) or "No specific critical issues extracted."

        result = chain.invoke({
            "log_summary": state["log_summary"],
            "rag_context": rag_result,
            "critical_issues": issues_text,
        })

        elapsed = _elapsed(start)
        status["root_cause"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   ✅ Done in {elapsed}s")
        return {
            "root_cause_analysis": result,
            "rag_context": [rag_result],
            "pipeline_status": status,
        }

    except Exception as e:
        elapsed = _elapsed(start)
        status["root_cause"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   ❌ RCA error: {e}")
        return {
            "root_cause_analysis": f"RCA unavailable: {e}",
            "rag_context": [rag_result],
            "errors": [f"root_cause: {e}"],
            "pipeline_status": status,
        }


# ════════════════════════════════════════════════════════════════
# AGENT 4: REMEDIATION PLANNER
# ════════════════════════════════════════════════════════════════

def remediation_node(
    state: CrewOpsState,
    llm: Optional[Any] = None,
) -> dict:
    """Generates a detailed, step-by-step remediation plan."""
    print("🔧 [4/7] Remediation Agent — generating fix plan...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_reasoning

    try:
        _, _, _, rem_p, _ = _get_prompts()
        chain = rem_p | llm | StrOutputParser()
        result = chain.invoke({
            "issues_text": state["log_summary"],
            "root_cause": state.get("root_cause_analysis") or "RCA not available",
        })

        elapsed = _elapsed(start)
        status["remediation"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   ✅ Done in {elapsed}s")
        return {"remediation_plan": result, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["remediation"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   ❌ Remediation error: {e}")
        return {
            "remediation_plan": f"Remediation plan unavailable: {e}",
            "errors": [f"remediation: {e}"],
            "pipeline_status": status,
        }


# ════════════════════════════════════════════════════════════════
# AGENT 5: COOKBOOK SYNTHESIZER
# ════════════════════════════════════════════════════════════════

def cookbook_node(
    state: CrewOpsState,
    llm: Optional[Any] = None,
) -> dict:
    """Synthesizes an operational runbook from the incident analysis."""
    print("📖 [5/7] Cookbook Agent — synthesizing operational runbook...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_generation

    try:
        _, _, _, _, cb_p = _get_prompts()
        chain = cb_p | llm | StrOutputParser()
        result = chain.invoke({
            "issues_text": state["log_summary"],
            "remediation_text": state.get("remediation_plan") or "See log analysis above.",
        })

        elapsed = _elapsed(start)
        status["cookbook"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   ✅ Done in {elapsed}s")
        return {"cookbook": result, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["cookbook"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   ❌ Cookbook error: {e}")
        return {
            "cookbook": f"Cookbook generation failed: {e}",
            "errors": [f"cookbook: {e}"],
            "pipeline_status": status,
        }


# ════════════════════════════════════════════════════════════════
# AGENT 6: JIRA TICKET CREATOR
# ════════════════════════════════════════════════════════════════

def jira_node(
    state: CrewOpsState,
    mock_mode: bool = True,
    jira_server: str = "https://example.atlassian.net",
    jira_email: str = "",
    jira_api_token: str = "",
    jira_project_key: str = "OPS",
    jira_epic_key: str = "",
    jira_sprint_name: str = "",
) -> dict:
    """
    Creates a JIRA incident ticket for P1/P2 incidents (and always for
    'other' log type with P4/Low priority). Skips silently for P3/P4
    on known log types only.

    Args:
        mock_mode:         When True, returns a fake ticket (no network calls).
        jira_server:       JIRA Cloud instance URL.
        jira_email:        JIRA user email.
        jira_api_token:    JIRA API token.
        jira_project_key:  JIRA project key for created tickets.
        jira_epic_key:     Epic issue key to link ticket to (e.g. "SCRUM-8").
        jira_sprint_name:  Sprint name to assign ticket to (e.g. "SCRUM Sprint 0").
    """
    import random
    print("🎫 [6/7] JIRA Agent — creating incident tickets...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    severity = state.get("severity", "P2")
    log_type = state.get("log_type", "other")

    # For "other" category always create a P4/Low ticket regardless of severity.
    # For known types, skip P3/P4 as they don't warrant a ticket.
    is_other = log_type == "other"
    if severity in ("P3", "P4") and not is_other:
        print(f"   ⏭️  Skipped — {severity} does not require JIRA ticket")
        status["jira"] = {"status": "skipped", "reason": "severity < P2"}
        return {"jira_tickets": [], "pipeline_status": status}
    # Force P4 effective severity for other-type tickets unless truly critical
    effective_severity = "P4" if is_other and severity not in ("P1", "P2") else severity

    try:
        if mock_mode:
            ticket_num = random.randint(100, 999)
            eff_sev = effective_severity
            tickets = [{
                "key": f"{jira_project_key}-{ticket_num}",
                "url": f"{jira_server}/browse/{jira_project_key}-{ticket_num}",
                "summary": f"[{eff_sev}] AI Detected Incident \u2014 {log_type.upper()}",
                "status": "Open",
                "mode": "mock",
                "epic": jira_epic_key or "(none)",
                "sprint": jira_sprint_name or "(none)",
            }]
            print(f"   🟡 MOCK: Ticket {tickets[0]['key']} created")
            if jira_epic_key:
                print(f"      Epic  → {jira_epic_key}")
            if jira_sprint_name:
                print(f"      Sprint→ {jira_sprint_name}")
        else:
            import requests as _req
            priority_map = {"P1": "Highest", "P2": "High", "P3": "Medium", "P4": "Low"}
            eff_sev = effective_severity
            rca   = state.get("root_cause_analysis", "") or ""
            remed = state.get("remediation_plan", "") or ""
            # ADF description for Jira API v3
            adf_body = {
                "type": "doc", "version": 1,
                "content": [
                    {"type": "heading", "attrs": {"level": 2},
                     "content": [{"type": "text", "text": f"[CrewOps] {severity} Incident Auto-Analysis"}]},
                    {"type": "heading", "attrs": {"level": 3},
                     "content": [{"type": "text", "text": "Root Cause Analysis"}]},
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": rca[:2000] if rca else "See log summary."}]},
                    {"type": "heading", "attrs": {"level": 3},
                     "content": [{"type": "text", "text": "Remediation Plan"}]},
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": remed[:2000] if remed else "See recommendations."}]},
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": "Generated by CrewOps Multi-Agent Pipeline.", "marks": [{"type": "em"}]}]},
                ]
            }

            # ── Resolve sprint ID from name (Jira Cloud requires int sprint ID) ──
            sprint_id = None
            if jira_sprint_name and jira_project_key:
                try:
                    boards_resp = _req.get(
                        f"{jira_server}/rest/agile/1.0/board",
                        auth=(jira_email, jira_api_token),
                        params={"projectKeyOrId": jira_project_key, "type": "scrum"},
                        timeout=10,
                    )
                    boards_resp.raise_for_status()
                    boards = boards_resp.json().get("values", [])
                    for board in boards:
                        sprints_resp = _req.get(
                            f"{jira_server}/rest/agile/1.0/board/{board['id']}/sprint",
                            auth=(jira_email, jira_api_token),
                            params={"state": "active,future"},
                            timeout=10,
                        )
                        if sprints_resp.ok:
                            for sp in sprints_resp.json().get("values", []):
                                if sp.get("name", "").strip() == jira_sprint_name.strip():
                                    sprint_id = sp["id"]
                                    break
                        if sprint_id:
                            break
                    if sprint_id:
                        print(f"   ✅ Sprint resolved: '{jira_sprint_name}' → ID {sprint_id}")
                    else:
                        print(f"   ⚠️  Sprint '{jira_sprint_name}' not found — ticket created without sprint")
                except Exception as sp_err:
                    print(f"   ⚠️  Sprint lookup failed ({sp_err}) — continuing without sprint")

            # ── Build fields payload ──
            fields_payload = {
                "project":     {"key": jira_project_key},
                "summary":     f"[{eff_sev}] AI Incident: {log_type.upper()} \u2014 CrewOps",
                "issuetype":   {"name": "Task"},
                "priority":    {"name": priority_map.get(eff_sev, "Low")},
                "description": adf_body,
            }
            epic_field_key = None
            if jira_epic_key:
                try:
                    epic_fields_resp = _req.get(
                        f"{jira_server}/rest/api/3/field",
                        auth=(jira_email, jira_api_token),
                        timeout=10,
                    )
                    epic_fields_resp.raise_for_status()
                    for field in epic_fields_resp.json():
                        if field.get("name", "").strip().lower() == "epic link":
                            epic_field_key = field["id"]
                            break
                    if epic_field_key:
                        fields_payload[epic_field_key] = jira_epic_key
                        print(f"   📎 Epic  → {jira_epic_key} ({epic_field_key})")
                    else:
                        print(f"   ⚠️  Epic Link field not found in Jira — skipping Epic assignment")
                except Exception as epic_err:
                    print(f"   ⚠️  Epic field lookup failed ({epic_err}) — skipping Epic assignment")

            # Sprint (customfield_10020 requires list of sprint IDs)
            if sprint_id:
                fields_payload["customfield_10020"] = [sprint_id]
                print(f"   🏃 Sprint → {jira_sprint_name} (ID {sprint_id})")

            resp = _req.post(
                f"{jira_server}/rest/api/3/issue",
                auth=(jira_email, jira_api_token),
                json={"fields": fields_payload},
                timeout=15,
            )
            resp.raise_for_status()
            issue_data = resp.json()
            issue_key  = issue_data["key"]
            tickets = [{
                "key": issue_key,
                "url": f"{jira_server}/browse/{issue_key}",
                "summary": f"[{eff_sev}] AI Incident",
                "status": "Open",
                "mode": "live",
                "epic": jira_epic_key or None,
                "sprint": jira_sprint_name or None,
            }]
            print(f"   ✅ LIVE: Ticket {issue_key} created → {jira_server}/browse/{issue_key}")

        elapsed = _elapsed(start)
        status["jira"] = {"status": "done", "elapsed_s": elapsed}
        return {"jira_tickets": tickets, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["jira"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   ❌ JIRA error (non-fatal): {e}")
        return {
            "jira_tickets": [{"key": "ERR", "error": str(e), "mode": "failed"}],
            "errors": [f"jira: {e}"],
            "pipeline_status": status,
        }


# ════════════════════════════════════════════════════════════════
# AGENT 7: NOTIFICATION ROUTER
# ════════════════════════════════════════════════════════════════

def notification_node(
    state: CrewOpsState,
    mock_mode: bool = True,
    n8n_webhook_url: str = "",
    slack_webhook_url: str = "",
    http_timeout: int = 8,
) -> dict:
    """
    Sends incident alerts via n8n (primary) or Slack Block Kit (fallback).

    Args:
        mock_mode:          When True, logs delivery without real HTTP calls.
        n8n_webhook_url:    n8n webhook endpoint.
        slack_webhook_url:  Slack incoming webhook URL.
        http_timeout:       HTTP request timeout in seconds.
    """
    from datetime import datetime

    print("📣 [7/7] Notification Agent — sending alerts...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    receipts = []

    if mock_mode:
        print("   🟡 MOCK: n8n + Slack notifications sent")
        receipts = [
            {"channel": "n8n", "status": "delivered_mock", "timestamp": datetime.utcnow().isoformat()},
            {"channel": "slack", "status": "delivered_mock", "timestamp": datetime.utcnow().isoformat()},
        ]
        status["notification"] = {"status": "done_mock", "elapsed_s": _elapsed(start)}
        return {"notifications_sent": receipts, "pipeline_status": status}

    # Live mode: n8n primary → Slack fallback
    payload = {
        "event_type": "incident_detected",
        "severity": state.get("severity", "P2"),
        "log_type": state.get("log_type", "other"),
        "rationale": state.get("severity_rationale", ""),
        "critical_issues": [
            i.get("title", i) if isinstance(i, dict) else i
            for i in (state.get("critical_issues") or [])[:5]
        ],
        "jira_tickets": [t.get("key") for t in (state.get("jira_tickets") or [])],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "CrewOps Multi-Agent Pipeline",
    }

    n8n_ok = False
    if n8n_webhook_url:
        try:
            resp = requests.post(n8n_webhook_url, json=payload, timeout=http_timeout)
            resp.raise_for_status()
            receipts.append({"channel": "n8n", "status": "delivered", "http_status": resp.status_code})
            n8n_ok = True
            print(f"   ✅ n8n delivered (HTTP {resp.status_code})")
        except Exception as e:
            print(f"   ⚠️  n8n failed ({e}) — falling back to Slack")

    if slack_webhook_url and not n8n_ok:
        try:
            blocks = build_slack_blocks(
                severity=state.get("severity", "P2"),
                log_type=state.get("log_type", "other"),
                severity_rationale=state.get("severity_rationale", ""),
                critical_issues=state.get("critical_issues") or [],
            )
            resp = requests.post(
                slack_webhook_url,
                json={"blocks": blocks, "text": f"CrewOps Alert — {state.get('severity')}"},
                timeout=http_timeout,
            )
            resp.raise_for_status()
            receipts.append({"channel": "slack", "status": "delivered", "http_status": resp.status_code})
            print(f"   ✅ Slack delivered (HTTP {resp.status_code})")
        except Exception as e:
            receipts.append({"channel": "slack", "status": "failed", "error": str(e)})
            print(f"   ❌ Slack failed: {e}")

    if not receipts:
        receipts = [{"channel": "none", "status": "no_webhook_configured"}]

    status["notification"] = {"status": "done", "elapsed_s": _elapsed(start)}
    return {"notifications_sent": receipts, "pipeline_status": status}

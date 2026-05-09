#!/usr/bin/env python3
"""
CrewOps — Local CLI Runner
Usage:
    python run.py                              # runs k8s_crashloop.log (default)
    python run.py data/sample_logs/mixed_incident.log
    python run.py --log "paste raw log text here"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import time
from functools import partial
from pathlib import Path

# ── Load .env before any other imports ──────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# ── Verify key is present ────────────────────────────────────────────────────
if not os.environ.get("OPENROUTER_API_KEY"):
    print("❌  OPENROUTER_API_KEY not set. Copy .env.example → .env and fill in your key.")
    sys.exit(1)

# ── LLM setup ────────────────────────────────────────────────────────────────
from langchain_openrouter import ChatOpenRouter
from langchain_core.tracers.langchain import LangChainTracer
from crewops.agents import configure_llms, notification_node, jira_node
from crewops.graph import build_graph
from crewops.state import CrewOpsState

FAST_MODEL      = "openai/gpt-4o-mini"
REASONING_MODEL = "openai/gpt-4o"
GEN_MODEL       = "openai/gpt-4o-mini"

def _make_llm(model: str, temperature: float = 0.1, max_tokens: int = 2000) -> ChatOpenRouter:
    return ChatOpenRouter(model=model, temperature=temperature, max_tokens=max_tokens)


# ── Pretty-print helpers ──────────────────────────────────────────────────────
SEV_EMOJI = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}
SEP = "─" * 72

def _wrap(text: str, indent: int = 4) -> str:
    prefix = " " * indent
    return textwrap.fill(str(text), width=80, initial_indent=prefix, subsequent_indent=prefix)

def _section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def print_results(state: dict, elapsed: float) -> None:
    sev = state.get("severity", "??")
    emoji = SEV_EMOJI.get(sev, "⚪")

    _section(f"{emoji}  CrewOps Analysis Complete  ({elapsed:.1f}s)")

    # ── Classification ──
    print(f"\n{'LOG TYPE':>12}:  {state.get('log_type', 'unknown').upper()}")
    print(f"{'SEVERITY':>12}:  {sev}  —  {state.get('severity_rationale', '')[:100]}")
    print(f"{'APPROVAL':>12}:  {'REQUIRED ⚠️' if state.get('approval_required') else 'Auto-approved ✅'}  [{state.get('approval_status','')}]")

    # ── Critical Issues ──
    issues = state.get("critical_issues", [])
    if issues:
        _section(f"Critical Issues ({len(issues)})")
        for i, iss in enumerate(issues, 1):
            if isinstance(iss, dict):
                print(f"  {i}. [{iss.get('severity','?')}] {iss.get('title', iss)}")
            else:
                print(f"  {i}. {iss}")

    # ── Summary ──
    if state.get("log_summary"):
        _section("Log Summary")
        print(_wrap(state["log_summary"]))

    # ── Root Cause Analysis ──
    if state.get("root_cause_analysis"):
        _section("Root Cause Analysis")
        print(_wrap(state["root_cause_analysis"]))

    # ── RAG Context used ──
    rag = state.get("rag_context", [])
    if rag:
        _section(f"Knowledge Base ({len(rag)} source(s) retrieved)")
        for r in rag:
            print(f"  • {str(r)[:120]}")

    # ── Remediation ──
    if state.get("remediation_plan"):
        _section("Remediation Plan")
        print(_wrap(state["remediation_plan"]))

    # ── Runbook ──
    if state.get("cookbook"):
        _section("Runbook / Cookbook")
        print(_wrap(state["cookbook"]))

    # ── JIRA ──
    tickets = state.get("jira_tickets", [])
    if tickets:
        _section(f"JIRA Tickets ({len(tickets)})")
        for t in tickets:
            if isinstance(t, dict):
                print(f"  🎫  {t.get('key','?')} — {t.get('url','')}")
                if t.get("mock"):
                    print("       (mock mode — no real ticket created)")
            else:
                print(f"  🎫  {t}")

    # ── Notifications ──
    notifs = state.get("notifications_sent", [])
    if notifs:
        _section(f"Notifications ({len(notifs)})")
        for n in notifs:
            if isinstance(n, dict):
                ch = n.get("channel", "?")
                st = n.get("status", "?")
                print(f"  📣  {ch} → {st}")
            else:
                print(f"  📣  {n}")

    # ── Pipeline timing ──
    ps = state.get("pipeline_status", {})
    if ps:
        _section("Agent Timing")
        for agent, info in sorted(ps.items()):
            if isinstance(info, dict) and "elapsed_s" in info:
                print(f"  {agent:<20} {info['elapsed_s']:.2f}s  [{info.get('status','?')}]")

    # ── Errors ──
    errors = state.get("errors", [])
    if errors:
        _section(f"⚠️  Errors / Warnings ({len(errors)})")
        for e in errors:
            print(f"  • {e}")

    print(f"\n{SEP}\n")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="CrewOps multi-agent incident analyser")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("log_file", nargs="?", default=None, help="Path to log file")
    group.add_argument("--log", "-l", metavar="TEXT", help="Raw log text (inline)")
    parser.add_argument(
        "--fast-model",   default=FAST_MODEL,      help=f"Fast LLM (default: {FAST_MODEL})"
    )
    parser.add_argument(
        "--smart-model",  default=REASONING_MODEL, help=f"Reasoning LLM (default: {REASONING_MODEL})"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Dump raw JSON state at end"
    )
    args = parser.parse_args()

    # ── Load log text ──
    if args.log:
        raw_log = args.log
        source = "(inline)"
    else:
        log_path = Path(args.log_file) if args.log_file else Path("data/sample_logs/k8s_crashloop.log")
        if not log_path.exists():
            print(f"❌  Log file not found: {log_path}")
            sys.exit(1)
        raw_log = log_path.read_text()
        source = str(log_path)

    print(f"\n{SEP}")
    print(f"  🚀  CrewOps — Multi-Agent Incident Analyser")
    print(f"  Log : {source}")
    print(f"  Fast: {args.fast_model}  |  Smart: {args.smart_model}")
    _notif_live = os.environ.get("NOTIFICATION_MOCK_MODE", "True").strip().lower() in ("false", "0", "no")
    _jira_live  = os.environ.get("JIRA_MOCK_MODE",         "True").strip().lower() in ("false", "0", "no")
    print(f"  JIRA: {'LIVE 🟢' if _jira_live else 'mock'}  "
          f"| Notifs: {'LIVE 🟢' if _notif_live else 'mock'}")
    print(SEP)
    print("\n⏳  Booting agents and running pipeline...\n")

    # ── Wire up LLMs ──
    llm_fast      = _make_llm(args.fast_model,  temperature=0.1, max_tokens=2000)
    llm_reasoning = _make_llm(args.smart_model, temperature=0.2, max_tokens=4000)
    llm_gen       = _make_llm(args.fast_model,  temperature=0.3, max_tokens=6000)
    configure_llms(fast=llm_fast, reasoning=llm_reasoning, generation=llm_gen)

    # ── Wire notification + jira nodes from env ──
    notif_mock = os.environ.get("NOTIFICATION_MOCK_MODE", "True").strip().lower() not in ("false", "0", "no")
    jira_mock  = os.environ.get("JIRA_MOCK_MODE",         "True").strip().lower() not in ("false", "0", "no")

    configured_notification = partial(
        notification_node,
        mock_mode=notif_mock,
        n8n_webhook_url=os.environ.get("N8N_WEBHOOK_URL", ""),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL", ""),
    )
    configured_jira = partial(
        jira_node,
        mock_mode=jira_mock,
        jira_server=os.environ.get("JIRA_SERVER", ""),
        jira_email=os.environ.get("JIRA_EMAIL", ""),
        jira_api_token=os.environ.get("JIRA_API_TOKEN", ""),
        jira_project_key=os.environ.get("JIRA_PROJECT_KEY", "CrewOps"),
        jira_epic_key=os.environ.get("JIRA_EPIC_KEY", ""),
        jira_sprint_name=os.environ.get("JIRA_SPRINT_NAME", ""),
    )

    # ── Build and invoke graph ──
    graph = build_graph(notification_fn=configured_notification, jira_fn=configured_jira)

    initial_state: CrewOpsState = {
        "raw_logs":             raw_log,
        "metadata":             {"source": source, "runner": "cli"},
        "log_summary":          "",
        "log_type":             "",
        "severity":             "",
        "severity_rationale":   "",
        "approval_required":    False,
        "approval_status":      "pending",
        "critical_issues":      [],
        "rag_context":          [],
        "root_cause_analysis":  "",
        "remediation_plan":     "",
        "cookbook":             "",
        "jira_tickets":         [],
        "notifications_sent":   [],
        "pipeline_status":      {},
        "errors":               [],
    }

    # Build LangSmith tracer — sends every LLM call as a child span
    project = os.environ.get("LANGCHAIN_PROJECT", "CrewOps-Hackathon")
    tracer = LangChainTracer(project_name=project)
    run_name = f"CrewOps | {Path(source).name if source != '(inline)' else 'inline'}"

    t0 = time.time()
    result = graph.invoke(
        initial_state,
        config={"callbacks": [tracer], "run_name": run_name},
    )
    elapsed = time.time() - t0
    print(f"\n🔭  Traces → https://smith.langchain.com → {project} project")

    print_results(result, elapsed)

    if args.json:
        # Redact raw_log from JSON dump to keep it readable
        dump = {k: v for k, v in result.items() if k != "raw_log"}
        print("── JSON STATE ──")
        print(json.dumps(dump, indent=2, default=str))


if __name__ == "__main__":
    main()

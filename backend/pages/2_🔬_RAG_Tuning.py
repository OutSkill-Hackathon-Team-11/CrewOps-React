"""
CrewOps — RAG & LLM Tuning Studio
Expose every knob in the pipeline: LLM temperatures, RAG retrieval params,
log processing limits, and a live test-runner with side-by-side comparison.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CrewOps · RAG Tuning",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important}
.stApp{background:linear-gradient(135deg,#060b18 0%,#0d1424 40%,#0a1628 70%,#060b18 100%)!important}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1120,#0d1528)!important;border-right:1px solid rgba(99,179,237,.15)!important}
[data-testid="stHeader"]{background:rgba(6,11,24,.95)!important;border-bottom:1px solid rgba(99,179,237,.12)!important}
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden}
[data-testid="collapsedControl"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}
[data-testid="stSidebar"][aria-expanded="false"]{display:flex!important;min-width:21rem!important;width:21rem!important}
[data-testid="stSidebar"][aria-expanded="true"]{min-width:21rem!important;width:21rem!important}
[data-testid="stMetric"]{background:linear-gradient(135deg,rgba(99,179,237,.08),rgba(139,92,246,.06));border:1px solid rgba(99,179,237,.18);border-radius:12px;padding:16px 20px!important}
[data-testid="stMetric"] label{color:#8ba3c7!important;font-size:.73rem!important;font-weight:600!important;letter-spacing:.06em;text-transform:uppercase}
[data-testid="stMetricValue"]{color:#e8f0fe!important;font-size:1.55rem!important;font-weight:700!important}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#3b82f6,#7c3aed)!important;border:none!important;border-radius:8px!important;color:#fff!important;font-weight:600!important;padding:.55rem 1.6rem!important;box-shadow:0 0 20px rgba(59,130,246,.35)}
.stButton>button[kind="secondary"]{background:rgba(99,179,237,.07)!important;border:1px solid rgba(99,179,237,.25)!important;border-radius:8px!important;color:#93c5fd!important;font-weight:500!important}
.stTabs [data-baseweb="tab-list"]{background:rgba(13,20,40,.6)!important;border-radius:10px!important;border:1px solid rgba(99,179,237,.12)!important;padding:4px;gap:2px}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:8px!important;color:#8ba3c7!important;font-weight:500!important;padding:8px 16px!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(59,130,246,.25),rgba(124,58,237,.2))!important;color:#93c5fd!important;border:1px solid rgba(99,179,237,.3)!important}
[data-testid="stDataFrame"]{background:rgba(13,20,40,.8)!important;border:1px solid rgba(99,179,237,.15)!important;border-radius:10px!important}
[data-testid="stExpander"]{background:rgba(13,20,40,.6)!important;border:1px solid rgba(99,179,237,.15)!important;border-radius:10px!important}
.stSuccess{background:rgba(74,222,128,.08)!important;border-color:rgba(74,222,128,.3)!important;border-radius:8px!important;color:#bbf7d0!important}
.stError{background:rgba(248,113,113,.08)!important;border-color:rgba(248,113,113,.3)!important;border-radius:8px!important;color:#fecaca!important}
.stInfo{background:rgba(99,179,237,.08)!important;border-color:rgba(99,179,237,.25)!important;border-radius:8px!important;color:#bae6fd!important}
h1,h2,h3,h4,h5,h6{color:#e8f0fe!important}
p,span,label,.stMarkdown{color:#c0d0e8!important}
.stCaption{color:#8ba3c7!important}
a{color:#93c5fd!important}
hr{border-color:rgba(99,179,237,.12)!important}
.param-section{background:rgba(13,20,40,.6);border:1px solid rgba(99,179,237,.15);border-radius:12px;padding:20px 24px;margin-bottom:16px}
.param-title{font-size:.8rem;font-weight:700;color:#93c5fd;letter-spacing:.08em;text-transform:uppercase;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid rgba(99,179,237,.12)}
.preset-chip{display:inline-block;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:3px 12px;font-size:.75rem;color:#93c5fd;margin:2px;cursor:pointer}
.result-box{background:rgba(13,20,40,.8);border:1px solid rgba(99,179,237,.18);border-radius:10px;padding:16px;font-size:.85rem;color:#c0d0e8;font-family:'Inter',monospace;white-space:pre-wrap;max-height:320px;overflow-y:auto}
</style>
""", unsafe_allow_html=True)

# ── Built-in presets ──────────────────────────────────────────────────────────
PRESETS: dict[str, dict] = {
    "🏎️  Speed (GPT-4o-mini)": {
        "fast_model":        "openai/gpt-4o-mini",
        "reasoning_model":   "openai/gpt-4o-mini",
        "generation_model":  "openai/gpt-4o-mini",
        "fast_temp":         0.0,
        "reasoning_temp":    0.1,
        "generation_temp":   0.2,
        "fast_max_tokens":   512,
        "reasoning_max_tokens": 1024,
        "generation_max_tokens": 1024,
        "rag_top_k":         3,
        "rag_similarity_threshold": 0.35,
        "rag_chunk_size":    512,
        "max_log_chars":     3000,
        "p1p2_full_pipeline": True,
        "kb_fallback":       True,
    },
    "🔬  Quality (GPT-4o)": {
        "fast_model":        "openai/gpt-4o-mini",
        "reasoning_model":   "openai/gpt-4o",
        "generation_model":  "openai/gpt-4o-mini",
        "fast_temp":         0.1,
        "reasoning_temp":    0.2,
        "generation_temp":   0.3,
        "fast_max_tokens":   800,
        "reasoning_max_tokens": 2048,
        "generation_max_tokens": 2048,
        "rag_top_k":         5,
        "rag_similarity_threshold": 0.25,
        "rag_chunk_size":    1024,
        "max_log_chars":     8000,
        "p1p2_full_pipeline": True,
        "kb_fallback":       True,
    },
    "⚖️  Balanced": {
        "fast_model":        "openai/gpt-4o-mini",
        "reasoning_model":   "openai/gpt-4o",
        "generation_model":  "openai/gpt-4o-mini",
        "fast_temp":         0.05,
        "reasoning_temp":    0.15,
        "generation_temp":   0.25,
        "fast_max_tokens":   600,
        "reasoning_max_tokens": 1500,
        "generation_max_tokens": 1500,
        "rag_top_k":         4,
        "rag_similarity_threshold": 0.28,
        "rag_chunk_size":    768,
        "max_log_chars":     5000,
        "p1p2_full_pipeline": True,
        "kb_fallback":       True,
    },
    "🧪  Creative (high temp)": {
        "fast_model":        "openai/gpt-4o-mini",
        "reasoning_model":   "openai/gpt-4o",
        "generation_model":  "openai/gpt-4o-mini",
        "fast_temp":         0.4,
        "reasoning_temp":    0.5,
        "generation_temp":   0.7,
        "fast_max_tokens":   800,
        "reasoning_max_tokens": 2000,
        "generation_max_tokens": 2000,
        "rag_top_k":         6,
        "rag_similarity_threshold": 0.20,
        "rag_chunk_size":    512,
        "max_log_chars":     6000,
        "p1p2_full_pipeline": True,
        "kb_fallback":       True,
    },
}

# ── Session state defaults ────────────────────────────────────────────────────
DEFAULT = PRESETS["⚖️  Balanced"]
for k, v in DEFAULT.items():
    if f"tune_{k}" not in st.session_state:
        st.session_state[f"tune_{k}"] = v

AVAILABLE_MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "openai/gpt-4-turbo",
    "anthropic/claude-3-haiku",
    "anthropic/claude-3-sonnet",
    "google/gemini-flash-1.5",
    "mistralai/mistral-7b-instruct",
    "meta-llama/llama-3-8b-instruct",
]


def apply_preset(name: str) -> None:
    preset = PRESETS[name]
    for k, v in preset.items():
        st.session_state[f"tune_{k}"] = v


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="font-size:1.8rem;font-weight:700;margin-bottom:4px">'
    '🔬 RAG &amp; LLM Tuning Studio</h1>'
    '<p style="color:#8ba3c7;margin-bottom:24px">Adjust every parameter in the CrewOps pipeline — '
    'then test with a real log to see the effect live.</p>',
    unsafe_allow_html=True,
)

# ── Presets row ───────────────────────────────────────────────────────────────
st.markdown("**Quick Presets**")
pcols = st.columns(len(PRESETS))
for col, pname in zip(pcols, PRESETS):
    with col:
        if st.button(pname, use_container_width=True, type="secondary"):
            apply_preset(pname)
            st.rerun()

st.markdown("---")

# ── Parameter panels (3 columns) ─────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 1])

# ── Column 1: Agent LLM params ────────────────────────────────────────────────
with col1:
    st.markdown("### 🤖 Agent LLM Parameters")
    with st.expander("⚡ Fast Agent (Classifier + Severity)", expanded=True):
        st.session_state["tune_fast_model"] = st.selectbox(
            "Model", AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(st.session_state["tune_fast_model"])
                  if st.session_state["tune_fast_model"] in AVAILABLE_MODELS else 0,
            key="sb_fast_model",
        )
        st.session_state["tune_fast_temp"] = st.slider(
            "Temperature", 0.0, 1.0, float(st.session_state["tune_fast_temp"]), 0.01,
            key="sl_fast_temp",
            help="0 = deterministic, 1 = creative. Keep low for classification.",
        )
        st.session_state["tune_fast_max_tokens"] = st.slider(
            "Max output tokens", 128, 2048, int(st.session_state["tune_fast_max_tokens"]), 64,
            key="sl_fast_tokens",
        )

    with st.expander("🧠 Reasoning Agent (RCA + Remediation)", expanded=True):
        st.session_state["tune_reasoning_model"] = st.selectbox(
            "Model", AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(st.session_state["tune_reasoning_model"])
                  if st.session_state["tune_reasoning_model"] in AVAILABLE_MODELS else 1,
            key="sb_reasoning_model",
        )
        st.session_state["tune_reasoning_temp"] = st.slider(
            "Temperature", 0.0, 1.0, float(st.session_state["tune_reasoning_temp"]), 0.01,
            key="sl_reasoning_temp",
        )
        st.session_state["tune_reasoning_max_tokens"] = st.slider(
            "Max output tokens", 256, 4096, int(st.session_state["tune_reasoning_max_tokens"]), 64,
            key="sl_reasoning_tokens",
        )

    with st.expander("📝 Generation Agent (Cookbook / Runbook)", expanded=True):
        st.session_state["tune_generation_model"] = st.selectbox(
            "Model", AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(st.session_state["tune_generation_model"])
                  if st.session_state["tune_generation_model"] in AVAILABLE_MODELS else 0,
            key="sb_generation_model",
        )
        st.session_state["tune_generation_temp"] = st.slider(
            "Temperature", 0.0, 1.0, float(st.session_state["tune_generation_temp"]), 0.01,
            key="sl_generation_temp",
        )
        st.session_state["tune_generation_max_tokens"] = st.slider(
            "Max output tokens", 256, 4096, int(st.session_state["tune_generation_max_tokens"]), 64,
            key="sl_generation_tokens",
        )

# ── Column 2: RAG params ──────────────────────────────────────────────────────
with col2:
    st.markdown("### 🗄️ RAG / Knowledge Base")
    with st.expander("Retrieval Parameters", expanded=True):
        st.session_state["tune_rag_top_k"] = st.slider(
            "Top-K results", 1, 15, int(st.session_state["tune_rag_top_k"]), 1,
            key="sl_top_k",
            help="Number of KB chunks retrieved per query. Higher = more context, more tokens.",
        )
        st.session_state["tune_rag_similarity_threshold"] = st.slider(
            "Similarity threshold", 0.0, 1.0,
            float(st.session_state["tune_rag_similarity_threshold"]), 0.01,
            key="sl_similarity",
            help="Minimum cosine similarity to include a chunk. Lower = more recall, less precision.",
        )
        st.session_state["tune_rag_chunk_size"] = st.select_slider(
            "Chunk size (tokens)", [128, 256, 512, 768, 1024, 1536, 2048],
            value=st.session_state["tune_rag_chunk_size"],
            key="sl_chunk",
            help="Larger chunks = more context per result but fewer distinct chunks retrieved.",
        )
        st.session_state["tune_kb_fallback"] = st.toggle(
            "Enable keyword fallback", value=bool(st.session_state["tune_kb_fallback"]),
            key="tgl_fallback",
            help="Falls back to keyword matching when LanceDB / LlamaIndex is unavailable.",
        )

    st.markdown("### 📥 Log Processing")
    with st.expander("Input Preprocessing", expanded=True):
        st.session_state["tune_max_log_chars"] = st.slider(
            "Max log characters sent to LLM", 500, 20_000,
            int(st.session_state["tune_max_log_chars"]), 500,
            key="sl_log_chars",
            help="Truncates the raw log at this many characters before sending. "
                 "Prevents token overflows on huge log dumps.",
        )
        truncate_strategy = st.radio(
            "Truncation strategy",
            ["Head (first N chars)", "Tail (last N chars)", "Head + Tail"],
            key="rad_trunc",
            help="Which part of a long log to keep.",
        )
        strip_timestamps = st.toggle(
            "Strip timestamps before sending", value=False, key="tgl_strip_ts",
            help="Removes ISO8601/syslog timestamps to save tokens.",
        )
        deduplicate_lines = st.toggle(
            "Deduplicate repeated lines", value=True, key="tgl_dedup",
            help="Collapses repeated identical log lines into '(repeated N times)'.",
        )

    st.markdown("### 🔀 Pipeline Routing")
    with st.expander("Severity-based Routing", expanded=True):
        st.session_state["tune_p1p2_full_pipeline"] = st.toggle(
            "Full pipeline for P1/P2", value=bool(st.session_state["tune_p1p2_full_pipeline"]),
            key="tgl_routing",
            help="P1/P2 runs RCA → Remediation → Cookbook → JIRA → Slack. "
                 "P3/P4 skips directly to Cookbook → JIRA.",
        )
        p1_threshold = st.slider(
            "P1 critical_issues threshold", 1, 10, 3, 1,
            key="sl_p1_thresh",
            help="If ≥ this many critical issues detected, escalate to P1.",
        )
        notify_on_p3 = st.toggle(
            "Send Slack alert for P3", value=False, key="tgl_p3_notify",
            help="By default only P1/P2 trigger Slack notifications.",
        )

# ── Column 3: Live config JSON + test runner ──────────────────────────────────
with col3:
    st.markdown("### 📋 Current Config")
    current_config = {
        "llm": {
            "fast":       {"model": st.session_state["tune_fast_model"],
                           "temperature": st.session_state["tune_fast_temp"],
                           "max_tokens": st.session_state["tune_fast_max_tokens"]},
            "reasoning":  {"model": st.session_state["tune_reasoning_model"],
                           "temperature": st.session_state["tune_reasoning_temp"],
                           "max_tokens": st.session_state["tune_reasoning_max_tokens"]},
            "generation": {"model": st.session_state["tune_generation_model"],
                           "temperature": st.session_state["tune_generation_temp"],
                           "max_tokens": st.session_state["tune_generation_max_tokens"]},
        },
        "rag": {
            "top_k":               st.session_state["tune_rag_top_k"],
            "similarity_threshold":st.session_state["tune_rag_similarity_threshold"],
            "chunk_size":          st.session_state["tune_rag_chunk_size"],
            "kb_fallback":         st.session_state["tune_kb_fallback"],
        },
        "processing": {
            "max_log_chars":     st.session_state["tune_max_log_chars"],
            "truncation":        truncate_strategy,
            "strip_timestamps":  strip_timestamps,
            "deduplicate_lines": deduplicate_lines,
        },
        "routing": {
            "full_pipeline_for_p1p2": st.session_state["tune_p1p2_full_pipeline"],
            "p1_threshold":           p1_threshold,
            "notify_on_p3":           notify_on_p3,
        },
    }
    config_json = json.dumps(current_config, indent=2)
    st.code(config_json, language="json")

    # Save / Load preset
    ccols = st.columns(2)
    with ccols[0]:
        save_name = st.text_input("Save as preset…", placeholder="My Custom Config", key="preset_name_input")
        if st.button("💾  Save Preset", type="secondary", use_container_width=True):
            if save_name:
                PRESETS[save_name] = {k.replace("tune_", ""): v
                                      for k, v in st.session_state.items()
                                      if k.startswith("tune_")}
                st.success(f"Saved preset: {save_name}")
            else:
                st.warning("Enter a preset name first.")
    with ccols[1]:
        st.download_button(
            label="⬇️  Export JSON",
            data=config_json,
            file_name="crewops_config.json",
            mime="application/json",
            type="secondary",
            use_container_width=True,
        )

# ── Live Test Runner ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🧪 Live Test Runner")
st.markdown(
    "Paste a log snippet below and run it through the pipeline with your current settings. "
    "Results appear side-by-side with default settings for comparison."
)

# Sample log loader
sample_logs_dir = Path(__file__).parent.parent / "data" / "sample_logs"
sample_files: list[str] = []
if sample_logs_dir.exists():
    sample_files = sorted(f.name for f in sample_logs_dir.glob("*.log"))

rc1, rc2 = st.columns([2, 1])
with rc2:
    if sample_files:
        selected_sample = st.selectbox("Load sample log", ["— paste manually —"] + sample_files, key="sel_sample")
        if selected_sample != "— paste manually —":
            sample_text = (sample_logs_dir / selected_sample).read_text(encoding="utf-8", errors="replace")
            # Honour max_log_chars even for sample
            max_c = st.session_state["tune_max_log_chars"]
            if len(sample_text) > max_c:
                sample_text = sample_text[:max_c] + "\n... [truncated]"
        else:
            sample_text = ""
    else:
        sample_text = ""
        st.info("No sample logs found in data/sample_logs/")

with rc1:
    log_input = st.text_area(
        "Log input",
        value=sample_text,
        height=200,
        placeholder="Paste your log here…",
        key="test_log_input",
    )

run_col1, run_col2, _ = st.columns([1, 1, 3])
with run_col1:
    run_tuned  = st.button("▶  Run with Tuned Config", type="primary",  use_container_width=True)
with run_col2:
    run_default = st.button("▶  Run with Default Config", type="secondary", use_container_width=True)

def _simulate_run(log_text: str, config: dict) -> dict:
    """
    Simulate (or actually run) the CrewOps pipeline.
    When the real graph is importable, it will be called here.
    Otherwise returns a structured mock result.
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from crewops.parsers import detect_log_type, extract_error_lines
        from crewops.rag     import search_knowledge_base

        max_c = config["processing"]["max_log_chars"]
        text  = log_text[:max_c]

        log_type     = detect_log_type(text)
        error_lines  = extract_error_lines(text)
        kb_results   = search_knowledge_base(
            text,
            top_k=config["rag"]["top_k"],
        )
        return {
            "log_type":         log_type,
            "error_lines_count": len(error_lines),
            "kb_hits":          len(kb_results) if kb_results else 0,
            "kb_snippets":      kb_results[:2] if kb_results else [],
            "top_errors":       error_lines[:5],
            "config_used":      config["llm"]["reasoning"]["model"],
            "status":           "partial_run",
            "note":             "Full LLM agents require API keys. Showing parser + RAG results.",
        }
    except Exception as exc:
        return {
            "status": "mock",
            "log_type": "kubernetes" if "pod" in log_text.lower() else
                        "nginx"      if "nginx" in log_text.lower() else
                        "other",
            "severity": "P2 HIGH",
            "summary":  f"[Demo] Detected likely incident. Full agent run needs API keys.\n"
                        f"Parser error: {exc}",
            "config_used": config["llm"]["reasoning"]["model"],
        }


if run_tuned or run_default:
    if not log_input.strip():
        st.warning("⚠️ Paste some log content first.")
    else:
        chosen_config = current_config if run_tuned else json.loads(
            json.dumps({k.replace("tune_", ""): v for k, v in DEFAULT.items()})
        )
        label = "Tuned Config" if run_tuned else "Default Config"

        with st.spinner(f"Running pipeline with {label}…"):
            t0     = time.time()
            result = _simulate_run(log_input, current_config if run_tuned else {
                "processing": {"max_log_chars": DEFAULT["max_log_chars"]},
                "rag":        {"top_k": DEFAULT["rag_top_k"]},
                "llm":        {"reasoning": {"model": DEFAULT["reasoning_model"]}},
            })
            elapsed = time.time() - t0

        st.markdown(f"#### Results — {label} ({elapsed:.2f}s)")
        r1, r2, r3 = st.columns(3)
        r1.metric("Log Type",      result.get("log_type", "—"))
        r2.metric("KB Hits",       result.get("kb_hits", "—"))
        r3.metric("Error Lines",   result.get("error_lines_count", "—"))

        with st.expander("📄 Full Result JSON", expanded=False):
            st.json(result)

        if result.get("top_errors"):
            with st.expander("🔴 Top Error Lines", expanded=True):
                for line in result["top_errors"]:
                    st.code(line, language="text")

        if result.get("kb_snippets"):
            with st.expander("📚 Knowledge Base Matches", expanded=True):
                for snippet in result["kb_snippets"]:
                    if isinstance(snippet, dict):
                        st.markdown(f"**{snippet.get('title', 'Match')}**")
                        st.caption(str(snippet.get("content", snippet))[:400] + "…")
                    else:
                        st.caption(str(snippet)[:400] + "…")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "💡 **Tip:** Changes here are session-only. Export the JSON and set values in "
    "your `.env` or `config.py` to persist across restarts."
)

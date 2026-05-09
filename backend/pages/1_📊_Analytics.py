"""
CrewOps — Analytics Dashboard
Fetches run data from LangSmith and visualises usage, error trends, and log classification stats.
"""
from __future__ import annotations

import os
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CrewOps · Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared CSS (mirror app.py theme) ─────────────────────────────────────────
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
[data-testid="stMetricDelta"]{color:#4ade80!important}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#3b82f6,#7c3aed)!important;border:none!important;border-radius:8px!important;color:#fff!important;font-weight:600!important;padding:.55rem 1.6rem!important;box-shadow:0 0 20px rgba(59,130,246,.35)}
.stButton>button[kind="secondary"]{background:rgba(99,179,237,.07)!important;border:1px solid rgba(99,179,237,.25)!important;border-radius:8px!important;color:#93c5fd!important;font-weight:500!important}
.stTabs [data-baseweb="tab-list"]{background:rgba(13,20,40,.6)!important;border-radius:10px!important;border:1px solid rgba(99,179,237,.12)!important;padding:4px;gap:2px}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:8px!important;color:#8ba3c7!important;font-weight:500!important;padding:8px 16px!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(59,130,246,.25),rgba(124,58,237,.2))!important;color:#93c5fd!important;border:1px solid rgba(99,179,237,.3)!important}
[data-testid="stDataFrame"]{background:rgba(13,20,40,.8)!important;border:1px solid rgba(99,179,237,.15)!important;border-radius:10px!important}
[data-testid="stExpander"]{background:rgba(13,20,40,.6)!important;border:1px solid rgba(99,179,237,.15)!important;border-radius:10px!important}
.stSuccess{background:rgba(74,222,128,.08)!important;border-color:rgba(74,222,128,.3)!important;border-radius:8px!important;color:#bbf7d0!important}
.stError{background:rgba(248,113,113,.08)!important;border-color:rgba(248,113,113,.3)!important;border-radius:8px!important;color:#fecaca!important}
.stWarning{background:rgba(251,191,36,.08)!important;border-color:rgba(251,191,36,.3)!important;border-radius:8px!important;color:#fde68a!important}
.stInfo{background:rgba(99,179,237,.08)!important;border-color:rgba(99,179,237,.25)!important;border-radius:8px!important;color:#bae6fd!important}
h1,h2,h3,h4,h5,h6{color:#e8f0fe!important}
p,span,label,.stMarkdown{color:#c0d0e8!important}
.stCaption{color:#8ba3c7!important}
a{color:#93c5fd!important}
hr{border-color:rgba(99,179,237,.12)!important}
.kpi-card{background:linear-gradient(135deg,rgba(99,179,237,.08),rgba(139,92,246,.06));border:1px solid rgba(99,179,237,.2);border-radius:14px;padding:20px 24px;text-align:center}
.kpi-value{font-size:2rem;font-weight:700;color:#e8f0fe;line-height:1}
.kpi-label{font-size:.75rem;font-weight:600;color:#8ba3c7;letter-spacing:.07em;text-transform:uppercase;margin-top:6px}
.kpi-delta{font-size:.8rem;color:#4ade80;margin-top:4px}
.severity-critical{color:#f87171;font-weight:600}
.severity-high{color:#fb923c;font-weight:600}
.severity-medium{color:#fbbf24;font-weight:600}
.severity-low{color:#4ade80;font-weight:600}
.section-header{font-size:1rem;font-weight:600;color:#93c5fd;letter-spacing:.04em;text-transform:uppercase;margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid rgba(99,179,237,.15)}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _excel_available() -> bool:
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        return False


# ── Data loading ──────────────────────────────────────────────────────────────
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "CrewOps-Hackathon")
LS_API_KEY   = os.getenv("LANGCHAIN_API_KEY", "")

MOCK_RUNS: list[dict] = [
    {"run_id": f"run-{i:03d}", "name": f"CrewOps | run-{i:03d}",
     "start_time": datetime(2025, 6, 1, tzinfo=timezone.utc) + timedelta(hours=i * 3),
     "duration_s": 12 + (i % 7) * 3,
     "status": "success" if i % 8 != 0 else "error",
     "total_tokens": 1800 + i * 120,
     "log_type": ["kubernetes", "nginx", "cloudwatch", "application", "database", "other", "mixed"][i % 7],
     "severity": ["P1 CRITICAL", "P2 HIGH", "P3 MEDIUM", "P4 LOW", "P1 CRITICAL", "P2 HIGH", "P3 MEDIUM"][i % 7],
     "critical_issues": max(0, 3 - (i % 4)),
     "service_name": ["UserService", "PaymentService", "NotificationService", "AuthService", "OrderService"][i % 5],
     "environment": ["Production", "Staging", "Development"][i % 3],
     }
    for i in range(1, 41)
]


@st.cache_data(ttl=120, show_spinner=False)
def load_runs(limit: int = 200) -> pd.DataFrame:
    """Try LangSmith first; fall back to mock data."""
    rows: list[dict] = []
    if LS_API_KEY:
        try:
            from langsmith import Client
            client = Client(api_key=LS_API_KEY)
            for run in client.list_runs(project_name=PROJECT_NAME, is_root=True, limit=limit):
                inp  = run.inputs  or {}
                outp = run.outputs or {}
                rows.append({
                    "run_id":         str(run.id),
                    "name":           run.name or "",
                    "start_time":     run.start_time.replace(tzinfo=timezone.utc) if run.start_time and run.start_time.tzinfo is None else run.start_time,
                    "duration_s":     round((run.end_time - run.start_time).total_seconds(), 1)
                                      if run.end_time and run.start_time else None,
                    "status":         run.status or "unknown",
                    "total_tokens":   run.total_tokens or 0,
                    "log_type":       inp.get("log_type") or outp.get("log_type", "unknown"),
                    "severity":       inp.get("severity") or outp.get("severity", ""),
                    "critical_issues":inp.get("critical_issues") or outp.get("critical_issues", 0),
                    "service_name":   inp.get("service_name", "—"),
                    "environment":    inp.get("environment", "—"),
                })
        except Exception:
            pass  # fall through to mock

    if not rows:
        rows = MOCK_RUNS  # type: ignore[assignment]
        st.caption("ℹ️ Showing demo data — connect LangSmith for live analytics.")

    df = pd.DataFrame(rows)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True, errors="coerce")
    df["date"]       = df["start_time"].dt.date
    df["total_tokens"] = pd.to_numeric(df["total_tokens"], errors="coerce").fillna(0).astype(int)
    df["duration_s"]   = pd.to_numeric(df["duration_s"], errors="coerce")
    df["severity_label"] = df["severity"].str.split(" ").str[0].fillna("Unknown")
    return df


# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")

    limit = st.slider("Max runs to fetch", 25, 500, 200, 25)

    if st.button("🔄  Refresh Data", type="primary", use_container_width=True):
        load_runs.clear()
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-header">FILTERS</div>', unsafe_allow_html=True)

    df_all = load_runs(limit)

    # Date range
    min_date = df_all["date"].min()
    max_date = df_all["date"].max()
    date_from = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
    date_to   = st.date_input("End date",   value=max_date, min_value=min_date, max_value=max_date)

    # Log type chips
    all_types = sorted(df_all["log_type"].dropna().unique())
    sel_types = st.multiselect("Log Type", all_types, default=all_types, key="type_filter")

    # Severity
    all_sevs = sorted(df_all["severity_label"].dropna().unique())
    sel_sevs  = st.multiselect("Severity", all_sevs, default=all_sevs, key="sev_filter")

    # Status
    all_statuses = sorted(df_all["status"].dropna().unique())
    sel_statuses  = st.multiselect("Status", all_statuses, default=all_statuses, key="status_filter")

    # Environment
    all_envs = sorted(df_all["environment"].dropna().unique())
    sel_envs  = st.multiselect("Environment", all_envs, default=all_envs, key="env_filter")

    # Search
    search = st.text_input("🔍 Search run name", placeholder="e.g. nginx, payment…")

# ── Apply filters ─────────────────────────────────────────────────────────────
df = df_all.copy()
df = df[(df["date"] >= date_from) & (df["date"] <= date_to)]
if sel_types:
    df = df[df["log_type"].isin(sel_types)]
if sel_sevs:
    df = df[df["severity_label"].isin(sel_sevs)]
if sel_statuses:
    df = df[df["status"].isin(sel_statuses)]
if sel_envs:
    df = df[df["environment"].isin(sel_envs)]
if search:
    df = df[df["name"].str.contains(search, case=False, na=False)]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="font-size:1.8rem;font-weight:700;margin-bottom:4px">'
    '📊 Log Analysis Dashboard</h1>'
    '<p style="color:#8ba3c7;margin-bottom:24px">Real-time pipeline metrics &amp; log classification analytics</p>',
    unsafe_allow_html=True,
)

# ── KPI row ───────────────────────────────────────────────────────────────────
total_runs     = len(df)
success_runs   = (df["status"] == "success").sum()
error_runs     = (df["status"] == "error").sum()
total_tokens   = int(df["total_tokens"].sum())
critical_count = (df["severity_label"] == "P1").sum()
high_count     = (df["severity_label"] == "P2").sum()
avg_duration   = df["duration_s"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Runs",         total_runs)
c2.metric("✅ Successful",      success_runs, delta=f"{success_runs/max(total_runs,1)*100:.0f}%")
c3.metric("❌ Errors",          error_runs)
c4.metric("🔴 Critical (P1)",  critical_count)
c5.metric("🔥 High (P2)",      high_count)

c6, c7 = st.columns(2)
c6.metric("Total Tokens Used",  f"{total_tokens:,}")
c7.metric("Avg Pipeline Time",  f"{avg_duration:.1f}s" if pd.notna(avg_duration) else "—")

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Trends", "🗂️ Distribution", "📋 Classified Issues"])

with tab1:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-header">Issues Over Time</div>', unsafe_allow_html=True)
        time_series = (
            df.groupby("date").size().reset_index(name="count")
        )
        if not time_series.empty:
            time_series["date"] = pd.to_datetime(time_series["date"])
            st.line_chart(time_series.set_index("date")["count"], color="#3b82f6", height=260)
        else:
            st.info("No data for selected range.")

    with col_b:
        st.markdown('<div class="section-header">Token Usage Over Time</div>', unsafe_allow_html=True)
        tok_series = (
            df.groupby("date")["total_tokens"].sum().reset_index()
        )
        if not tok_series.empty:
            tok_series["date"] = pd.to_datetime(tok_series["date"])
            st.area_chart(tok_series.set_index("date")["total_tokens"], color="#7c3aed", height=260)
        else:
            st.info("No token data.")

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown('<div class="section-header">Pipeline Success Rate by Day</div>', unsafe_allow_html=True)
        daily = df.groupby(["date", "status"]).size().unstack(fill_value=0).reset_index()
        daily["date"] = pd.to_datetime(daily["date"])
        if not daily.empty:
            st.bar_chart(daily.set_index("date"), height=260, color=["#4ade80", "#f87171"] if "success" in daily.columns and "error" in daily.columns else None)
        else:
            st.info("No data.")

    with col_d:
        st.markdown('<div class="section-header">Average Duration by Log Type</div>', unsafe_allow_html=True)
        dur_by_type = df.groupby("log_type")["duration_s"].mean().dropna().sort_values(ascending=False)
        if not dur_by_type.empty:
            st.bar_chart(dur_by_type, color="#93c5fd", height=260)
        else:
            st.info("No duration data.")

with tab2:
    col_e, col_f = st.columns(2)

    with col_e:
        st.markdown('<div class="section-header">Severity Distribution</div>', unsafe_allow_html=True)
        sev_counts = df["severity_label"].value_counts()
        if not sev_counts.empty:
            sev_df = sev_counts.reset_index()
            sev_df.columns = ["Severity", "Count"]
            st.bar_chart(sev_df.set_index("Severity"), color="#f87171", height=280)
        else:
            st.info("No severity data.")

    with col_f:
        st.markdown('<div class="section-header">Log Type Distribution</div>', unsafe_allow_html=True)
        type_counts = df["log_type"].value_counts()
        if not type_counts.empty:
            type_df = type_counts.reset_index()
            type_df.columns = ["Log Type", "Count"]
            st.bar_chart(type_df.set_index("Log Type"), color="#7c3aed", height=280)
        else:
            st.info("No log type data.")

    col_g, col_h = st.columns(2)

    with col_g:
        st.markdown('<div class="section-header">Runs by Environment</div>', unsafe_allow_html=True)
        env_counts = df["environment"].value_counts()
        if not env_counts.empty:
            st.bar_chart(env_counts, color="#4ade80", height=240)
        else:
            st.info("No environment data.")

    with col_h:
        st.markdown('<div class="section-header">Runs by Service</div>', unsafe_allow_html=True)
        svc_counts = df["service_name"].value_counts().head(10)
        if not svc_counts.empty:
            st.bar_chart(svc_counts, color="#fbbf24", height=240)
        else:
            st.info("No service data.")

with tab3:
    st.markdown('<div class="section-header">Classified Issues</div>', unsafe_allow_html=True)

    # Table columns
    display_cols = ["name", "date", "log_type", "severity", "environment",
                    "service_name", "status", "total_tokens", "duration_s"]
    display_cols = [c for c in display_cols if c in df.columns]
    df_display = df[display_cols].sort_values("date", ascending=False) if "date" in df.columns else df[display_cols]

    # Rename for readability
    col_rename = {
        "name": "Run Name", "date": "Date", "log_type": "Log Type",
        "severity": "Severity", "environment": "Environment",
        "service_name": "Service", "status": "Status",
        "total_tokens": "Tokens", "duration_s": "Duration (s)"
    }
    df_display = df_display.rename(columns=col_rename)

    st.dataframe(df_display, use_container_width=True, height=480)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("---")
    col_exp1, col_exp2, _ = st.columns([1, 1, 3])
    with col_exp1:
        csv_bytes = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️  Export CSV",
            data=csv_bytes,
            file_name=f"crewops_runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )
    with col_exp2:
        buf = io.BytesIO()
        df_display.to_excel(buf, index=False, engine="openpyxl") if _excel_available() else None
        if _excel_available():
            st.download_button(
                label="⬇️  Export Excel",
                data=buf.getvalue(),
                file_name=f"crewops_runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="secondary",
                use_container_width=True,
            )





# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"📡 Project: **{PROJECT_NAME}** · Data refreshes every 2 min · "
           f"Showing **{len(df)}** of **{len(df_all)}** total runs")

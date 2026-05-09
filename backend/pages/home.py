"""
CrewOps — Home Page (main analysis workflow)
"""
import os, time, threading
from pathlib import Path
from functools import partial

import streamlit as st

# ── Top-left logo + title ─────────────────────────────────────────────────────
_logo_col, _title_col = st.columns([1, 6], vertical_alignment="center")
with _logo_col:
    st.image("assets/logo_nobg.png", use_container_width=True)
with _title_col:
    st.markdown("""
    <div style="padding-left:4px">
      <div style="font-size:1.45rem;font-weight:700;color:#e8f0fe;line-height:1.15;letter-spacing:-.01em">
        CrewOps
      </div>
      <div style="font-size:.78rem;color:#8ba3c7;letter-spacing:.03em;margin-top:1px">
        AI Incident Management Platform
      </div>
    </div>
    """, unsafe_allow_html=True)
st.markdown('<div style="margin-bottom:16px"></div>', unsafe_allow_html=True)

# ── Sidebar (Home-only controls) ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="nav-section">AI Models</div>', unsafe_allow_html=True)
    fast_model = st.selectbox("Fast", ["openai/gpt-4o-mini","openai/gpt-4o","anthropic/claude-3-haiku","google/gemini-flash-1.5"], label_visibility="collapsed")
    st.caption("⚡ Fast / classifier model")
    smart_model = st.selectbox("Reasoning", ["openai/gpt-4o","openai/gpt-4o-mini","anthropic/claude-3-5-sonnet","google/gemini-pro-1.5"], label_visibility="collapsed")
    st.caption("🧠 Deep reasoning model")

    st.session_state["fast_model"]  = fast_model
    st.session_state["smart_model"] = smart_model

    st.markdown('<div class="nav-section">Integrations</div>', unsafe_allow_html=True)
    jira_mock  = st.toggle("JIRA mock mode",   value=os.environ.get("JIRA_MOCK_MODE","True").lower() not in ("false","0","no"))
    notif_mock = st.toggle("Notify mock mode", value=os.environ.get("NOTIFICATION_MOCK_MODE","True").lower() not in ("false","0","no"))
    st.session_state["jira_mock"]   = jira_mock
    st.session_state["notif_mock"]  = notif_mock

    st.markdown('<div class="nav-section">API Status</div>', unsafe_allow_html=True)
    api_ok = bool(os.environ.get("OPENROUTER_API_KEY"))
    ls_ok  = bool(os.environ.get("LANGCHAIN_API_KEY"))
    st.markdown(f"""
    <div style="display:flex;flex-direction:column;gap:8px;padding:4px 0 12px">
      <div style="display:flex;align-items:center;gap:8px;font-size:.82rem;color:#c0d0e8">
        <span class="{'dot-green' if api_ok else 'dot-red'}">●</span>
        OpenRouter {'Connected' if api_ok else 'Missing key'}
      </div>
      <div style="display:flex;align-items:center;gap:8px;font-size:.82rem;color:#c0d0e8">
        <span class="{'dot-green' if ls_ok else 'dot-red'}">●</span>
        LangSmith {'Connected' if ls_ok else 'Missing key'}
      </div>
      <div style="display:flex;align-items:center;gap:8px;font-size:.82rem;color:#c0d0e8">
        <span class="{'dot-red' if jira_mock else 'dot-green'}">●</span>
        JIRA {'Mock' if jira_mock else 'Live'}
      </div>
      <div style="display:flex;align-items:center;gap:8px;font-size:.82rem;color:#c0d0e8">
        <span class="{'dot-red' if notif_mock else 'dot-green'}">●</span>
        Alerts {'Mock' if notif_mock else 'Live'}
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    <div style="padding:12px;background:rgba(59,130,246,.06);border:1px solid rgba(99,179,237,.15);border-radius:10px">
      <div style="font-size:.68rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#60a5fa;margin-bottom:6px">System Health</div>
      <div style="font-size:1.4rem;font-weight:700;color:#4ade80">Operational</div>
      <div style="font-size:.72rem;color:#8ba3c7;margin-top:2px">All 7 agents ready</div>
    </div>
    """, unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="crewops-hero">
  <div class="hero-badge">⚡ Multi-Agent DevOps Platform</div>
  <h1 class="hero-title">Observability. Triage. <span class="hero-accent">Automate.</span></h1>
  <p class="hero-sub">7 AI agents analyse logs, perform root-cause analysis, generate runbooks,
  create JIRA tickets and send real-time alerts &mdash; in under 60 seconds.</p>
</div>
""", unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
tab_input, tab_samples = st.tabs(["📋  Log Input", "📁  Sample Logs"])

with tab_samples:
    sample_dir = Path("data/sample_logs")
    sample_files = sorted(sample_dir.glob("*.log")) if sample_dir.exists() else []
    if sample_files:
        cs, cb2 = st.columns([3,1])
        with cs:
            chosen = st.selectbox("Sample", ["— select —"] + [f.name for f in sample_files])
        with cb2:
            st.write("")
            if chosen != "— select —" and st.button("Load →", key="load_sample", type="secondary"):
                st.session_state["log_text"]   = (sample_dir / chosen).read_text()
                st.session_state["log_source"] = chosen
                st.success(f"Loaded **{chosen}**")
    else:
        st.info("No sample logs found in `data/sample_logs/`")

with tab_input:
    cu, cp = st.columns([1,2])
    with cu:
        uploaded = st.file_uploader("Upload log file", type=["log","txt","json"])
        if uploaded:
            content = uploaded.read().decode("utf-8", errors="replace")
            st.session_state["log_text"]   = content
            st.session_state["log_source"] = uploaded.name
            st.success(f"**{uploaded.name}** — {len(content):,} chars")
    with cp:
        log_text = st.text_area("Or paste log content",
            value=st.session_state.get("log_text",""), height=180,
            placeholder="Paste Kubernetes, Nginx, CloudWatch or application logs here…",
            key="log_paste")
        if log_text:
            st.session_state["log_text"] = log_text
            if "log_source" not in st.session_state:
                st.session_state["log_source"] = "(pasted)"

st.write("")
raw_log = st.session_state.get("log_text","").strip()
cb1, cb2 = st.columns([1,4])
with cb1:
    run_btn = st.button("⚡  Analyse Incident", type="primary", disabled=not raw_log, use_container_width=True)
with cb2:
    if not raw_log:
        st.markdown('<div style="padding-top:10px;color:#8ba3c7;font-size:.85rem">↑ Upload or paste logs to begin analysis</div>', unsafe_allow_html=True)
    else:
        src = st.session_state.get("log_source","input")
        st.markdown(f'<div style="padding-top:10px;font-size:.82rem;color:#8ba3c7"><span style="color:#60a5fa;font-weight:600">{src}</span>&nbsp;·&nbsp;{raw_log.count(chr(10))+1:,} lines&nbsp;·&nbsp;{len(raw_log):,} chars</div>', unsafe_allow_html=True)

# ── Pipeline ──────────────────────────────────────────────────────────────────
if run_btn and raw_log:
    if not os.environ.get("OPENROUTER_API_KEY"):
        st.error("OPENROUTER_API_KEY not set."); st.stop()

    from langchain_openrouter import ChatOpenRouter
    from langchain_core.tracers.langchain import LangChainTracer
    from crewops.agents import configure_llms, notification_node, jira_node
    from crewops.graph import build_graph
    from crewops.state import CrewOpsState

    configure_llms(
        fast=ChatOpenRouter(model=fast_model, temperature=0.1, max_tokens=2000),
        reasoning=ChatOpenRouter(model=smart_model, temperature=0.2, max_tokens=4000),
        generation=ChatOpenRouter(model=fast_model, temperature=0.3, max_tokens=6000),
    )
    configured_notification = partial(notification_node, mock_mode=notif_mock,
        n8n_webhook_url=os.environ.get("N8N_WEBHOOK_URL",""),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL",""))
    configured_jira = partial(jira_node, mock_mode=jira_mock,
        jira_server=os.environ.get("JIRA_SERVER",""), jira_email=os.environ.get("JIRA_EMAIL",""),
        jira_api_token=os.environ.get("JIRA_API_TOKEN",""), jira_project_key=os.environ.get("JIRA_PROJECT_KEY","SCRUM"),
        jira_epic_key=os.environ.get("JIRA_EPIC_KEY",""), jira_sprint_name=os.environ.get("JIRA_SPRINT_NAME",""))

    graph  = build_graph(notification_fn=configured_notification, jira_fn=configured_jira)
    tracer = LangChainTracer(project_name=os.environ.get("LANGCHAIN_PROJECT","CrewOps-Hackathon"))
    initial_state: CrewOpsState = {
        "raw_logs":raw_log, "metadata":{"source":st.session_state.get("log_source","ui"),"runner":"streamlit"},
        "log_summary":"","log_type":"","severity":"","severity_rationale":"",
        "approval_required":False,"approval_status":"pending","critical_issues":[],
        "rag_context":[],"root_cause_analysis":"","remediation_plan":"","cookbook":"",
        "jira_tickets":[],"notifications_sent":[],"pipeline_status":{},"errors":[],
    }

    AGENTS=[("🔍","Classifier","classifier"),("🎯","Severity","severity"),
            ("🔬","Root Cause","root_cause"),("🔧","Remediation","remediation"),
            ("📖","Runbook","cookbook"),("🎫","JIRA","jira"),("📣","Alerts","notification")]

    st.write("")
    st.markdown('<div style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#4a6080;margin-bottom:10px">Pipeline Execution</div>', unsafe_allow_html=True)
    prog = st.progress(0, text="Initialising agents…")
    acs  = st.columns(7); slots=[]
    for i,(icon,name,_) in enumerate(AGENTS):
        with acs[i]:
            s=st.empty()
            s.markdown(f'<div class="agent-card"><div class="agent-icon">{icon}</div><div class="agent-name">{name}</div><div class="agent-st" style="color:#4a6080">waiting</div></div>',unsafe_allow_html=True)
            slots.append(s)

    t0=time.time(); res_h={}; err_h={}

    def _run():
        try:
            res_h["state"]=graph.invoke(initial_state,config={"callbacks":[tracer],"run_name":f"CrewOps | {st.session_state.get('log_source','ui')}"})
        except Exception as e:
            err_h["err"]=str(e)

    th=threading.Thread(target=_run,daemon=True); th.start()
    spf=list("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"); f=0

    while th.is_alive():
        time.sleep(0.4); f+=1; sp=spf[f%10]
        cur=res_h.get("state",{}).get("pipeline_status",{})
        dn=len([v for v in cur.values() if isinstance(v,dict) and v.get("status") in ("done","done_mock","skipped")])
        prog.progress(max(5,int(dn/7*95)),text=f"{sp} Running — {dn}/7 agents complete")
        for idx,(icon,name,key) in enumerate(AGENTS):
            info=cur.get(key,{})
            if not isinstance(info,dict): continue
            s=info.get("status","")
            if s in ("done","done_mock","skipped"):
                t=f"{info.get('elapsed_s',0):.1f}s"
                slots[idx].markdown(f'<div class="agent-card a-done"><div class="agent-icon">{icon}</div><div class="agent-name">{name}</div><div class="agent-st" style="color:#4ade80">✓ {t}</div></div>',unsafe_allow_html=True)
            elif s=="error":
                slots[idx].markdown(f'<div class="agent-card a-err"><div class="agent-icon">{icon}</div><div class="agent-name">{name}</div><div class="agent-st" style="color:#f87171">✗ error</div></div>',unsafe_allow_html=True)

    th.join(); elapsed=time.time()-t0
    if "err" in err_h: st.error(f"Pipeline error: {err_h['err']}"); st.stop()
    result=res_h.get("state",{}); fps=result.get("pipeline_status",{})
    prog.progress(100,text=f"✅ Analysis complete — {elapsed:.1f}s")

    for idx,(icon,name,key) in enumerate(AGENTS):
        info=fps.get(key,{})
        if isinstance(info,dict):
            s=info.get("status",""); t=f"{info.get('elapsed_s',0):.1f}s"
            css="a-done" if s in ("done","done_mock","skipped") else "a-err" if s=="error" else ""
            stat=f"✓ {t}" if css=="a-done" else "✗ err" if css=="a-err" else ""
            col=("#4ade80" if css=="a-done" else "#f87171") if css else "#4a6080"
            slots[idx].markdown(f'<div class="agent-card {css}"><div class="agent-icon">{icon}</div><div class="agent-name">{name}</div><div class="agent-st" style="color:{col}">{stat}</div></div>',unsafe_allow_html=True)

    # results
    st.write("")
    st.markdown('<div style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#4a6080;margin-bottom:12px">Analysis Results</div>', unsafe_allow_html=True)
    sev=result.get("severity","??"); log_type=result.get("log_type","?").upper()
    issues=result.get("critical_issues",[]); approval=result.get("approval_required",False)
    SEV_E={"P1":"🔴","P2":"🟠","P3":"🟡","P4":"🟢"}
    sev_e=SEV_E.get(sev,"⚪")
    m1,m2,m3,m4,m5=st.columns(5)
    m1.metric("Severity",f"{sev_e} {sev}")
    m2.metric("Log Type",log_type)
    m3.metric("Critical Issues",str(len(issues)))
    m4.metric("Approval","Required ⚠️" if approval else "Auto-resolved ✅")
    m5.metric("Pipeline Time",f"{elapsed:.1f}s")
    sev_c=f"sev-{sev.lower()}" if sev in ("P1","P2","P3","P4") else "sev-p4"
    rat=result.get("severity_rationale","")
    st.markdown(f'<div class="{sev_c} sev-banner">{sev_e} {sev}&nbsp;&nbsp;·&nbsp;&nbsp;{rat[:200]}</div>',unsafe_allow_html=True)

    st.write("")
    r1,r2,r3,r4,r5,r6=st.tabs(["📋  Summary","🔬  Root Cause","🔧  Remediation","📖  Runbook","🎫  JIRA & Alerts","⏱️  Pipeline"])

    with r1:
        if issues:
            st.markdown('<div class="result-card"><h4>Critical Issues ('+str(len(issues))+')</h4>',unsafe_allow_html=True)
            for i,iss in enumerate(issues,1):
                title=iss.get("title",str(iss)) if isinstance(iss,dict) else str(iss)
                sev_i=iss.get("severity","") if isinstance(iss,dict) else ""
                lbl=f"[{sev_i}] " if sev_i else ""
                st.markdown(f'<div class="issue-row"><div class="issue-num">#{i}</div><div class="issue-text"><b style="color:#f87171">{lbl}</b>{title}</div></div>',unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)
        st.markdown('<div class="result-card"><h4>Log Summary</h4>',unsafe_allow_html=True)
        st.markdown(f'<div style="color:#c0d0e8;line-height:1.65;font-size:.9rem">{result.get("log_summary","—")}</div>',unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
        rag=result.get("rag_context",[])
        if rag:
            with st.expander(f"📚 Knowledge Base — {len(rag)} source(s) referenced"):
                for item in rag: st.caption(str(item)[:400])

    with r2:
        rca=result.get("root_cause_analysis","")
        if rca:
            st.markdown('<div class="result-card"><h4>Root Cause Analysis</h4>',unsafe_allow_html=True)
            st.markdown(rca); st.markdown("</div>",unsafe_allow_html=True)
        else: st.info("Root cause analysis skipped (P3/P4 — summary-only path)")

    with r3:
        remed=result.get("remediation_plan","")
        if remed:
            st.markdown('<div class="result-card"><h4>Remediation Plan</h4>',unsafe_allow_html=True)
            st.markdown(remed); st.markdown("</div>",unsafe_allow_html=True)
        else: st.info("Remediation plan not generated")

    with r4:
        cb=result.get("cookbook","")
        if cb:
            st.markdown('<div class="result-card"><h4>Operations Runbook</h4>',unsafe_allow_html=True)
            st.markdown(cb); st.markdown("</div>",unsafe_allow_html=True)
        else: st.info("Runbook not generated")

    with r5:
        tickets=result.get("jira_tickets",[]); notifs=result.get("notifications_sent",[]); errors=result.get("errors",[])
        cj,cn=st.columns(2)
        with cj:
            st.markdown('<div class="result-card"><h4>JIRA Tickets</h4>',unsafe_allow_html=True)
            if tickets:
                for tk in tickets:
                    if isinstance(tk,dict):
                        key=tk.get("key","?"); url=tk.get("url","#"); mode=tk.get("mode","mock")
                        if key=="ERR": st.error(f"Error: {tk.get('error','?')}")
                        else:
                            live=mode!="mock"
                            cls="t-live" if live else "t-mock"; lbl="● LIVE" if live else "○ mock"
                            st.markdown(f'<div class="ticket-row"><a href="{url}" target="_blank" class="ticket-key">{key} ↗</a><span class="{cls}">{lbl}</span></div>',unsafe_allow_html=True)
            else: st.caption("No tickets created")
            st.markdown("</div>",unsafe_allow_html=True)
        with cn:
            st.markdown('<div class="result-card"><h4>Notifications</h4>',unsafe_allow_html=True)
            if notifs:
                for n in notifs:
                    if isinstance(n,dict):
                        ch=n.get("channel","?"); s=n.get("status","?"); ok="delivered" in s.lower()
                        st.markdown(f'<div class="notif-row"><span>{"✅" if ok else "⚠️"}</span><span><b>{ch}</b> — {s}</span></div>',unsafe_allow_html=True)
            else: st.caption("No notifications sent")
            st.markdown("</div>",unsafe_allow_html=True)
        if errors:
            st.markdown('<div class="result-card"><h4>Pipeline Errors</h4>',unsafe_allow_html=True)
            for e in errors: st.warning(str(e))
            st.markdown("</div>",unsafe_allow_html=True)
        ls_proj=os.environ.get("LANGCHAIN_PROJECT","CrewOps-Hackathon")
        st.markdown(f'<div style="margin-top:12px;font-size:.8rem;color:#8ba3c7">📊 <a href="https://smith.langchain.com" target="_blank">View LangSmith traces</a>&nbsp;·&nbsp;Project: <span style="color:#93c5fd">{ls_proj}</span></div>',unsafe_allow_html=True)

    with r6:
        ps=result.get("pipeline_status",{})
        if ps:
            import pandas as pd
            rows=[]
            for agent,info in sorted(ps.items()):
                if isinstance(info,dict):
                    st2=info.get("status","?")
                    rows.append({"Agent":agent.replace("_"," ").title(),"Status":("✅ " if st2 in ("done","done_mock","skipped") else "❌ " if st2=="error" else "⏳ ")+st2,"Time (s)":round(info.get("elapsed_s",0),2),"Mode":info.get("mode","—")})
            if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        fm=fast_model.split("/")[-1]; sm=smart_model.split("/")[-1]
        st.markdown(f'<div style="margin-top:14px;display:flex;gap:12px;flex-wrap:wrap"><span class="chip">⏱ Wall time: {elapsed:.1f}s</span><span class="chip">🤖 7 agents</span><span class="chip">⚡ {fm}</span><span class="chip">🧠 {sm}</span></div>',unsafe_allow_html=True)

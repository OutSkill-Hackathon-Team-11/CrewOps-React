"""
CrewOps — Streamlit Web UI  (Dark DevOps Edition)
Run with: streamlit run app.py
"""
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

st.set_page_config(page_title="CrewOps", page_icon="\u26a1", layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important}
.stApp{background:linear-gradient(135deg,#060b18 0%,#0d1424 40%,#0a1628 70%,#060b18 100%)!important}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1120,#0d1528)!important;border-right:1px solid rgba(99,179,237,.15)!important}
[data-testid="stSidebar"]>div:first-child{padding-top:1.5rem}
[data-testid="stHeader"]{background:rgba(6,11,24,.95)!important;border-bottom:1px solid rgba(99,179,237,.12)!important}
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden}
[data-testid="collapsedControl"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}
[data-testid="stSidebar"][aria-expanded="false"]{display:flex!important;min-width:21rem!important;width:21rem!important}
[data-testid="stSidebar"][aria-expanded="true"]{min-width:21rem!important;width:21rem!important}
section[data-testid="stSidebar"]>div{pointer-events:auto!important}

[data-testid="stMetric"]{background:linear-gradient(135deg,rgba(99,179,237,.08),rgba(139,92,246,.06));border:1px solid rgba(99,179,237,.18);border-radius:12px;padding:16px 20px!important}
[data-testid="stMetric"] label{color:#8ba3c7!important;font-size:.73rem!important;font-weight:600!important;letter-spacing:.06em;text-transform:uppercase}
[data-testid="stMetricValue"]{color:#e8f0fe!important;font-size:1.55rem!important;font-weight:700!important}
[data-testid="stMetricDelta"]{color:#4ade80!important}

.stButton>button[kind="primary"]{background:linear-gradient(135deg,#3b82f6,#7c3aed)!important;border:none!important;border-radius:8px!important;color:#fff!important;font-weight:600!important;padding:.55rem 1.6rem!important;box-shadow:0 0 20px rgba(59,130,246,.35)}
.stButton>button[kind="primary"]:hover{box-shadow:0 0 32px rgba(59,130,246,.55)!important}
.stButton>button[kind="secondary"]{background:rgba(99,179,237,.07)!important;border:1px solid rgba(99,179,237,.25)!important;border-radius:8px!important;color:#93c5fd!important;font-weight:500!important}

.stTextArea textarea,[data-testid="stFileUploader"]{background:rgba(13,20,40,.8)!important;border:1px solid rgba(99,179,237,.2)!important;border-radius:8px!important;color:#e2e8f0!important}
.stTextArea textarea::placeholder{color:rgba(139,163,199,.5)!important}
[data-testid="stSelectbox"]>div>div{background:rgba(13,20,40,.8)!important;border:1px solid rgba(99,179,237,.2)!important;border-radius:8px!important;color:#e2e8f0!important}

.stTabs [data-baseweb="tab-list"]{background:rgba(13,20,40,.6)!important;border-radius:10px!important;border:1px solid rgba(99,179,237,.12)!important;padding:4px;gap:2px}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:8px!important;color:#8ba3c7!important;font-weight:500!important;padding:8px 16px!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(59,130,246,.25),rgba(124,58,237,.2))!important;color:#93c5fd!important;border:1px solid rgba(99,179,237,.3)!important}

.stProgress>div>div>div>div{background:linear-gradient(90deg,#3b82f6,#7c3aed)!important;border-radius:4px!important}
.stProgress>div>div{background:rgba(99,179,237,.1)!important;border-radius:4px!important}

[data-testid="stDataFrame"]{background:rgba(13,20,40,.8)!important;border:1px solid rgba(99,179,237,.15)!important;border-radius:10px!important}
[data-testid="stExpander"]{background:rgba(13,20,40,.6)!important;border:1px solid rgba(99,179,237,.15)!important;border-radius:10px!important}

.stSuccess{background:rgba(74,222,128,.08)!important;border-color:rgba(74,222,128,.3)!important;border-radius:8px!important;color:#bbf7d0!important}
.stError{background:rgba(248,113,113,.08)!important;border-color:rgba(248,113,113,.3)!important;border-radius:8px!important;color:#fecaca!important}
.stWarning{background:rgba(251,191,36,.08)!important;border-color:rgba(251,191,36,.3)!important;border-radius:8px!important;color:#fde68a!important}
.stInfo{background:rgba(99,179,237,.08)!important;border-color:rgba(99,179,237,.25)!important;border-radius:8px!important;color:#bae6fd!important}
hr{border-color:rgba(99,179,237,.12)!important}

h1,h2,h3,h4,h5,h6{color:#e8f0fe!important}
p,span,label,.stMarkdown{color:#c0d0e8!important}
.stCaption{color:#8ba3c7!important}
a{color:#93c5fd!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label{color:#c0d0e8!important}
.dot-green,[data-testid="stSidebar"] .dot-green{color:#4ade80!important;font-size:1rem}
.dot-red,[data-testid="stSidebar"] .dot-red{color:#f87171!important;font-size:1rem}

.crewops-hero{background:linear-gradient(135deg,rgba(13,20,40,.95),rgba(20,30,60,.9));border:1px solid rgba(99,179,237,.2);border-radius:16px;padding:32px 40px;margin-bottom:24px;position:relative;overflow:hidden}
.crewops-hero::before{content:'';position:absolute;top:-50%;right:-10%;width:500px;height:500px;background:radial-gradient(circle,rgba(99,179,237,.07) 0%,transparent 70%);pointer-events:none}
.crewops-hero::after{content:'';position:absolute;bottom:-30%;right:10%;width:300px;height:300px;background:radial-gradient(circle,rgba(124,58,237,.09) 0%,transparent 70%);pointer-events:none}
.hero-badge{display:inline-block;background:linear-gradient(135deg,rgba(59,130,246,.2),rgba(124,58,237,.2));border:1px solid rgba(99,179,237,.3);border-radius:20px;padding:4px 14px;font-size:.72rem;font-weight:600;color:#93c5fd;letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px}
.hero-title{font-size:2.3rem;font-weight:700;color:#e8f0fe;line-height:1.2;margin:0 0 4px}
.hero-accent{color:#60a5fa}
.hero-sub{font-size:.92rem;color:#8ba3c7;margin:8px 0 0;max-width:680px}

.sidebar-logo{display:flex;align-items:center;gap:10px;padding:8px 4px 20px;border-bottom:1px solid rgba(99,179,237,.12);margin-bottom:20px}
.logo-icon{width:36px;height:36px;background:linear-gradient(135deg,#3b82f6,#7c3aed);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:1.1rem}
.logo-name{font-size:1.1rem;font-weight:700;color:#e8f0fe!important}
.logo-sub{font-size:.63rem;color:#8ba3c7!important;letter-spacing:.07em;text-transform:uppercase}
.nav-section{font-size:.63rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#4a6080!important;padding:16px 0 6px}

.agent-card{background:rgba(13,20,40,.7);border:1px solid rgba(99,179,237,.14);border-radius:10px;padding:14px 8px;text-align:center;min-height:88px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}
.agent-icon{font-size:1.3rem;line-height:1}
.agent-name{font-size:.65rem;font-weight:600;color:#8ba3c7;letter-spacing:.04em;text-transform:uppercase}
.agent-st{font-size:.72rem}
.a-done{border-color:rgba(74,222,128,.35)!important;background:rgba(74,222,128,.05)!important}
.a-err{border-color:rgba(248,113,113,.35)!important;background:rgba(248,113,113,.05)!important}

.sev-p1{background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.35);color:#fca5a5}
.sev-p2{background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.35);color:#fde68a}
.sev-p3{background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.25);color:#fef08a}
.sev-p4{background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.3);color:#bbf7d0}
.sev-banner{display:inline-flex;align-items:center;gap:8px;border-radius:8px;padding:10px 18px;font-weight:600;font-size:.9rem;margin:8px 0}

.result-card{background:linear-gradient(135deg,rgba(13,20,40,.95),rgba(16,24,48,.9));border:1px solid rgba(99,179,237,.15);border-radius:12px;padding:20px 24px;margin-bottom:16px}
.result-card h4{color:#93c5fd!important;font-size:.73rem!important;font-weight:700!important;letter-spacing:.09em;text-transform:uppercase;margin-bottom:12px!important}

.issue-row{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border-radius:8px;margin-bottom:8px;background:rgba(13,20,40,.6);border-left:3px solid rgba(248,113,113,.55)}
.issue-num{color:#8ba3c7;font-size:.72rem;font-weight:600;min-width:20px;padding-top:1px}
.issue-text{color:#e2e8f0;font-size:.88rem;line-height:1.45}

.ticket-row{display:flex;align-items:center;justify-content:space-between;padding:11px 16px;border-radius:8px;background:rgba(13,20,40,.7);border:1px solid rgba(99,179,237,.12);margin-bottom:8px}
.ticket-key{color:#60a5fa;font-weight:700;font-size:.9rem;text-decoration:none}
.t-live{color:#4ade80;font-size:.74rem;font-weight:600}
.t-mock{color:#94a3b8;font-size:.74rem}
.notif-row{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:8px;background:rgba(13,20,40,.7);border:1px solid rgba(74,222,128,.2);margin-bottom:8px;color:#bbf7d0;font-size:.85rem}
.chip{display:inline-block;background:rgba(99,179,237,.08);border:1px solid rgba(99,179,237,.18);border-radius:20px;padding:3px 12px;font-size:.72rem;color:#93c5fd;font-weight:500}
[data-testid="stFileUploader"]{background:rgba(13,20,40,.6)!important;border:1px dashed rgba(99,179,237,.25)!important;border-radius:10px!important}
</style>
""", unsafe_allow_html=True)

# ── Navigation ────────────────────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/home.py",            title="Home",       icon="🏠", default=True),
    st.Page("pages/1_📊_Analytics.py",  title="Analytics",  icon="📊"),
    st.Page("pages/2_🔬_RAG_Tuning.py", title="RAG Tuning", icon="🔬"),
])
pg.run()
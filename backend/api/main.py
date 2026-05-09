import os
import uuid
import asyncio
from functools import partial
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from langchain_openrouter import ChatOpenRouter
from langchain_core.tracers.langchain import LangChainTracer

from crewops.agents import (
    configure_llms,
    notification_node,
    jira_node,
)

from crewops.graph import build_graph


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="CrewOps API",
    version="1.0.0",
)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class AnalyzeRequest(BaseModel):
    raw_logs: str

    fast_model: str = "openai/gpt-4o-mini"
    smart_model: str = "openai/gpt-4o"

    jira_mock: bool = True
    notif_mock: bool = True

    source: Optional[str] = "api"


# =========================================================
# STARTUP
# =========================================================

GRAPH = None


@app.on_event("startup")
def startup_event():

    global GRAPH

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY not set")

    # -----------------------------------------------------
    # Configure LLMs
    # -----------------------------------------------------

    configure_llms(
        fast=ChatOpenRouter(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            max_tokens=2000,
        ),

        reasoning=ChatOpenRouter(
            model="openai/gpt-4o",
            temperature=0.2,
            max_tokens=4000,
        ),

        generation=ChatOpenRouter(
            model="openai/gpt-4o-mini",
            temperature=0.3,
            max_tokens=6000,
        ),
    )

    # -----------------------------------------------------
    # Configure integrations
    # -----------------------------------------------------

    configured_notification = partial(
        notification_node,
        mock_mode=os.environ.get(
            "NOTIFICATION_MOCK_MODE",
            "true"
        ).lower() == "true",

        n8n_webhook_url=os.environ.get(
            "N8N_WEBHOOK_URL",
            ""
        ),

        slack_webhook_url=os.environ.get(
            "SLACK_WEBHOOK_URL",
            ""
        ),
    )

    configured_jira = partial(
        jira_node,

        mock_mode=os.environ.get(
            "JIRA_MOCK_MODE",
            "true"
        ).lower() == "true",

        jira_server=os.environ.get(
            "JIRA_SERVER",
            ""
        ),

        jira_email=os.environ.get(
            "JIRA_EMAIL",
            ""
        ),

        jira_api_token=os.environ.get(
            "JIRA_API_TOKEN",
            ""
        ),

        jira_project_key=os.environ.get(
            "JIRA_PROJECT_KEY",
            "SCRUM"
        ),

        jira_epic_key=os.environ.get(
            "JIRA_EPIC_KEY",
            ""
        ),

        jira_sprint_name=os.environ.get(
            "JIRA_SPRINT_NAME",
            ""
        ),
    )

    # -----------------------------------------------------
    # Build graph
    # -----------------------------------------------------

    GRAPH = build_graph(
        notification_fn=configured_notification,
        jira_fn=configured_jira,
    )

    print("✅ CrewOps graph initialized")


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "crewops-api",
    }


# =========================================================
# ANALYZE ENDPOINT
# =========================================================

@app.post("/analyze")
async def analyze_logs(payload: AnalyzeRequest):

    global GRAPH

    if not payload.raw_logs.strip():
        raise HTTPException(
            status_code=400,
            detail="raw_logs cannot be empty",
        )

    tracer = LangChainTracer(
        project_name=os.environ.get(
            "LANGCHAIN_PROJECT",
            "CrewOps-Hackathon"
        )
    )

    # -----------------------------------------------------
    # Initial LangGraph state
    # -----------------------------------------------------

    initial_state = {
        "raw_logs": payload.raw_logs,

        "metadata": {
            "source": payload.source,
            "runner": "fastapi",
            "request_id": str(uuid.uuid4()),
        },

        "log_summary": "",
        "log_type": "",

        "severity": "",
        "severity_rationale": "",

        "approval_required": False,
        "approval_status": "pending",

        "critical_issues": [],

        "rag_context": [],
        "root_cause_analysis": "",

        "remediation_plan": "",

        "cookbook": "",

        "jira_tickets": [],
        "notifications_sent": [],

        "pipeline_status": {},

        "errors": [],
    }

    try:

        # Run graph in separate thread
        result = await asyncio.to_thread(
            GRAPH.invoke,
            initial_state,
            {
                "callbacks": [tracer],
                "run_name": f"CrewOps API | {payload.source}",
            }
        )

        return {
            "success": True,
            "result": result,
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
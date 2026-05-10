import os
import uuid
import asyncio
import json
from functools import partial
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_openrouter import ChatOpenRouter
from langchain_core.tracers.langchain import LangChainTracer

from crewops.agents import (
    configure_llms,
    classifier_node,
    severity_node,
    root_cause_node,
    remediation_node,
    cookbook_node,
    notification_node,
    jira_node,
)

from crewops.graph import build_graph

from api.tuning import router as tuning_router

# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="CrewOps API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(tuning_router)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class AnalyzeRequest(BaseModel):
    raw_logs: str

    fast_model: str = "openai/gpt-4o-mini"
    smart_model: str = "openai/gpt-4o"
    reasoning_model: Optional[str] = None
    generation_model: Optional[str] = None

    fast_temp: float = 0.1
    reasoning_temp: float = 0.2
    generation_temp: float = 0.3

    fast_max_tokens: int = 2000
    reasoning_max_tokens: int = 4000
    generation_max_tokens: int = 6000

    jira_mock: bool = True
    notif_mock: bool = True

    source: Optional[str] = "api"


# =========================================================
# STARTUP
# =========================================================

GRAPH = None


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default

    return raw.lower() in ("1", "true", "yes", "y", "on")


def _base_state(
    raw_logs: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "raw_logs": raw_logs,
        "metadata": metadata,
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


def _callbacks() -> list[Any]:
    if not os.environ.get("LANGCHAIN_API_KEY"):
        return []

    return [
        LangChainTracer(
            project_name=os.environ.get(
                "LANGCHAIN_PROJECT",
                "CrewOps-Hackathon",
            )
        )
    ]


def _chat_openrouter(
    model: str,
    temperature: float,
    max_tokens: int,
) -> ChatOpenRouter:
    if not model or not model.strip():
        raise HTTPException(status_code=400, detail="model names cannot be empty")

    return ChatOpenRouter(
        model=model.strip(),
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _llms_from_request(payload: AnalyzeRequest) -> dict[str, ChatOpenRouter]:
    reasoning_model = payload.reasoning_model or payload.smart_model
    generation_model = payload.generation_model or payload.fast_model

    return {
        "fast": _chat_openrouter(
            model=payload.fast_model,
            temperature=payload.fast_temp,
            max_tokens=payload.fast_max_tokens,
        ),
        "reasoning": _chat_openrouter(
            model=reasoning_model,
            temperature=payload.reasoning_temp,
            max_tokens=payload.reasoning_max_tokens,
        ),
        "generation": _chat_openrouter(
            model=generation_model,
            temperature=payload.generation_temp,
            max_tokens=payload.generation_max_tokens,
        ),
    }


def _build_request_graph(payload: AnalyzeRequest):
    llms = _llms_from_request(payload)

    return build_graph(
        classifier_fn=partial(classifier_node, llm=llms["fast"]),
        severity_fn=partial(severity_node, llm=llms["fast"]),
        root_cause_fn=partial(root_cause_node, llm=llms["reasoning"]),
        remediation_fn=partial(remediation_node, llm=llms["reasoning"]),
        cookbook_fn=partial(cookbook_node, llm=llms["generation"]),
        notification_fn=_configured_notification(payload.notif_mock),
        jira_fn=_configured_jira(payload.jira_mock),
    )


def _configured_notification(mock_mode: bool):
    return partial(
        notification_node,
        mock_mode=mock_mode,
        n8n_webhook_url=os.environ.get("N8N_WEBHOOK_URL", ""),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL", ""),
    )


def _configured_jira(mock_mode: bool):
    return partial(
        jira_node,
        mock_mode=mock_mode,
        jira_server=os.environ.get("JIRA_SERVER", ""),
        jira_email=os.environ.get("JIRA_EMAIL", ""),
        jira_api_token=os.environ.get("JIRA_API_TOKEN", ""),
        jira_project_key=os.environ.get("JIRA_PROJECT_KEY", "SCRUM"),
        jira_epic_key=os.environ.get("JIRA_EPIC_KEY", ""),
        jira_sprint_name=os.environ.get("JIRA_SPRINT_NAME", ""),
    )


@app.on_event("startup")
def startup_event():

    global GRAPH

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set; pipeline routes will be unavailable")
        return

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

    # -----------------------------------------------------
    # Build graph
    # -----------------------------------------------------

    GRAPH = build_graph(
        notification_fn=_configured_notification(
            _env_bool("NOTIFICATION_MOCK_MODE", True)
        ),
        jira_fn=_configured_jira(
            _env_bool("JIRA_MOCK_MODE", True)
        ),
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
        "openrouter_configured": bool(os.environ.get("OPENROUTER_API_KEY")),
        "graph_initialized": GRAPH is not None,
    }


# =========================================================
# ANALYZE ENDPOINT
# =========================================================

@app.post("/analyze")
async def analyze_logs(payload: AnalyzeRequest):

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY not set",
        )

    if not payload.raw_logs.strip():
        raise HTTPException(
            status_code=400,
            detail="raw_logs cannot be empty",
        )

    request_graph = _build_request_graph(payload)
    reasoning_model = payload.reasoning_model or payload.smart_model
    generation_model = payload.generation_model or payload.fast_model

    # -----------------------------------------------------
    # Initial LangGraph state
    # -----------------------------------------------------

    initial_state = _base_state(
        raw_logs=payload.raw_logs,
        metadata={
            "source": payload.source,
            "runner": "fastapi",
            "request_id": str(uuid.uuid4()),
            "llm": {
                "fast_model": payload.fast_model,
                "reasoning_model": reasoning_model,
                "generation_model": generation_model,
            },
        },
    )

    async def event_generator():
        try:
            # We use stream() to get incremental updates
            # LangGraph stream yields dicts of {node_name: state_update}
            for update in request_graph.stream(
                initial_state,
                {
                    "callbacks": _callbacks(),
                    "run_name": (
                        f"CrewOps API | {payload.source} | "
                        f"{payload.fast_model} / {reasoning_model} / {generation_model}"
                    ),
                }
            ):
                # We yield the node that just finished and the current state update
                yield f"data: {json.dumps(update)}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"


    return StreamingResponse(event_generator(), media_type="text/event-stream")


ERROR_KEYWORDS = [

    # Generic
    "error",
    "exception",
    "fatal",
    "critical",
    "panic",
    "traceback",

    # HTTP
    "500",
    "502",
    "503",
    "504",

    # Kubernetes
    "crashloopbackoff",
    "oomkilled",
    "failed",
    "evicted",

    # Database
    "deadlock",
    "connection refused",
    "too many connections",

    # Infra
    "timeout",
    "unreachable",
    "segmentation fault",
]


def is_error_log(log_text: str) -> bool:

    if not log_text:
        return False

    text = log_text.lower()

    return any(
        keyword in text
        for keyword in ERROR_KEYWORDS
    )


@app.post("/webhook/logs")
async def webhook_logs(request: Request):

    global GRAPH

    if GRAPH is None:
        raise HTTPException(
            status_code=503,
            detail="CrewOps graph is not initialized. Check OPENROUTER_API_KEY.",
        )

    try:
        payload = await request.json()

    except Exception:
        payload = {
            "raw_logs": (await request.body()).decode()
        }

    raw_logs = (
        payload.get("raw_logs")
        or payload.get("logs")
        or payload.get("message")
        or ""
    )

    # =====================================================
    # FILTER
    # =====================================================

    if not is_error_log(raw_logs):

        return {
            "success": True,
            "pipeline_triggered": False,
            "message": "No error detected. Pipeline skipped.",
        }

    print("🚨 Error detected — running CrewOps pipeline")

    # =====================================================
    # INITIAL STATE
    # =====================================================

    initial_state = _base_state(
        raw_logs=raw_logs,
        metadata={
            "source": "webhook",
            "runner": "fastapi",
            "request_id": str(uuid.uuid4()),
        },
    )

    # =====================================================
    # RUN PIPELINE
    # =====================================================

    result = await asyncio.to_thread(
        GRAPH.invoke,
        initial_state,
        {"callbacks": _callbacks(), "run_name": "CrewOps Webhook"},
    )

    return {
        "success": True,
        "pipeline_triggered": True,
        "result": result
    }

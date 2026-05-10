import os
import uuid
import asyncio
import json
from functools import partial
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
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

from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                continue

manager = ConnectionManager()

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/webhook/logs")
async def receive_logs(request: Request):
    try:
        data = await request.json()
        # Expecting {"log": "..."} or raw string
        log_entry = data.get("log", str(data))
        
        # Broadcast to all WS clients
        await manager.broadcast({
            "timestamp": datetime.now().isoformat(),
            "content": log_entry,
            "id": str(uuid.uuid4())
        })
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

from datetime import datetime



from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    
    provider: str = "openrouter"
    api_key: Optional[str] = None
    base_url: Optional[str] = None



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

@app.get("/models/ollama")
async def get_ollama_models(base_url: str = "http://localhost:11434"):
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            # Try /api/tags first (standard)
            resp = await client.get(f"{base_url}/api/tags", timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                # Handle different Ollama versions
                models = data.get("models", [])
                if not models and "tags" in data:
                    models = data["tags"]
                return {"models": models}
            return {"models": []}
    except Exception as e:
        print(f"Ollama discovery error: {e}")
        return {"models": [], "error": str(e)}


@app.get("/health")
def health():

    # Dynamic connection checks
    connections = [
        {
            "name": "OpenRouter",
            "status": "green" if os.environ.get("OPENROUTER_API_KEY") else "red"
        },
        {
            "name": "LangSmith",
            "status": "green" if os.environ.get("LANGCHAIN_API_KEY") and os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true" else "red"
        },
        {
            "name": "JIRA",
            "status": "green" if os.environ.get("JIRA_API_TOKEN") and os.environ.get("JIRA_MOCK_MODE", "").lower() == "false" else "red"
        },
        {
            "name": "n8n",
            "status": "green" if os.environ.get("N8N_WEBHOOK_URL") and os.environ.get("NOTIFICATION_MOCK_MODE", "").lower() == "false" else "red"
        },
        {
            "name": "Slack",
            "status": "green" if os.environ.get("SLACK_WEBHOOK_URL") and os.environ.get("NOTIFICATION_MOCK_MODE", "").lower() == "false" else "red"
        }
    ]
    
    return {
        "status": "ok",
        "service": "crewops-api",
        "connections": connections
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
    # Configure LLMs for this request
    # -----------------------------------------------------
    
    provider = payload.provider.lower()
    api_key = payload.api_key or os.environ.get("OPENROUTER_API_KEY")
    base_url = payload.base_url

    def create_llm(model_name, temp, tokens):
        if provider == "ollama":
            return ChatOllama(
                model=model_name,
                base_url=base_url or "http://localhost:11434",
                temperature=temp,
            )
        elif provider == "openai":
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temp,
                max_tokens=tokens,
            )
        elif provider == "openrouter":
            return ChatOpenRouter(
                model=model_name,
                api_key=api_key,
                temperature=temp,
                max_tokens=tokens,
            )
        else:
            # Fallback to OpenRouter
            return ChatOpenRouter(
                model=model_name,
                api_key=api_key,
                temperature=temp,
                max_tokens=tokens,
            )

    # Note: This modifies global state in crewops.agents
    # Safe for local hackathon usage.
    configure_llms(
        fast=create_llm(payload.fast_model, 0.1, 2000),
        reasoning=create_llm(payload.smart_model, 0.2, 4000),
        generation=create_llm(payload.fast_model, 0.3, 6000),
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

    async def event_generator():
        try:
            # We use stream() to get incremental updates
            # LangGraph stream yields dicts of {node_name: state_update}
            for update in GRAPH.stream(
                initial_state,
                {
                    "callbacks": [tracer],
                    "run_name": f"CrewOps API | {payload.source}",
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

    initial_state = {
        "raw_logs": raw_logs,

        "metadata": {
            "source": "webhook",
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

    # =====================================================
    # RUN PIPELINE
    # =====================================================

    result = await asyncio.to_thread(
        GRAPH.invoke,
        initial_state,
    )

    return {
        "success": True,
        "pipeline_triggered": True,
        "result": result
    }

# api/tuning.py

import asyncio
import os
import re
import uuid
from functools import partial
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.tracers.langchain import LangChainTracer
from langchain_openrouter import ChatOpenRouter

from crewops.agents import (
    classifier_node,
    severity_node,
    root_cause_node,
    remediation_node,
    cookbook_node,
    notification_node,
    jira_node,
)
from crewops.graph import build_graph
from crewops.rag import search_knowledge_base

router = APIRouter(
    prefix="/tuning",
    tags=["Tuning"],
)

# -----------------------------------------------------------------------------
# AVAILABLE MODELS
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# PRESETS
# -----------------------------------------------------------------------------

PRESETS = {
    "balanced": {
        "fast_model": "openai/gpt-4o-mini",
        "reasoning_model": "openai/gpt-4o",
        "generation_model": "openai/gpt-4o-mini",
        "fast_temp": 0.05,
        "reasoning_temp": 0.15,
        "generation_temp": 0.25,
        "fast_max_tokens": 600,
        "reasoning_max_tokens": 1500,
        "generation_max_tokens": 1500,
        "rag_top_k": 4,
        "rag_similarity_threshold": 0.28,
        "rag_chunk_size": 768,
        "kb_fallback": True,
        "max_log_chars": 5000,
        "truncation_strategy": "Tail (last N chars)",
        "strip_timestamps": False,
        "deduplicate_lines": True,
        "p1p2_full_pipeline": True,
        "p1_threshold": 3,
        "notify_on_p3": False,
    }
}

DEFAULT_CONFIG = PRESETS["balanced"]

# -----------------------------------------------------------------------------
# PYDANTIC MODELS
# -----------------------------------------------------------------------------


class TuningConfig(BaseModel):
    fast_model: str = Field(
        default="openai/gpt-4o-mini",
        examples=["openai/gpt-4o-mini"],
    )

    reasoning_model: str = Field(
        default="openai/gpt-4o",
        examples=["openai/gpt-4o"],
    )

    generation_model: str = Field(
        default="openai/gpt-4o-mini",
        examples=["openai/gpt-4o-mini"],
    )

    fast_temp: float = Field(default=0.05, ge=0.0, le=1.0)
    reasoning_temp: float = Field(default=0.15, ge=0.0, le=1.0)
    generation_temp: float = Field(default=0.25, ge=0.0, le=1.0)

    fast_max_tokens: int = Field(default=600, ge=1)
    reasoning_max_tokens: int = Field(default=1500, ge=1)
    generation_max_tokens: int = Field(default=1500, ge=1)

    rag_top_k: int = Field(default=4, ge=1)
    rag_similarity_threshold: float = Field(
        default=0.28,
        ge=0.0,
        le=1.0,
    )

    rag_chunk_size: int = Field(default=768)

    kb_fallback: bool = True

    max_log_chars: int = Field(default=5000, ge=100)

    truncation_strategy: Literal[
        "Head (first N chars)",
        "Tail (last N chars)",
        "Head + Tail",
    ] = "Tail (last N chars)"

    strip_timestamps: bool = False
    deduplicate_lines: bool = True

    p1p2_full_pipeline: bool = True

    p1_threshold: int = Field(default=3, ge=1)

    notify_on_p3: bool = False


class RunPipelineRequest(BaseModel):
    log_text: str = Field(
        ...,
        min_length=1,
        examples=["ERROR database connection failed"],
    )

    config: TuningConfig


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------


def truncate_log(
    text: str,
    strategy: str,
    max_chars: int,
) -> str:

    if len(text) <= max_chars:
        return text

    if strategy == "Head (first N chars)":
        return text[:max_chars]

    if strategy == "Tail (last N chars)":
        return text[-max_chars:]

    if strategy == "Head + Tail":
        half = max_chars // 2

        return (
            text[:half]
            + "\n\n... TRUNCATED ...\n\n"
            + text[-half:]
        )

    return text[:max_chars]


def strip_log_timestamps(text: str) -> str:
    return re.sub(
        r"^\s*(?:\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?\s*|\[[^\]]*\]\s*)",
        "",
        text,
        flags=re.MULTILINE,
    )


def deduplicate_log_lines(text: str) -> str:
    seen = set()
    lines = []

    for line in text.splitlines():
        key = line.strip()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)

    return "\n".join(lines)


def preprocess_log(
    text: str,
    config: TuningConfig,
) -> str:
    processed = text

    if config.strip_timestamps:
        processed = strip_log_timestamps(processed)

    if config.deduplicate_lines:
        processed = deduplicate_log_lines(processed)

    return truncate_log(
        text=processed,
        strategy=config.truncation_strategy,
        max_chars=config.max_log_chars,
    )


def make_chat_model(
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


class TuningQueryEngine:
    def __init__(self, top_k: int, enabled: bool) -> None:
        self.top_k = top_k
        self.enabled = enabled

    def query(self, query: str) -> str:
        if not self.enabled:
            return "Knowledge base fallback disabled for this tuning run."

        return search_knowledge_base(
            query,
            top_k=self.top_k,
        )


def simulate_pipeline(
    log_text: str,
    config: TuningConfig,
) -> dict[str, Any]:

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not set",
        )

    processed_log = preprocess_log(log_text, config)

    try:
        fast_llm = make_chat_model(
            model=config.fast_model,
            temperature=config.fast_temp,
            max_tokens=config.fast_max_tokens,
        )
        reasoning_llm = make_chat_model(
            model=config.reasoning_model,
            temperature=config.reasoning_temp,
            max_tokens=config.reasoning_max_tokens,
        )
        generation_llm = make_chat_model(
            model=config.generation_model,
            temperature=config.generation_temp,
            max_tokens=config.generation_max_tokens,
        )
        query_engine = TuningQueryEngine(
            top_k=config.rag_top_k,
            enabled=config.kb_fallback,
        )

        graph = build_graph(
            classifier_fn=partial(classifier_node, llm=fast_llm),
            severity_fn=partial(severity_node, llm=fast_llm),
            root_cause_fn=partial(
                root_cause_node,
                llm=reasoning_llm,
                query_engine=query_engine,
            ),
            remediation_fn=partial(remediation_node, llm=reasoning_llm),
            cookbook_fn=partial(cookbook_node, llm=generation_llm),
            jira_fn=partial(jira_node, mock_mode=True),
            notification_fn=partial(notification_node, mock_mode=True),
        )

        initial_state = {
            "raw_logs": processed_log,
            "metadata": {
                "source": "tuning",
                "runner": "fastapi",
                "request_id": str(uuid.uuid4()),
                "tuning_config": config.model_dump(),
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

        invoke_config = {
            "run_name": (
                "CrewOps Tuning | "
                f"{config.fast_model} / {config.reasoning_model} / {config.generation_model}"
            ),
        }

        if os.environ.get("LANGCHAIN_API_KEY"):
            invoke_config["callbacks"] = [
                LangChainTracer(
                    project_name=os.environ.get(
                        "LANGCHAIN_PROJECT",
                        "CrewOps-Hackathon",
                    )
                )
            ]

        result = graph.invoke(initial_state, config=invoke_config)

        return {
            "status": "success",
            "config_used": config.model_dump(),
            "processed_log_preview": processed_log[:500],
            "processed_log_chars": len(processed_log),
            "log_type": result.get("log_type"),
            "severity": result.get("severity"),
            "summary": result.get("log_summary"),
            "issues": result.get("critical_issues", []),
            "root_cause_analysis": result.get("root_cause_analysis"),
            "recommendations": result.get("remediation_plan"),
            "cookbook": result.get("cookbook"),
            "kb_hits": len(result.get("rag_context", [])),
            "rag_context": result.get("rag_context", []),
            "jira_tickets": result.get("jira_tickets", []),
            "notifications_sent": result.get("notifications_sent", []),
            "pipeline_status": result.get("pipeline_status", {}),
            "errors": result.get("errors", []),
            "result": result,
        }

    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# -----------------------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------------------


@router.get("/models")
async def get_models():

    return {
        "models": AVAILABLE_MODELS,
    }


@router.get("/presets")
async def get_presets():

    return PRESETS


@router.get("/default-config")
async def get_default_config():

    return DEFAULT_CONFIG


@router.post("/validate-config")
async def validate_config(
    config: TuningConfig,
):

    return {
        "valid": True,
        "config": config.model_dump(),
    }


@router.post("/run")
async def run_pipeline(
    request: RunPipelineRequest,
):

    result = await asyncio.to_thread(
        simulate_pipeline,
        request.log_text,
        request.config,
    )

    return result

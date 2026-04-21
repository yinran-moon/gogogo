import json
import uuid
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import agent_graph, AgentState

logger = logging.getLogger(__name__)
router = APIRouter()

sessions: dict[str, AgentState] = {}


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    phase: str | None = None
    destination: str | None = None
    days: int | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    phase: str
    profile: dict | None = None
    itinerary: dict | None = None
    destination: str = ""


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id

    if session_id not in sessions:
        sessions[session_id] = AgentState(
            phase="profile_collecting",
            messages=[],
            profile={},
            destination="",
            days=3,
            itinerary={},
            last_response="",
            user_input="",
        )

    state = sessions[session_id]

    PHASE_ALIASES = {
        "profile": "profile_collecting",
        "profile_collecting": "profile_collecting",
        "inspiration": "inspiration",
        "planning": "planning",
        "companion": "companion",
        "review": "review",
    }
    if req.phase and req.phase != state["phase"]:
        state["phase"] = PHASE_ALIASES.get(req.phase, req.phase)

    if req.destination:
        state["destination"] = req.destination
    if req.days:
        state["days"] = req.days

    state["user_input"] = req.message

    result = await agent_graph.ainvoke(state)

    sessions[session_id] = result

    return ChatResponse(
        session_id=session_id,
        response=result["last_response"],
        phase=result["phase"],
        profile=result.get("profile"),
        itinerary=result.get("itinerary"),
        destination=result.get("destination", ""),
    )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE 流式响应（简化版：先完整生成再分块推送）"""
    response = await chat(req)

    async def event_generator():
        text = response.response
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield {
                "event": "message",
                "data": json.dumps({"content": chunk, "phase": response.phase}, ensure_ascii=False),
            }

        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "phase": response.phase,
                    "profile": response.profile,
                    "itinerary": response.itinerary,
                    "destination": response.destination,
                },
                ensure_ascii=False,
            ),
        }

    return EventSourceResponse(event_generator())


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        return {"error": "Session not found"}
    state = sessions[session_id]
    return {
        "session_id": session_id,
        "phase": state["phase"],
        "profile": state.get("profile"),
        "destination": state.get("destination", ""),
        "itinerary": state.get("itinerary"),
        "messages": state.get("messages", []),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "ok"}

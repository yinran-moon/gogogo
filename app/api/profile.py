from fastapi import APIRouter
from app.api.chat import sessions

router = APIRouter()


@router.get("/profile/{session_id}")
async def get_profile(session_id: str):
    if session_id not in sessions:
        return {"error": "Session not found"}
    return {"profile": sessions[session_id].get("profile", {})}

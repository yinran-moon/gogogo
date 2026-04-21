from fastapi import APIRouter
from app.api.chat import sessions

router = APIRouter()


@router.get("/trip/{session_id}")
async def get_trip(session_id: str):
    if session_id not in sessions:
        return {"error": "Session not found"}
    state = sessions[session_id]
    return {
        "destination": state.get("destination", ""),
        "itinerary": state.get("itinerary", {}),
        "days": state.get("days", 0),
    }

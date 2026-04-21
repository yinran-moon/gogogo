"""
LangGraph 主编排 Agent：管理全链路状态机。

状态流转：
  profile_collecting → inspiration → planning → companion → review
"""
import json
import re
import logging
from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END

from app.models.profile import TravelerProfile
from app.agents.profile_agent import run_profile_agent
from app.agents.inspiration_agent import run_inspiration_agent
from app.agents.planner_agent import run_planner_agent
from app.agents.companion_agent import run_companion_agent
from app.agents.review_agent import run_review_agent

logger = logging.getLogger(__name__)

Phase = Literal["profile_collecting", "inspiration", "planning", "companion", "review"]


class AgentState(TypedDict):
    phase: Phase
    messages: list[dict]
    profile: dict
    destination: str
    days: int
    itinerary: dict
    last_response: str
    user_input: str


def _profile_from_dict(d: dict) -> TravelerProfile:
    return TravelerProfile(**{k: v for k, v in d.items() if k in TravelerProfile.model_fields})


async def profile_node(state: AgentState) -> AgentState:
    profile = _profile_from_dict(state.get("profile", {}))
    history = state.get("messages", [])

    if state.get("user_input"):
        history = history + [{"role": "user", "content": state["user_input"]}]

    response_text, updated_profile = await run_profile_agent(history, profile)

    new_messages = history + [{"role": "assistant", "content": response_text}]

    return {
        **state,
        "messages": new_messages,
        "profile": updated_profile.model_dump(),
        "last_response": response_text,
        "phase": "profile_collecting",
    }


async def inspiration_node(state: AgentState) -> AgentState:
    profile = _profile_from_dict(state.get("profile", {}))
    user_input = state.get("user_input", "")

    response = await run_inspiration_agent(profile, user_feedback=user_input)

    new_messages = state.get("messages", [])
    if user_input:
        new_messages = new_messages + [{"role": "user", "content": user_input}]
    new_messages = new_messages + [{"role": "assistant", "content": response}]

    dest_match = re.search(r'"destination"\s*:\s*"([^"]+)"', response)
    destination = dest_match.group(1) if dest_match else state.get("destination", "")

    return {
        **state,
        "messages": new_messages,
        "last_response": response,
        "destination": destination,
        "phase": "inspiration",
    }


async def planning_node(state: AgentState) -> AgentState:
    profile = _profile_from_dict(state.get("profile", {}))
    destination = state.get("destination", "成都")
    days = state.get("days", 3)
    user_input = state.get("user_input", "")
    existing_plan = state.get("itinerary") if state.get("itinerary") else None

    response = await run_planner_agent(
        profile=profile,
        destination=destination,
        days=days,
        user_request=user_input,
        existing_plan=existing_plan,
    )

    itinerary_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    itinerary = {}
    if itinerary_match:
        try:
            itinerary = json.loads(itinerary_match.group(1))
        except json.JSONDecodeError:
            pass

    new_messages = state.get("messages", [])
    if user_input:
        new_messages = new_messages + [{"role": "user", "content": user_input}]
    new_messages = new_messages + [{"role": "assistant", "content": response}]

    return {
        **state,
        "messages": new_messages,
        "last_response": response,
        "itinerary": itinerary if itinerary else state.get("itinerary", {}),
        "phase": "planning",
    }


async def companion_node(state: AgentState) -> AgentState:
    destination = state.get("destination", "成都")
    user_input = state.get("user_input", "")
    itinerary = state.get("itinerary")

    response = await run_companion_agent(
        user_message=user_input,
        city=destination,
        current_itinerary=itinerary,
    )

    new_messages = state.get("messages", [])
    if user_input:
        new_messages = new_messages + [{"role": "user", "content": user_input}]
    new_messages = new_messages + [{"role": "assistant", "content": response}]

    return {
        **state,
        "messages": new_messages,
        "last_response": response,
        "phase": "companion",
    }


async def review_node(state: AgentState) -> AgentState:
    itinerary = state.get("itinerary", {})
    user_input = state.get("user_input", "")

    style = "xiaohongshu"
    for s in ["朋友圈", "moments"]:
        if s in user_input:
            style = "moments"
            break
    for s in ["vlog", "视频"]:
        if s in user_input:
            style = "vlog"
            break
    for s in ["消费", "花费", "预算", "复盘"]:
        if s in user_input:
            style = "budget"
            break

    response = await run_review_agent(
        itinerary=itinerary,
        user_feelings=user_input,
        style=style,
    )

    new_messages = state.get("messages", [])
    if user_input:
        new_messages = new_messages + [{"role": "user", "content": user_input}]
    new_messages = new_messages + [{"role": "assistant", "content": response}]

    return {
        **state,
        "messages": new_messages,
        "last_response": response,
        "phase": "review",
    }


def should_advance_from_profile(state: AgentState) -> str:
    profile = state.get("profile", {})
    if profile.get("is_complete") in (True, "true", "True"):
        return "inspiration"
    return "end"


def route_by_phase(state: AgentState) -> str:
    return state.get("phase", "profile_collecting")


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("profile_collecting", profile_node)
    graph.add_node("inspiration", inspiration_node)
    graph.add_node("planning", planning_node)
    graph.add_node("companion", companion_node)
    graph.add_node("review", review_node)

    graph.set_conditional_entry_point(route_by_phase, {
        "profile_collecting": "profile_collecting",
        "inspiration": "inspiration",
        "planning": "planning",
        "companion": "companion",
        "review": "review",
    })

    graph.add_conditional_edges("profile_collecting", should_advance_from_profile, {
        "inspiration": "inspiration",
        "end": END,
    })
    graph.add_edge("inspiration", END)
    graph.add_edge("planning", END)
    graph.add_edge("companion", END)
    graph.add_edge("review", END)

    return graph.compile()


agent_graph = build_graph()

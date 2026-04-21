import json
import re
import logging
from pathlib import Path

from app.services.llm_router import chat_completion
from app.models.profile import TravelerProfile

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "profile_system.md").read_text(encoding="utf-8")


def _extract_profile_json(text: str) -> dict | None:
    pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("Failed to parse profile JSON from response")
    return None


def _strip_json_block(text: str) -> str:
    return re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL).strip()


async def run_profile_agent(
    conversation_history: list[dict],
    current_profile: TravelerProfile | None = None,
) -> tuple[str, TravelerProfile]:
    """
    运行画像构建 Agent。
    返回 (助手回复文本, 更新后的画像)。
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if current_profile and current_profile.travel_style:
        profile_context = f"\n\n当前已采集到的用户画像：\n```json\n{current_profile.model_dump_json(indent=2)}\n```\n请基于此继续采集未完成的维度。"
        messages[0]["content"] += profile_context

    messages.extend(conversation_history)

    response = await chat_completion(messages, task="profile", temperature=0.7)

    profile_data = _extract_profile_json(response)
    display_text = _strip_json_block(response)

    if profile_data:
        updated = TravelerProfile(**{
            **(current_profile.model_dump() if current_profile else {}),
            **{k: v for k, v in profile_data.items() if v},
        })
    else:
        updated = current_profile or TravelerProfile()

    return display_text, updated

import json
import logging
from pathlib import Path

from app.services.llm_router import chat_completion
from app.services.knowledge_service import knowledge_service
from app.services.weather import get_weather

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "companion_system.md").read_text(encoding="utf-8")


async def run_companion_agent(
    user_message: str,
    city: str,
    current_itinerary: dict | None = None,
    conversation_history: list[dict] | None = None,
) -> str:
    """实时陪跑 Agent：基于 RAG 检索 + 天气数据提供实时建议。"""
    context = knowledge_service.get_context(
        f"{city} {user_message}",
        city=city,
        top_k=5,
    )

    weather = await get_weather(city)
    weather_str = json.dumps(weather, ensure_ascii=False) if weather else "天气数据暂不可用"

    full_prompt = f"""{SYSTEM_PROMPT}

## 当前城市: {city}

## 实时天气
{weather_str}

## 参考资料（来自知识库检索）
{context}"""

    if current_itinerary:
        full_prompt += f"\n\n## 用户当前行程\n{json.dumps(current_itinerary, ensure_ascii=False, indent=2)}"

    messages = [{"role": "system", "content": full_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_message})

    response = await chat_completion(messages, task="companion", temperature=0.7)
    return response

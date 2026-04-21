import json
import logging
from pathlib import Path

from app.services.llm_router import chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "review_system.md").read_text(encoding="utf-8")

STYLE_PROMPTS = {
    "moments": "请生成朋友圈文案风格的旅行总结",
    "xiaohongshu": "请生成小红书笔记风格的旅行总结",
    "vlog": "请生成 Vlog 脚本风格的旅行总结",
    "budget": "请生成消费复盘报告",
}


async def run_review_agent(
    itinerary: dict,
    user_feelings: str = "",
    style: str = "xiaohongshu",
    conversation_history: list[dict] | None = None,
) -> str:
    """旅后复盘 Agent：基于行程数据和用户感受生成不同风格的内容。"""
    style_instruction = STYLE_PROMPTS.get(style, STYLE_PROMPTS["xiaohongshu"])

    full_prompt = f"""{SYSTEM_PROMPT}

## 行程数据
{json.dumps(itinerary, ensure_ascii=False, indent=2)}"""

    messages = [{"role": "system", "content": full_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    user_msg = style_instruction
    if user_feelings:
        user_msg += f"\n\n我的旅行感受：{user_feelings}"

    messages.append({"role": "user", "content": user_msg})

    response = await chat_completion(messages, task="review", temperature=0.8)
    return response

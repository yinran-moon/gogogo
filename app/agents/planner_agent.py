import json
import logging
from pathlib import Path

from app.services.llm_router import chat_completion
from app.services.knowledge_service import knowledge_service
from app.models.profile import TravelerProfile
from app.models.trip import TripPlan

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "planner_system.md").read_text(encoding="utf-8")


async def run_planner_agent(
    profile: TravelerProfile,
    destination: str,
    days: int = 3,
    user_request: str = "",
    existing_plan: dict | None = None,
    conversation_history: list[dict] | None = None,
) -> str:
    """基于 RAG 检索 POI 数据 + 用户画像，生成/调整行程。"""
    queries = [
        f"{destination} 景点推荐 {' '.join(profile.interests)}",
        f"{destination} 美食推荐 特色小吃",
        f"{destination} 交通攻略 地铁公交",
        f"{destination} 避坑指南 注意事项",
    ]

    all_context = []
    for q in queries:
        docs = knowledge_service.retrieve(q, city=destination, top_k=3)
        all_context.extend(docs)

    context = "\n\n---\n\n".join(list(dict.fromkeys(all_context)))

    user_profile_str = f"""## 用户画像
- 出行风格: {profile.travel_style}
- 预算: {profile.budget_level}
- 同行人: {profile.companions}
- 体力: {profile.physical_level}
- 兴趣: {', '.join(profile.interests)}
- 特殊约束: {json.dumps(profile.constraints, ensure_ascii=False)}
- 出行时间: {json.dumps(profile.travel_dates, ensure_ascii=False)}"""

    full_prompt = f"""{SYSTEM_PROMPT}

{user_profile_str}

## 目的地: {destination}
## 行程天数: {days}天

## 参考资料（来自知识库检索）
{context}"""

    if existing_plan:
        full_prompt += f"\n\n## 当前行程（用户要求调整）\n```json\n{json.dumps(existing_plan, ensure_ascii=False, indent=2)}\n```"

    messages = [{"role": "system", "content": full_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    if user_request:
        messages.append({"role": "user", "content": user_request})
    else:
        messages.append({"role": "user", "content": f"请为我规划一份{destination}{days}天的详细行程"})

    response = await chat_completion(messages, task="planning", temperature=0.6, max_tokens=6000)
    return response

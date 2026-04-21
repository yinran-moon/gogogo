import json
import re
import logging

from app.services.llm_router import chat_completion
from app.services.knowledge_service import knowledge_service
from app.models.profile import TravelerProfile

logger = logging.getLogger(__name__)


def _build_query_from_profile(profile: TravelerProfile) -> str:
    parts = []
    if profile.destination_pref:
        parts.append(f"目的地偏好: {json.dumps(profile.destination_pref, ensure_ascii=False)}")
    if profile.interests:
        parts.append(f"兴趣: {', '.join(profile.interests)}")
    if profile.travel_style:
        parts.append(f"风格: {profile.travel_style}")
    if profile.budget_level:
        parts.append(f"预算: {profile.budget_level}")
    if profile.companions:
        parts.append(f"同行: {profile.companions}")
    return " ".join(parts) if parts else "热门旅行目的地推荐"


def _extract_city(profile: TravelerProfile) -> str | None:
    dest = profile.destination_pref
    if isinstance(dest, dict):
        for key in ["city", "destination", "region"]:
            if key in dest and dest[key]:
                return dest[key]
    return None


async def run_inspiration_agent(
    profile: TravelerProfile,
    user_feedback: str = "",
    conversation_history: list[dict] | None = None,
) -> str:
    """基于画像 + RAG 检索，推荐目的地灵感。"""
    query = _build_query_from_profile(profile)
    city = _extract_city(profile)

    context = knowledge_service.get_context(query, city=city, top_k=8)

    system_prompt = f"""你是一位创意旅行灵感推荐师。根据用户画像和参考资料，推荐最匹配的旅行目的地和玩法。

## 用户画像
{profile.model_dump_json(indent=2, exclude={"is_complete"})}

## 参考资料（来自知识库检索）
{context}

## 输出要求
推荐 2-3 个目的地/玩法方案，每个方案包含：
1. 目的地名称和核心亮点（1-2句话）
2. 最佳出行时间
3. 预估费用区间
4. 匹配度评分（1-5星）
5. 推荐理由（结合用户画像说明为何匹配）

用 ```json 包裹结构化数据：
```json
{{
  "recommendations": [
    {{
      "destination": "目的地",
      "highlights": "核心亮点",
      "best_time": "最佳时间",
      "budget_range": "费用区间",
      "match_score": 5,
      "reason": "推荐理由"
    }}
  ]
}}
```

在 JSON 之前，用生动自然的语言介绍这些推荐，让用户产生向往感。"""

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    if user_feedback:
        messages.append({"role": "user", "content": user_feedback})
    else:
        messages.append({"role": "user", "content": "请根据我的画像推荐适合我的旅行目的地和玩法"})

    response = await chat_completion(messages, task="inspiration", temperature=0.8)
    return response

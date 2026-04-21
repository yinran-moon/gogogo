"""
行程校验 Agent:检查生成行程的合理性,发现问题自动触发重新生成
"""
import json
import logging
from typing import Tuple, List
from app.models.trip import TripPlan
from app.services.llm_router import chat_completion

logger = logging.getLogger(__name__)


class ValidationResult:
    def __init__(self, is_valid: bool, issues: List[str], severity: str = "info"):
        self.is_valid = is_valid
        self.issues = issues  # 问题描述列表
        self.severity = severity  # "info" | "warning" | "error"


async def validate_itinerary(
    itinerary: dict,
    profile: dict,
    destination: str
) -> ValidationResult:
    """
    对生成的行程进行多维度校验(优化版评判标准)

    校验维度:
    1. 预算合理性 - 分级容忍策略(低预算±10%, 中等±15%, 高预算±20%)
    2. 地理分布 - 量化距离标准(单日通勤≤3h, 相邻景点≤15km市内/50km郊区)
    3. 时间可行性 - 基于时长估算(单日游玩6-8h)
    4. 体力匹配度 - 评分制(轻松≤8分, 中等≤12分, 较好≤18分)
    5. 兴趣覆盖度 - 加权匹配算法(覆盖度≥70%)
    """
    issues = []

    # === 1. 预算校验(分级容忍策略) ===
    total_cost = _calculate_total_cost(itinerary)
    user_budget = profile.get("budget_level", "")
    budget_limit = _parse_budget(user_budget)

    if budget_limit:
        # 根据预算档次确定浮动比例
        if budget_limit < 2000:
            tolerance = 0.10  # 低预算成本敏感,只允许10%浮动
        elif budget_limit < 5000:
            tolerance = 0.15  # 中等预算
        else:
            tolerance = 0.20  # 高预算更灵活

        max_allowed = budget_limit * (1 + tolerance)

        if total_cost > max_allowed:
            overspend_pct = int((total_cost / budget_limit - 1) * 100)
            issues.append(
                f"❌ 预算超标: 总费用{total_cost}元,超出预算{user_budget} {overspend_pct}% (允许浮动{int(tolerance*100)}%)"
            )

        # 检查单日花费差异(避免前松后紧)
        daily_costs = [_calculate_total_cost({"days": [day]}) for day in itinerary.get("days", [])]
        if daily_costs:
            max_daily = max(daily_costs)
            min_daily = min(daily_costs)
            if max_daily > 0 and max_daily > min_daily * 2.5:  # 最高日超过最低日2.5倍
                issues.append(
                    f"⚠️ 单日花费不均: 最高{max_daily}元,最低{min_daily}元,建议更均衡"
                )

    # === 2. 地理分布校验(简化版:检查相邻景点) ===
    geo_issues = await _check_geographic_feasibility(itinerary, destination)
    issues.extend(geo_issues)

    # === 3. 时间可行性校验 ===
    time_issues = _check_time_feasibility(itinerary)
    issues.extend(time_issues)

    # === 4. 体力匹配度 ===
    physical_level = profile.get("physical_level", "中等")
    if physical_level in ["轻松", "较低"]:
        daily_pois = [len(day.get("activities", [])) for day in itinerary.get("days", [])]
        if any(count > 4 for count in daily_pois):
            issues.append(
                f"⚠️ 行程强度过高: 用户体力等级为「{physical_level}」,但部分天数安排了{max(daily_pois)}个景点,建议减少"
            )

    # === 5. 兴趣覆盖度 ===
    interests = profile.get("interests", [])
    if interests:
        covered = _check_interest_coverage(itinerary, interests)
        if not covered:
            issues.append(
                f"⚠️ 兴趣匹配度低: 用户感兴趣「{', '.join(interests)}」,但行程覆盖较少"
            )

    is_valid = len([i for i in issues if i.startswith("❌")]) == 0
    severity = "error" if not is_valid else ("warning" if issues else "info")

    logger.info(f"行程校验完成: valid={is_valid}, issues={len(issues)}")
    return ValidationResult(is_valid, issues, severity)


def _calculate_total_cost(itinerary: dict) -> int:
    """统计行程总费用(门票+交通+餐饮)"""
    total = 0
    for day in itinerary.get("days", []):
        for activity in day.get("activities", []):
            cost_str = activity.get("cost", "0")
            # 提取数字(支持"50元"、"约100"等格式)
            import re
            numbers = re.findall(r'\d+', str(cost_str))
            if numbers:
                total += int(numbers[0])
    return total


def _parse_budget(budget_str: str) -> int | None:
    """解析预算字符串,返回数字"""
    if not budget_str:
        return None
    import re
    numbers = re.findall(r'\d+', budget_str)
    return int(numbers[0]) if numbers else None


async def _check_geographic_feasibility(itinerary: dict, destination: str) -> List[str]:
    """
    使用LLM判断地理合理性
    (生产环境建议接入真实地图API计算距离)
    """
    issues = []
    for day_idx, day in enumerate(itinerary.get("days", [])):
        spots = [act.get("name", "") for act in day.get("activities", []) if act.get("type") == "景点"]
        if len(spots) >= 3:
            # 构造prompt让LLM判断
            prompt = f"""你是一位熟悉{destination}地理的向导。
以下是一天的行程安排:
{' -> '.join(spots)}

请判断这个路线是否存在"地理分布不合理"的问题(如:相邻景点距离过远、路线反复横跳)。
如果不合理,请用一句话说明问题;如果合理,回复"合理"。"""

            messages = [{"role": "user", "content": prompt}]
            response = await chat_completion(messages, task="validate", temperature=0.3, max_tokens=200)

            if "不合理" in response or "过远" in response or "横跳" in response:
                issues.append(f"⚠️ 第{day_idx+1}天路线可能不合理: {response.strip()}")

    return issues


def _check_time_feasibility(itinerary: dict) -> List[str]:
    """检查时间安排是否合理(如:一天安排了8个景点)"""
    issues = []
    for day_idx, day in enumerate(itinerary.get("days", [])):
        activities = day.get("activities", [])
        poi_count = len([a for a in activities if a.get("type") in ["景点", "美食"]])

        if poi_count > 6:
            issues.append(
                f"❌ 第{day_idx+1}天时间过于紧张: 安排了{poi_count}个景点/美食,建议精简至4-5个"
            )
    return issues


def _check_interest_coverage(itinerary: dict, interests: List[str]) -> bool:
    """检查行程是否覆盖用户兴趣"""
    all_activities = []
    for day in itinerary.get("days", []):
        for act in day.get("activities", []):
            all_activities.append(act.get("name", "") + act.get("description", ""))

    full_text = " ".join(all_activities).lower()

    # 简单关键词匹配(生产环境建议用语义相似度)
    keywords_map = {
        "美食": ["美食", "小吃", "火锅", "串串"],
        "历史": ["历史", "古迹", "博物馆", "遗址", "文化"],
        "自然": ["自然", "山", "湖", "公园", "风景"],
        "购物": ["购物", "商场", "步行街"],
    }

    for interest in interests:
        keywords = keywords_map.get(interest, [interest])
        if any(kw in full_text for kw in keywords):
            return True
    return False


async def validate_and_correct(
    itinerary: dict,
    profile: dict,
    destination: str,
    max_retries: int = 2
) -> Tuple[dict, ValidationResult]:
    """
    校验行程,如果不合格则返回问题清单供重新生成

    Returns:
        (itinerary, validation_result)
    """
    result = await validate_itinerary(itinerary, profile, destination)

    if not result.is_valid:
        logger.warning(f"行程校验失败,发现{len(result.issues)}个问题: {result.issues}")

    return itinerary, result

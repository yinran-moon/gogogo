import httpx
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_route_info(origin: str, destination: str) -> dict | None:
    """高德地图路径规划（驾车/公交），返回预估时长和距离"""
    if not settings.amap_api_key:
        return _mock_route(origin, destination)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://restapi.amap.com/v3/direction/transit/integrated",
                params={
                    "origin": origin,
                    "destination": destination,
                    "city": "成都",
                    "key": settings.amap_api_key,
                },
                timeout=5.0,
            )
            data = resp.json()
            if data.get("status") == "1":
                route = data.get("route", {})
                return {
                    "origin": origin,
                    "destination": destination,
                    "distance": route.get("distance", "未知"),
                    "duration": f"约{int(route.get('transits', [{}])[0].get('duration', 0)) // 60}分钟",
                }
    except Exception as e:
        logger.warning(f"AMap API failed: {e}")

    return _mock_route(origin, destination)


def _mock_route(origin: str, destination: str) -> dict:
    return {
        "origin": origin,
        "destination": destination,
        "distance": "未知",
        "duration": "约30-60分钟",
        "note": "路线数据为模拟，请配置高德地图 API key",
    }

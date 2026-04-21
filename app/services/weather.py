import httpx
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CITY_LOCATION_MAP = {
    "成都": "101270101",
    "西安": "101110101",
    "北京": "101010100",
    "上海": "101020100",
    "重庆": "101040100",
    "广州": "101280101",
    "杭州": "101210101",
}


async def get_weather(city: str) -> dict | None:
    if not settings.weather_api_key:
        return _mock_weather(city)

    location = CITY_LOCATION_MAP.get(city)
    if not location:
        return _mock_weather(city)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.weather_base_url}/weather/3d",
                params={"location": location, "key": settings.weather_api_key},
                timeout=5.0,
            )
            data = resp.json()
            if data.get("code") == "200" and data.get("daily"):
                day = data["daily"][0]
                return {
                    "city": city,
                    "date": day["fxDate"],
                    "text_day": day["textDay"],
                    "temp_min": day["tempMin"],
                    "temp_max": day["tempMax"],
                    "humidity": day.get("humidity", ""),
                }
    except Exception as e:
        logger.warning(f"Weather API failed: {e}")

    return _mock_weather(city)


def _mock_weather(city: str) -> dict:
    return {
        "city": city,
        "date": "today",
        "text_day": "晴",
        "temp_min": "15",
        "temp_max": "25",
        "humidity": "50",
        "note": "天气数据为模拟数据，请配置和风天气 API key 获取实时天气",
    }

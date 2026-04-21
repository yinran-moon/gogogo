from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "GoGoGo"
    debug: bool = True

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    default_llm_model: str = "deepseek/deepseek-chat"
    review_llm_model: str = "openai/qwen-plus"

    embedding_model_name: str = "shibing624/text2vec-base-chinese"

    chroma_persist_dir: str = "data/chroma_db"
    knowledge_dir: str = "data/knowledge"

    sqlite_url: str = "sqlite+aiosqlite:///data/gogogo.db"

    weather_api_key: str = ""
    weather_base_url: str = "https://devapi.qweather.com/v7"

    amap_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

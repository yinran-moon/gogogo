import litellm
from app.core.config import get_settings

settings = get_settings()

MODEL_ROUTING = {
    "profile": "openai/qwen-plus",
    "inspiration": "openai/qwen-plus",
    "planning": "openai/qwen-plus",
    "companion": "openai/qwen-plus",
    "review": "openai/qwen-plus",
    "validate": "openai/qwen-plus",
    "fallback": "openai/qwen-plus",
}

litellm.set_verbose = False


def _get_api_params(model: str) -> dict:
    if settings.deepseek_api_key and model.startswith("deepseek/"):
        return {"api_key": settings.deepseek_api_key, "api_base": settings.deepseek_base_url}
    return {"api_key": settings.qwen_api_key, "api_base": settings.qwen_base_url}


async def chat_completion(
    messages: list[dict],
    task: str = "fallback",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = False,
) -> str | litellm.CustomStreamWrapper:
    model = MODEL_ROUTING.get(task, MODEL_ROUTING["fallback"])
    api_params = _get_api_params(model)

    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        **api_params,
    )

    if stream:
        return response

    return response.choices[0].message.content


async def chat_completion_stream(
    messages: list[dict],
    task: str = "fallback",
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    model = MODEL_ROUTING.get(task, MODEL_ROUTING["fallback"])
    api_params = _get_api_params(model)

    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        **api_params,
    )

    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content

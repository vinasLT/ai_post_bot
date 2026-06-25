from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings


@lru_cache(maxsize=4)
def get_chat_openai(**kwargs) -> ChatOpenAI:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return ChatOpenAI(api_key=api_key, use_responses_api=True, **kwargs)


def get_lot_chooser_llm() -> ChatOpenAI:
    return get_chat_openai(model="gpt-5-mini", reasoning_effort="medium")


def get_image_processing_llm() -> ChatOpenAI:
    return get_chat_openai(model="gpt-4o", temperature=0)


def get_choose_final_lots_llm() -> ChatOpenAI:
    return get_chat_openai(model="gpt-5-mini", reasoning_effort="medium")

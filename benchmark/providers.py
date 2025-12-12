import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

def load_env():
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=dotenv_path)

load_env()


@dataclass
class UsageInfo:
    """Token usage and cost information from API response."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0


def chat(
    messages: List[Dict[str, Any]], model: str
) -> Tuple[str, Optional[str], UsageInfo]:
    logging.debug("calling model=%s", model)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY.")
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        extra_body={"usage": {"include": True}}
    )

    # Extract usage info from response
    usage_info = UsageInfo()
    if hasattr(response, 'usage') and response.usage:
        usage_info.prompt_tokens = getattr(response.usage, 'prompt_tokens', 0) or 0
        usage_info.completion_tokens = getattr(response.usage, 'completion_tokens', 0) or 0
        usage_info.total_tokens = getattr(response.usage, 'total_tokens', 0) or 0
        # Cost is in credits from OpenRouter
        if hasattr(response.usage, 'cost'):
            usage_info.cost = float(response.usage.cost) if response.usage.cost else 0.0

    return response.choices[0].message.content, None, usage_info
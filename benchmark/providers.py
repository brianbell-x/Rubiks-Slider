import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

def load_env():
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=dotenv_path)

load_env()

def chat(
    messages: List[Dict[str, Any]], model: str
) -> Tuple[str, Optional[str]]:
    logging.debug("calling model=%s", model)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY.")
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content, None
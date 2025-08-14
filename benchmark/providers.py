import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from dotenv import load_dotenv
import httpx

# Load environment variables from .env file
def load_env():
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=dotenv_path)

load_env()

# --- Provider Registry and Utilities ---

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self._providers[name.lower()] = func

    def get(self, name: str) -> Callable:
        key = name.lower()
        if key not in self._providers:
            raise RuntimeError(f"API Error: Unsupported LLM provider: {name}")
        return self._providers[key]

provider_registry = ProviderRegistry()

def get_response(
    messages: List[Dict[str, Any]],
    provider: str,
    model: str,
    model_config: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str]]:
    func = provider_registry.get(provider)
    return func(messages, model, model_config)

def chat(
    messages: List[Dict[str, Any]],
    provider: str,
    model: str,
    model_config: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str]]:
    return get_response(messages, provider, model, model_config)

# --- Provider Implementations ---

def call_gemini_api(
    messages: List[Dict[str, Any]], model: str, model_config: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[str]]:
    if not messages:
        raise RuntimeError("API Error (gemini): Input messages list is empty or None.")
    try:
        import google.generativeai as genai
        from google.generativeai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "API Error (gemini): API key not found. Set GEMINI_API_KEY environment variable."
            )

        genai.configure(api_key=api_key)
        logging.debug("calling gemini / model=%s", model)
        gemini_model = genai.GenerativeModel(model_name=model)

        gemini_messages = [
            {
                "role": "model" if msg.get("role", "user") == "assistant" else "user",
                "parts": [{"text": msg.get("content", "")}]
            }
            for msg in messages
        ]

        generation_config = types.GenerationConfig(temperature=1.0)

        response = gemini_model.generate_content(
            contents=gemini_messages,
            generation_config=generation_config,
        )

        logging.info(f"Gemini API Raw Response: {response}")

        reply_text, thinking_text = _parse_gemini_response(response)
        return reply_text, thinking_text

    except ImportError:
        raise RuntimeError(
            "API Error (gemini): Google Generative AI SDK not installed. Run 'pip install google-generativeai'."
        )
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}", exc_info=True)
        raise RuntimeError(f"API Error (gemini): {str(e)}")

def _parse_gemini_response(response) -> Tuple[Optional[str], Optional[str]]:
    thinking_texts = []
    reply_text = None
    try:
        if hasattr(response, "parts") and response.parts:
            if len(response.parts) == 1:
                reply_text = response.parts[0].text
            else:
                for i, part in enumerate(response.parts):
                    if i < len(response.parts) - 1:
                        thinking_texts.append(part.text)
                    else:
                        reply_text = part.text
        elif hasattr(response, "candidates") and response.candidates and response.candidates[0].content.parts:
            parts = response.candidates[0].content.parts
            if len(parts) == 1:
                reply_text = parts[0].text
            else:
                for i, part in enumerate(parts):
                    if i < len(parts) - 1:
                        thinking_texts.append(part.text)
                    else:
                        reply_text = part.text
        else:
            if (
                hasattr(response, "prompt_feedback")
                and response.prompt_feedback.block_reason
            ):
                raise RuntimeError(
                    f"API Error (gemini): Blocked - {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                )
            finish_reason = (
                response.candidates[0].finish_reason
                if hasattr(response, "candidates") and response.candidates
                else None
            )
            if finish_reason and getattr(finish_reason, "name", None) != "STOP":
                raise RuntimeError(
                    f"API Error (gemini): Finished with reason: {getattr(finish_reason, 'name', None)}"
                )
            raise RuntimeError(
                "API Error (gemini): Unexpected response format or empty content."
            )
    except (AttributeError, IndexError, TypeError) as e:
        logging.error(
            f"Error parsing Gemini response: {e}\nRaw Response: {response}"
        )
        raise RuntimeError(
            f"API Error (gemini): Failed to parse response - {str(e)}"
        )

    thinking_text = "\n".join(thinking_texts) if thinking_texts else None
    return reply_text, thinking_text

provider_registry.register("gemini", call_gemini_api)

def call_openai_api(
    messages: List[Dict[str, Any]], model: str, model_config: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[str]]:
    if not messages:
        raise RuntimeError("API Error (openai): Input messages list is empty or None.")
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "API Error (openai): API key not found. Set OPENAI_API_KEY environment variable."
            )

        client = OpenAI(api_key=api_key, http_client=httpx.Client(verify=False))
        api_messages = messages
        logging.debug("calling openai / model=%s", model)

        # Use Responses API if reasoning_effort is specified, else fallback to chat completions
        use_responses_api = model_config is not None and "reasoning_effort" in model_config
        if use_responses_api:
            return _call_openai_responses(client, api_messages, model, model_config)
        else:
            return _call_openai_chat(client, api_messages, model)

    except ImportError:
        raise RuntimeError(
            "API Error (openai): OpenAI SDK not installed. Run 'pip install openai'."
        )
    except Exception as e:
        raise RuntimeError(f"API Error (openai): {str(e)}")

def _call_openai_responses(client, messages, model, model_config):
    # Use the last user message as input for the responses API
    last_user_message = next(
        (msg.get("content", "") for msg in reversed(messages) if msg.get("role") == "user"),
        None
    )
    if last_user_message is None:
        raise RuntimeError("API Error (openai): No user message found for responses API input.")

    reasoning = {
        "effort": model_config["reasoning_effort"],
        "summary": "detailed"
    }
    try:
        response = client.responses.create(
            model=model,
            input=last_user_message,
            reasoning=reasoning,
        )
    except Exception as e:
        raise RuntimeError(f"API Error (openai): {str(e)}")
    logging.info(f"OpenAI API Raw Response: {response}")

    # Extract main reply and reasoning summary
    main_reply = None
    reasoning_summary = None
    for item in response.output:
        if hasattr(item, "type") and item.type == "message":
            content_list = getattr(item, "content", [])
            for c in content_list:
                if hasattr(c, "type") and c.type == "output_text":
                    main_reply = getattr(c, "text", None)
        elif hasattr(item, "type") and item.type == "reasoning":
            summary_arr = getattr(item, "summary", [])
            if summary_arr:
                reasoning_summary = "\n".join(
                    getattr(s, "text", "")
                    for s in summary_arr
                    if hasattr(s, "type") and s.type == "summary_text"
                )
    if not main_reply and hasattr(response, "text"):
        main_reply = response.text
    return main_reply, reasoning_summary

def _call_openai_chat(client, messages, model):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=1.0,
        )
    except Exception as e:
        raise RuntimeError(f"API Error (openai): {str(e)}")
    logging.info(f"OpenAI API Raw Response: {response}")

    return response.choices[0].message.content, None

provider_registry.register("openai", call_openai_api)

def call_anthropic_api(
    messages: List[Dict[str, Any]], model: str, model_config: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[str]]:
    if not messages:
        raise RuntimeError(
            "API Error (anthropic): Input messages list is empty or None."
        )
    try:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "API Error (anthropic): API key not found. Set ANTHROPIC_API_KEY environment variable."
            )

        client = anthropic.Anthropic(
            api_key=api_key, http_client=httpx.Client(verify=False, timeout=600)
        )

        anthropic_messages = [
            {"role": msg["role"], "content": [{"type": "text", "text": msg.get("content", "")}]}
            for msg in messages
        ]

        logging.debug("calling anthropic / model=%s", model)

        # Add thinking parameter for Sonnet
        thinking = {"type": "enabled", "budget_tokens": 32000} # Set thinking budget to half
        response = client.messages.create(
            model=model,
            messages=anthropic_messages,
            max_tokens=64000,
            temperature=1.0,
            thinking=thinking,
        )
        logging.info(f"Anthropic API Raw Response: {response}")

        reply_text, thinking_text = _parse_anthropic_response(response)
        return reply_text, thinking_text

    except ImportError:
        raise RuntimeError(
            "API Error (anthropic): Anthropic SDK not installed. Run 'pip install anthropic'."
        )
    except Exception as e:
        raise RuntimeError(f"API Error (anthropic): {str(e)}")

def _parse_anthropic_response(response) -> Tuple[Optional[str], Optional[str]]:
    thinking_texts = []
    reply_texts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "thinking":
            thinking_texts.append(getattr(block, "thinking", ""))
        elif block_type == "redacted_thinking":
            thinking_texts.append("[REDACTED THINKING]")
        elif block_type == "text":
            reply_texts.append(getattr(block, "text", ""))
    reply_text = "\n".join(reply_texts).strip() if reply_texts else None
    thinking_text = "\n".join(thinking_texts).strip() if thinking_texts else None
    return reply_text, thinking_text

provider_registry.register("anthropic", call_anthropic_api)

def call_openrouter_api(
    messages: List[Dict[str, Any]], model: str, model_config: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[str]]:
    logging.debug("calling openrouter / model=%s", model)

    if not messages:
        raise RuntimeError(
            "API Error (openrouter): Input messages list is empty or None."
        )
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "API Error (openrouter): API key not found. Set OPENROUTER_API_KEY environment variable."
            )

        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.Client(verify=False),
            timeout=120,
        )

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=16384
        )
        logging.info(f"OpenRouter API Raw Response: {response}")

        return response.choices[0].message.content, None

    except ImportError:
        raise RuntimeError(
            "API Error (openrouter): OpenAI SDK not installed. Run 'pip install openai'."
        )
    except Exception as e:
        raise RuntimeError(f"API Error (openrouter): {str(e)}")

provider_registry.register("openrouter", call_openrouter_api)

# --- Integration Test ---

def run_integration_tests():
    """
    Quick integration test for all providers.
    Usage:
        python -m benchmark.providers
    Requires:
        - .env file with all necessary API keys (OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY)
    """
    logging.basicConfig(level=logging.INFO, format='%(name)s:%(message)s')

    test_cases = [
        {
            "provider": "openrouter",
            "model": "openai/gpt-4.1",
        },
    ]

    test_messages = [
        {"role": "user", "content": "Explain the theory of relativity in simple terms."}
    ]

    print("=" * 60)
    print("benchmark.providers quick integration test")
    print("=" * 60)
    for case in test_cases:
        provider = case["provider"]
        model = case["model"]
        model_config = case.get("model_config")
        print(f"\n--- Testing provider: {provider} | model: {model} ---")
        try:
            reply, reasoning = get_response(
                test_messages, provider, model, model_config
            )
            print("Main reply:")
            print(f"  {repr(reply)}")
            print("Reasoning/Thoughts:")
            if reasoning:
                print(f"  {repr(reasoning)}")
            else:
                print("  (None)")
        except Exception as e:
            print(f"ERROR: {e}")
    print("\nAll tests complete.")

if __name__ == "__main__":
    run_integration_tests()

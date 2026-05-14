"""
AgenticOs — NVIDIA NIM smoke test
Quick smoke-test for the Nvidia NIM streaming API.
API key is loaded from .env (NVIDIA_API_KEY) or the environment.
"""

import os
import sys

# Load .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _env = os.path.join(_root, ".env")
    if os.path.exists(_env):
        with open(_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
_REASONING = "\033[90m" if _USE_COLOR else ""
_RESET = "\033[0m" if _USE_COLOR else ""

TEST_PROMPT = "Say hello and describe yourself in one sentence."


def _configured_model() -> str:
    env_model = os.environ.get("NVIDIA_NIM_MODEL", "").strip()
    if env_model:
        return env_model
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from core.runtime_config import load_config

        cfg = load_config()
        return (
            cfg.get("cloud", {})
            .get("nvidia", {})
            .get("model", "openai/gpt-oss-120b")
        )
    except Exception:
        return "openai/gpt-oss-120b"


def main() -> int:
    from openai import OpenAI

    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        print(
            "ERROR: NVIDIA_API_KEY not set. Add it to your .env file or environment.",
            file=sys.stderr,
        )
        return 1

    model = _configured_model()
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )

    print(f"Testing Nvidia NIM with model: {model}")
    print(f"Prompt: {TEST_PROMPT}\n{'-' * 50}")

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": TEST_PROMPT}],
            temperature=1,
            top_p=1,
            max_tokens=512,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": True,
                    "clear_thinking": False,
                }
            },
            stream=True,
        )

        for chunk in completion:
            if not getattr(chunk, "choices", None) or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                print(f"{_REASONING}{reasoning}{_RESET}", end="", flush=True)
            content = getattr(delta, "content", None)
            if content:
                print(content, end="", flush=True)

        print(f"\n{'-' * 50}\nTest complete.")
        return 0

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

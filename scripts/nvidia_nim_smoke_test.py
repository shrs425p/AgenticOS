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

from openai import OpenAI

API_KEY = os.environ.get("NVIDIA_API_KEY", "")
if not API_KEY:
    print(
        "ERROR: NVIDIA_API_KEY not set. Add it to your .env file or environment.",
        file=sys.stderr,
    )
    sys.exit(1)

_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
_REASONING = "\033[90m" if _USE_COLOR else ""
_RESET = "\033[0m" if _USE_COLOR else ""

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=API_KEY,
)

TEST_PROMPT = "Say hello and describe yourself in one sentence."

print("Testing Nvidia NIM with model: z-ai/glm4.7")
print(f"Prompt: {TEST_PROMPT}\n{'─' * 50}")

try:
    completion = client.chat.completions.create(
        model="z-ai/glm4.7",
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

    print(f"\n{'─' * 50}\nTest complete.")

except Exception as e:
    print(f"\nERROR: {e}", file=sys.stderr)
    sys.exit(1)

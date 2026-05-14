"""Model client adapters for Ollama and Nvidia NIM."""

import json
import os
import sys
import time
from collections import defaultdict, deque

import requests

from core.runtime_config import BASE_DIR
from core.runtime_ui import C, Spinner


try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


_RATE_LIMIT_HISTORY: dict[str, deque[float]] = defaultdict(deque)


def _get_nested(cfg: dict, path: str, default=None):
    current = cfg
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _configured_rpm(cfg: dict, provider: str, model: str) -> float:
    limits = cfg.get("rate_limits", {}) or {}
    model_key = f"{provider}:{model}"
    raw = (
        _get_nested(limits, f"models.{model_key}.rpm")
        or _get_nested(limits, f"providers.{provider}.rpm")
        or limits.get("default_rpm")
    )
    try:
        rpm = float(raw)
    except (TypeError, ValueError):
        return 0.0
    safety = limits.get("safety_factor", 1.0)
    try:
        rpm *= float(safety)
    except (TypeError, ValueError):
        pass
    return max(0.0, rpm)


def _wait_for_rate_limit(cfg: dict, provider: str, model: str) -> None:
    limits = cfg.get("rate_limits", {}) or {}
    if not limits.get("enabled", False):
        return
    rpm = _configured_rpm(cfg, provider, model)
    if rpm <= 0:
        return

    window = float(limits.get("window_seconds", 60))
    max_requests = max(1, int(rpm * window / 60))
    key = f"{provider}:{model}"
    history = _RATE_LIMIT_HISTORY[key]

    now = time.monotonic()
    while history and now - history[0] >= window:
        history.popleft()

    if len(history) >= max_requests:
        sleep_for = window - (now - history[0])
        if sleep_for > 0:
            print(
                f"\n{C.YELLOW}Rate limit pacing {key}: sleeping {sleep_for:.1f}s "
                f"({rpm:.1f} effective RPM).{C.RESET}"
            )
            time.sleep(sleep_for)
        now = time.monotonic()
        while history and now - history[0] >= window:
            history.popleft()

    history.append(time.monotonic())


def _unique_sorted_model_ids(model_ids) -> list:
    return sorted({model_id for model_id in model_ids if model_id})


class OllamaClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base_url = cfg["ollama"]["base_url"]
        self.model = cfg["ollama"]["default_model"]
        self.timeout = cfg["ollama"]["timeout"]
        self.temp = cfg["ollama"]["temperature"]
        self.ctx = cfg["ollama"]["num_ctx"]
        self.stream = cfg["agent"]["stream"]
        self.provider = "ollama"

    def list_models(self) -> list:
        self.last_list_error = ""
        try:
            list_timeout = self.cfg.get("timeouts", {}).get("list_models", 10)
            response = requests.get(f"{self.base_url}/api/tags", timeout=list_timeout)
            response.raise_for_status()
            return _unique_sorted_model_ids(
                model.get("name", "") for model in response.json().get("models", [])
            )
        except Exception as exc:
            self.last_list_error = f"{type(exc).__name__}: {exc}"
            return []

    def chat(self, messages: list, system: str = "") -> str:
        _wait_for_rate_limit(self.cfg, self.provider, self.model)
        full_messages = [{"role": "system", "content": system}] if system else []
        full_messages.extend(messages)
        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": self.stream,
            "options": {"temperature": self.temp, "num_ctx": self.ctx},
        }

        full = ""
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=self.stream,
                timeout=self.timeout,
            ) as response:
                response.raise_for_status()
                if self.stream:
                    print(f"{C.GREEN}", end="", flush=True)
                    for line in response.iter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        full += token
                        print(token, end="", flush=True)
                    print(C.RESET)
                else:
                    full = response.json().get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from exc
        return full


class NvidiaClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        nvidia_cfg = cfg["cloud"]["nvidia"]
        self.base_url = nvidia_cfg["base_url"]
        self.model = nvidia_cfg["model"]
        self.timeout = nvidia_cfg.get(
            "timeout", cfg.get("timeouts", {}).get("api_default", 180)
        )
        self.temp = nvidia_cfg["temperature"]
        self.top_p = nvidia_cfg["top_p"]
        self.max_tokens = nvidia_cfg["max_tokens"]
        self.stream = cfg["agent"].get("stream", True)
        self.provider = "nvidia"
        self.api_key = os.environ.get("NVIDIA_API_KEY", "").strip()

        if not self.api_key:
            env_path = os.path.join(BASE_DIR, ".env")
            if os.path.exists(env_path):
                with open(env_path, encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if line.startswith("NVIDIA_API_KEY"):
                            self.api_key = (
                                line.split("=", 1)[-1].strip().strip('"').strip("'")
                            )
                            break

        if not self.api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY is not set. Add it to .env or environment variables."
            )
        try:
            from openai import OpenAI

            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        except ImportError:
            print("Error: openai library not installed. Run: pip install openai")
            self._client = None

        self.last_list_error = ""

    def list_models(self) -> list:
        self.last_list_error = ""
        if not self._client:
            self.last_list_error = (
                "OpenAI client not available (missing `openai` package)."
            )
            return [self.model]
        try:
            models = self._client.models.list()
            return _unique_sorted_model_ids(model.id for model in models)
        except Exception as exc:
            self.last_list_error = f"{type(exc).__name__}: {exc}"
            return [self.model]

    def chat(self, messages: list, system: str = None) -> str:
        if not self.api_key:
            return "FINAL ANSWER: NVIDIA_API_KEY is not set. Add it to .env or switch the provider to Ollama in config.yaml."
        _wait_for_rate_limit(self.cfg, self.provider, self.model)

        full_messages = []
        is_stubborn = any(
            flag in self.model.lower()
            for flag in ["glm", "gpt-oss", "nemotron", "llama-3.1-405b"]
        )
        if system:
            if is_stubborn:
                temp_messages = []
                user_found = False
                for message in messages:
                    updated = message.copy()
                    if updated["role"] == "user":
                        if not user_found:
                            updated["content"] = (
                                f"{system}\n\n[TASK]: {updated['content']}"
                            )
                            user_found = True
                        else:
                            updated["content"] = (
                                "[REMINDER: Follow the CORE OPERATING DIRECTIVE format.]\n"
                                + updated["content"]
                            )
                    temp_messages.append(updated)
                if not user_found:
                    temp_messages.append({"role": "user", "content": system})
                full_messages = temp_messages
            else:
                full_messages.append({"role": "system", "content": system})
                full_messages.extend(messages)
        else:
            full_messages = messages

        use_color = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
        reasoning_color = "\033[90m" if use_color else ""
        reset = "\033[0m" if use_color else ""
        full = ""
        reasoning_text = ""

        supports_thinking = any(
            flag in self.model.lower() for flag in ["glm", "reasoning", "nemotron"]
        )

        def _request(extra_body: dict | None):
            import time
            from openai import RateLimitError, APIError
            
            max_retries = 5
            base_delay = 5.0
            
            for attempt in range(max_retries):
                try:
                    with Spinner(f"Requesting {self.model}"):
                        # Defensive: never send invalid max_tokens to the API.
                        mt = self.max_tokens
                        try:
                            mt = int(mt)
                        except Exception:
                            mt = self.cfg.get("timeouts", {}).get("fallback_max_tokens", 1024)
                        if mt < 1:
                            mt = self.cfg.get("timeouts", {}).get("fallback_max_tokens", 1024)
                        return self._client.chat.completions.create(
                            model=self.model,
                            messages=full_messages,
                            temperature=self.temp,
                            top_p=self.top_p,
                            max_tokens=mt,
                            extra_body=extra_body,
                            stream=self.stream,
                            timeout=self.timeout,
                        )
                except RateLimitError as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"\n\033[93m⚠ Rate limit hit (429). Retrying in {delay} seconds...\033[0m")
                        time.sleep(delay)
                    else:
                        raise e
                except APIError as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"\n\033[93m⚠ API Rate limit hit. Retrying in {delay} seconds...\033[0m")
                        time.sleep(delay)
                    else:
                        raise e

        extra = None
        if supports_thinking:
            extra = {
                "chat_template_kwargs": {
                    "enable_thinking": True,
                    "clear_thinking": False,
                }
            }

        completion = _request(extra if extra else None)

        if self.stream:
            in_think = False
            for chunk in completion:
                if not getattr(chunk, "choices", None) or not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    reasoning_text += reasoning
                    if not in_think:
                        print(f"{reasoning_color}~  ", end="", flush=True)
                        in_think = True
                    print(reasoning, end="", flush=True)
                content = getattr(delta, "content", None)
                if content:
                    if in_think:
                        print(f"{reset}", end="", flush=True)
                        in_think = False
                    print(content, end="", flush=True)
                    full += content
            print()
        else:
            message = completion.choices[0].message
            reasoning = getattr(message, "reasoning_content", "")
            if reasoning:
                print(f"{reasoning_color}{reasoning}{reset}")
                reasoning_text = reasoning_text + reasoning
            full = message.content or ""

        # Some models (esp. with thinking enabled) can return reasoning-only.
        # If that happens, retry once with thinking disabled to get normal content.
        if (
            supports_thinking
            and (not full or not full.strip())
            and reasoning_text.strip()
        ):
            try:
                completion2 = _request(
                    {"chat_template_kwargs": {"enable_thinking": False}}
                )
                full2 = ""
                if self.stream:
                    for chunk in completion2:
                        if not getattr(chunk, "choices", None) or not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        content = getattr(delta, "content", None)
                        if content:
                            print(content, end="", flush=True)
                            full2 += content
                    print()
                else:
                    msg2 = completion2.choices[0].message
                    full2 = msg2.content or ""
                if full2.strip():
                    return full2
            except Exception:
                # If retry fails, fall through to empty handling in runtime.
                pass
        return full


class GeminiClient:
    """Google Gemini API client using the google-genai SDK."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        gemini_cfg = cfg.get("cloud", {}).get("gemini", {})
        self.model = gemini_cfg.get("model", "gemini-2.0-flash")
        self.temp = gemini_cfg.get("temperature", 1.0)
        self.max_tokens = gemini_cfg.get("max_tokens", 8192)
        self.top_p = gemini_cfg.get("top_p", 0.95)
        self.stream = cfg.get("agent", {}).get("stream", True)
        self.provider = "gemini"
        self.last_list_error = ""

        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not self.api_key:
            env_path = os.path.join(BASE_DIR, ".env")
            if os.path.exists(env_path):
                with open(env_path, encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY"):
                            self.api_key = (
                                line.split("=", 1)[-1].strip().strip('"').strip("'")
                            )
                            break

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to .env or environment variables."
            )

        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            self._genai = genai
        except ImportError:
            print(
                "Error: google-genai not installed. "
                "Run: pip install google-genai"
            )
            self._client = None
            self._genai = None

    def list_models(self) -> list:
        self.last_list_error = ""
        if not self._client:
            self.last_list_error = "google-genai package not installed."
            return [self.model]
        try:
            models = self._client.models.list()
            return _unique_sorted_model_ids(
                m.name.replace("models/", "")
                for m in models
                if "generateContent" in getattr(m, "supported_actions", [])
                or "generateContent" in getattr(m, "supported_generation_methods", [])
            )
        except Exception as exc:
            self.last_list_error = f"{type(exc).__name__}: {exc}"
            return [self.model]

    def chat(self, messages: list, system: str = "") -> str:
        if not self._client:
            return "FINAL ANSWER: google-genai is not installed. Run: pip install google-genai"
        _wait_for_rate_limit(self.cfg, self.provider, self.model)

        use_color = sys.stdout.isatty() and os.getenv("NO_COLOR") is None

        # Build config
        from google.genai import types as genai_types

        gen_config = genai_types.GenerateContentConfig(
            temperature=self.temp,
            top_p=self.top_p,
            max_output_tokens=self.max_tokens,
            system_instruction=system if system else None,
        )

        # Convert AgenticOs messages → Gemini Content list
        # Roles: "user" stays "user", "assistant" becomes "model", skip "system"
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                continue  # handled via system_instruction above
            if role == "assistant":
                role = "model"
            if role not in ("user", "model"):
                continue
            contents.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=content)],
            ))

        if not contents:
            return ""

        full = ""
        with Spinner(f"Requesting {self.model}"):
            pass  # spinner shown during setup; streaming prints inline

        if self.stream:
            if use_color:
                print("\033[92m", end="", flush=True)
            for chunk in self._client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=gen_config,
            ):
                token = chunk.text if hasattr(chunk, "text") and chunk.text else ""
                if token:
                    full += token
                    print(token, end="", flush=True)
            if use_color:
                print("\033[0m")
            else:
                print()
        else:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=gen_config,
            )
            full = response.text or ""

        return full


class GroqClient:
    """Groq API client using the official groq SDK."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        groq_cfg = cfg.get("cloud", {}).get("groq", {})
        self.model = groq_cfg.get("model", "llama3-70b-8192")
        self.temp = groq_cfg.get("temperature", 1.0)
        self.max_tokens = groq_cfg.get("max_tokens", 8192)
        self.top_p = groq_cfg.get("top_p", 0.95)
        self.stream = cfg.get("agent", {}).get("stream", True)
        self.provider = "groq"
        self.last_list_error = ""

        self.api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not self.api_key:
            env_path = os.path.join(BASE_DIR, ".env")
            if os.path.exists(env_path):
                with open(env_path, encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        # Fallback for misspelled qrok
                        if line.startswith("GROQ_API_KEY") or line.startswith("QROK_API_KEY"):
                            self.api_key = (
                                line.split("=", 1)[-1].strip().strip('"').strip("'")
                            )
                            break

        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to .env or environment variables."
            )

        try:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        except ImportError:
            print("Error: groq library not installed. Run: pip install groq")
            self._client = None

    def list_models(self) -> list:
        self.last_list_error = ""
        if not self._client:
            self.last_list_error = "groq package not installed."
            return [self.model]
        try:
            models = self._client.models.list()
            return _unique_sorted_model_ids(model.id for model in models.data)
        except Exception as exc:
            self.last_list_error = f"{type(exc).__name__}: {exc}"
            return [self.model]

    def chat(self, messages: list, system: str = "") -> str:
        if not self._client:
            return "FINAL ANSWER: groq is not installed. Run: pip install groq"
        _wait_for_rate_limit(self.cfg, self.provider, self.model)

        # Convert to OpenAI-style messages list
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        use_color = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
        
        with Spinner(f"Requesting {self.model}"):
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=self.temp,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
                stream=self.stream,
            )

        full = ""
        if self.stream:
            if use_color:
                print("\033[92m", end="", flush=True)
            for chunk in completion:
                if not getattr(chunk, "choices", None) or not chunk.choices:
                    continue
                content = getattr(chunk.choices[0].delta, "content", None)
                if content:
                    print(content, end="", flush=True)
                    full += content
            if use_color:
                print("\033[0m")
            else:
                print()
        else:
            full = completion.choices[0].message.content or ""

        return full


class OpenAICompatibleClient:
    """Base class for OpenAI, OpenRouter, and GitHub Models."""
    def __init__(self, cfg: dict, provider: str, env_key: str, default_model: str, base_url: str = None):
        self.cfg = cfg
        provider_cfg = cfg.get("cloud", {}).get(provider, {})
        self.model = provider_cfg.get("model", default_model)
        self.temp = provider_cfg.get("temperature", 1.0)
        self.max_tokens = provider_cfg.get("max_tokens", 8192)
        self.top_p = provider_cfg.get("top_p", 1.0)
        self.stream = cfg.get("agent", {}).get("stream", True)
        self.provider = provider
        self.last_list_error = ""

        self.api_key = os.environ.get(env_key, "").strip()
        if not self.api_key:
            env_path = os.path.join(BASE_DIR, ".env")
            if os.path.exists(env_path):
                with open(env_path, encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if line.startswith(env_key):
                            self.api_key = line.split("=", 1)[-1].strip().strip('"').strip("'")
                            break

        if not self.api_key:
            raise RuntimeError(f"{env_key} is not set. Add it to .env or environment variables.")

        try:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = OpenAI(**kwargs)
        except ImportError:
            print("Error: openai library not installed. Run: pip install openai")
            self._client = None

    def list_models(self) -> list:
        self.last_list_error = ""
        if not self._client:
            self.last_list_error = "openai package not installed."
            return getattr(self, "_cached_models", [self.model])
        try:
            models = self._client.models.list()
            res = _unique_sorted_model_ids(model.id for model in models.data)
            self._cached_models = res
            return res
        except Exception as exc:
            self.last_list_error = f"{type(exc).__name__}: {exc}"
            return getattr(self, "_cached_models", [self.model])

    def chat(self, messages: list, system: str = "") -> str:
        if not self._client:
            return "FINAL ANSWER: openai is not installed. Run: pip install openai"
        _wait_for_rate_limit(self.cfg, self.provider, self.model)

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        use_color = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
        
        with Spinner(f"Requesting {self.model}"):
            # Handle o1/o3-mini which don't support system prompts or some parameters
            kwargs = {
                "model": self.model,
                "messages": full_messages,
                "stream": self.stream
            }
            if not self.model.startswith("o1") and not self.model.startswith("o3"):
                kwargs["temperature"] = self.temp
                kwargs["top_p"] = self.top_p
                kwargs["max_tokens"] = self.max_tokens

            completion = self._client.chat.completions.create(**kwargs)

        full = ""
        if self.stream:
            if use_color:
                print("\033[92m", end="", flush=True)
            for chunk in completion:
                if not getattr(chunk, "choices", None) or not chunk.choices:
                    continue
                content = getattr(chunk.choices[0].delta, "content", None)
                if content:
                    print(content, end="", flush=True)
                    full += content
            if use_color:
                print("\033[0m")
            else:
                print()
        else:
            full = completion.choices[0].message.content or ""

        return full


class OpenAIClient(OpenAICompatibleClient):
    def __init__(self, cfg: dict):
        super().__init__(cfg, "openai", "OPENAI_API_KEY", "gpt-4o-mini")

class OpenRouterClient(OpenAICompatibleClient):
    def __init__(self, cfg: dict):
        super().__init__(cfg, "openrouter", "OPENROUTER_API_KEY", "google/gemma-2-9b-it:free", "https://openrouter.ai/api/v1")

class GithubClient(OpenAICompatibleClient):
    def __init__(self, cfg: dict):
        super().__init__(cfg, "github", "GITHUB_TOKEN", "gpt-4o-mini", "https://models.inference.ai.azure.com")


class DeepseekClient(OpenAICompatibleClient):
    def __init__(self, cfg: dict):
        super().__init__(cfg, "deepseek", "DEEPSEEK_API_KEY", "deepseek-chat", "https://api.deepseek.com")

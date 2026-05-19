"""Model client adapters for Ollama and Nvidia NIM."""

import json
import os
import sys
import time
import logging
from collections import defaultdict, deque

import requests
from core.runtime_config import BASE_DIR
from core.exceptions import RateLimitExhausted
from core.runtime_ui import C, Spinner
from core.retry import retry_call


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

# Environment variables (from .env) are loaded at startup in `main.py`.


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


def _load_api_key(env_key: str, fallback_keys: list[str] | None = None) -> str:
    value = os.environ.get(env_key, "").strip()
    if value:
        return value

    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return ""

    with open(env_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw = line.split("=", 1)
            key = key.strip()
            if key == env_key or (fallback_keys and key in fallback_keys):
                return raw.strip().strip('"').strip("'")
    return ""


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
        performance = self.cfg.get("performance", {})
        max_retries = int(performance.get("max_retries", 5))
        base_delay = float(performance.get("base_retry_delay", 5.0))

        def _do_post():
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=self.stream,
                timeout=self.timeout,
            ) as response:
                # Let caller handle response streaming/consumption; raise for status here.
                response.raise_for_status()
                return response

        def _retry_on_exc(exc: Exception) -> bool:
            # Retry only on HTTP 429. Do not retry ConnectionError here.
            if isinstance(exc, requests.exceptions.HTTPError):
                code = getattr(exc.response, "status_code", None)
                return code == 429
            return False

        def _on_retry(attempt: int, exc: Exception, delay: float):
            logging.warning(
                "ollama rate limit hit (attempt %d). Waiting %.2fs", attempt, delay
            )
            print(f"\n\033[93m⚠ Rate limit hit (429). Retrying in {delay:.2f} seconds...\033[0m")

        try:
            response = retry_call(
                _do_post,
                max_retries=max_retries,
                base_delay=base_delay,
                retry_on_exception=_retry_on_exc,
                on_retry=_on_retry,
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            # Convert exhausted 429s into a uniform RateLimitExhausted error for callers/tests.
            code = getattr(exc.response, "status_code", None)
            if code == 429:
                raise RateLimitExhausted(f"Rate limit exhausted for ollama after {max_retries} retries") from exc
            raise

        # Consume response (streaming or not)
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
        self.api_key = _load_api_key("NVIDIA_API_KEY")

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
            from openai import RateLimitError, APIError

            performance = self.cfg.get("performance", {})
            max_retries = int(performance.get("max_retries", 5))
            base_delay = float(performance.get("base_retry_delay", 5.0))

            def _do_request():
                with Spinner(f"Requesting {self.model}", cfg=self.cfg):
                    # Defensive: never send invalid max_tokens to the API.
                    mt = self.max_tokens
                    try:
                        mt = int(mt)
                    except (ValueError, TypeError):
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

            def _retry_on_exc(exc: Exception) -> bool:
                if isinstance(exc, RateLimitError):
                    return True
                if isinstance(exc, APIError) and "429" in str(exc):
                    return True
                return False

            def _on_retry(attempt: int, exc: Exception, delay: float):
                logging.warning(
                    f"{self.provider} rate limit hit (attempt {attempt}). Waiting {delay:.2f}s"
                )
                print(f"\n\033[93m⚠ Rate limit hit (429). Retrying in {delay:.2f} seconds...\033[0m")

            try:
                return retry_call(
                    _do_request,
                    max_retries=max_retries,
                    base_delay=base_delay,
                    retry_on_exception=_retry_on_exc,
                    on_retry=_on_retry,
                )
            except RateLimitError as e:
                raise RateLimitExhausted(
                    f"Rate limit exhausted for {self.provider} after {max_retries} retries"
                ) from e
            except APIError as e:
                if "429" in str(e):
                    raise RateLimitExhausted(
                        f"Rate limit exhausted for {self.provider} after {max_retries} retries"
                    ) from e
                raise

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
            except (ValueError, RuntimeError, AttributeError):
                # If retry fails, fall through to empty handling in runtime.
                pass
        return full


class GeminiClient:
    """Google Gemini API client using the google-genai SDK."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        gemini_cfg = cfg.get("cloud", {}).get("gemini", {})
        self.model = gemini_cfg.get("model")
        self.temp = gemini_cfg.get("temperature", 1.0)
        self.max_tokens = gemini_cfg.get("max_tokens", 8192)
        self.top_p = gemini_cfg.get("top_p", 0.95)
        self.stream = cfg.get("agent", {}).get("stream", True)
        self.provider = "gemini"
        self.last_list_error = ""

        self.api_key = _load_api_key("GEMINI_API_KEY")
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
        self.model = groq_cfg.get("model", cfg.get("agent", {}).get("default_model", "llama3-70b-8192"))
        self.temp = groq_cfg.get("temperature", 1.0)
        self.max_tokens = groq_cfg.get("max_tokens", 8192)
        self.top_p = groq_cfg.get("top_p", 0.95)
        self.stream = cfg.get("agent", {}).get("stream", True)
        self.provider = "groq"
        self.last_list_error = ""

        self.api_key = _load_api_key("GROQ_API_KEY", fallback_keys=["QROK_API_KEY"])
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
    def __init__(self, cfg: dict, provider: str, env_key: str):
        self.cfg = cfg
        provider_cfg = cfg.get("cloud", {}).get(provider, {})

        self.model = provider_cfg.get("model")
        if not self.model:
            raise RuntimeError(f"Missing 'model' configuration for {provider} in config/providers.yaml")

        self.temp = provider_cfg.get("temperature", 1.0)
        self.max_tokens = provider_cfg.get("max_tokens", 8192)
        self.top_p = provider_cfg.get("top_p", 1.0)
        self.stream = cfg.get("agent", {}).get("stream", True)
        self.provider = provider
        self.last_list_error = ""

        self.api_key = _load_api_key(env_key)
        if not self.api_key:
            raise RuntimeError(f"{env_key} is not set. Add it to .env or environment variables.")

        try:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key}

            base_url = provider_cfg.get("base_url")
            if base_url:
                kwargs["base_url"] = base_url
            elif provider != "openai":
                raise RuntimeError(f"Missing 'base_url' configuration for {provider} in config/providers.yaml")

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
        
        performance = self.cfg.get("performance", {})
        max_retries = int(performance.get("max_retries", 5))
        base_delay = float(performance.get("base_retry_delay", 5.0))

        # Prepare kwargs for the OpenAI-compatible create call
        kwargs = {
            "model": self.model,
            "messages": full_messages,
            "stream": self.stream,
        }
        if not self.model.startswith("o1") and not self.model.startswith("o3"):
            kwargs["temperature"] = self.temp
            kwargs["top_p"] = self.top_p
            kwargs["max_tokens"] = self.max_tokens

        def _do_create():
            with Spinner(f"Requesting {self.model}"):
                return self._client.chat.completions.create(**kwargs)

        def _retry_on_exc(exc: Exception) -> bool:
            try:
                from openai import RateLimitError, APIError
            except Exception:
                return False
            if isinstance(exc, RateLimitError):
                return True
            if isinstance(exc, APIError) and "429" in str(exc):
                return True
            return False

        def _on_retry(attempt: int, exc: Exception, delay: float):
            logging.warning(
                "%s rate limit hit (attempt %d). Waiting %.2fs", self.provider, attempt, delay
            )
            print(f"\n\033[93m⚠ Rate limit hit (429). Retrying in {delay:.2f} seconds...\033[0m")

        try:
            completion = retry_call(
                _do_create,
                max_retries=max_retries,
                base_delay=base_delay,
                retry_on_exception=_retry_on_exc,
                on_retry=_on_retry,
            )
        except Exception as e:
            # Convert common rate-limit exceptions into RateLimitExhausted for callers/tests
            try:
                from openai import RateLimitError, APIError
                if isinstance(e, RateLimitError) or (isinstance(e, APIError) and "429" in str(e)):
                    raise RateLimitExhausted(f"Rate limit exhausted for {self.provider} after {max_retries} retries") from e
            except Exception:
                pass
            raise

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
        super().__init__(cfg, "openai", "OPENAI_API_KEY")

class OpenRouterClient(OpenAICompatibleClient):
    def __init__(self, cfg: dict):
        super().__init__(cfg, "openrouter", "OPENROUTER_API_KEY")

class GithubClient(OpenAICompatibleClient):
    def __init__(self, cfg: dict):
        super().__init__(cfg, "github", "GITHUB_TOKEN")


class DeepseekClient(OpenAICompatibleClient):
    def __init__(self, cfg: dict):
        super().__init__(cfg, "deepseek", "DEEPSEEK_API_KEY")


class TieredClient:
    """Wraps multiple model clients and provides automatic failover.

    If the primary client raises an exception during `chat()`, the TieredClient
    automatically tries the next client in the tier list.  This ensures near-100%
    uptime across providers.

    Usage:
        primary = OllamaClient(cfg)
        fallbacks = [GeminiClient(cfg), GroqClient(cfg)]
        client = TieredClient(primary, fallbacks)
        response = client.chat(messages, system="...")
    """

    def __init__(self, primary, fallbacks: list = None):
        self.primary = primary
        self.fallbacks = fallbacks or []
        self._active = primary
        self._failure_count: dict[str, int] = {}  # provider -> count

    # ── Proxy properties (delegate to active client) ──
    @property
    def provider(self):
        return self._active.provider

    @property
    def model(self):
        return self._active.model

    @model.setter
    def model(self, value):
        self._active.model = value

    @property
    def last_list_error(self):
        return getattr(self._active, "last_list_error", "")

    @last_list_error.setter
    def last_list_error(self, value):
        self._active.last_list_error = value

    def list_models(self) -> list:
        return self._active.list_models()

    def chat(self, messages: list, system: str = "") -> str:
        """Try the active client; on failure, cascade through fallbacks."""
        clients = [self._active] + [
            c for c in ([self.primary] + self.fallbacks) if c is not self._active
        ]

        last_error = None
        for client in clients:
            try:
                response = client.chat(messages, system=system)
                # Success: reset failure count and promote this client
                self._failure_count[client.provider] = 0
                if client is not self._active:
                    print(
                        f"{C.YELLOW}-> Failover succeeded. Now using: "
                        f"{client.provider}/{client.model}{C.RESET}"
                    )
                    self._active = client
                return response
            except Exception as e:
                self._failure_count[client.provider] = (
                    self._failure_count.get(client.provider, 0) + 1
                )
                print(
                    f"{C.RED}[TieredClient] {client.provider}/{client.model} "
                    f"failed ({e}). Trying next...{C.RESET}"
                )
                last_error = e

        # All clients failed
        raise RuntimeError(
            f"All tiered clients exhausted. Last error: {last_error}"
        )

    def get_active_provider(self) -> str:
        """Return the currently active provider name."""
        return self._active.provider

    def get_failure_stats(self) -> dict:
        """Return per-provider failure counts."""
        return dict(self._failure_count)

import pytest
from unittest.mock import patch, MagicMock, mock_open
from core.model_clients import OllamaClient, NvidiaClient
from core.exceptions import RateLimitExhausted
import requests
import logging
import os

class TestModelClientsRateLimiting:
    def setup_method(self):
        self.cfg = {
            "performance": {"max_retries": 3, "base_retry_delay": 0.01},
            "agent": {"stream": False, "default_model": "test"},
            "ollama": {"base_url": "http://localhost:11434", "default_model": "llama2", "timeout": 10, "temperature": 0.7, "num_ctx": 4096},  # DevSkim: ignore
            "cloud": {"nvidia": {"base_url": "https://api.nvidia.com", "model": "nemotron", "timeout": 10, "temperature": 0.7, "top_p": 1.0, "max_tokens": 1000}}
        }

    @patch('core.model_clients.requests.post')
    def test_ollama_429_retries_and_exhaustion(self, mock_post, caplog):
        client = OllamaClient(self.cfg)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_error = requests.exceptions.HTTPError("429 Too Many Requests")
        mock_error.response = mock_response

        mock_context = MagicMock()
        mock_context.__enter__.return_value.raise_for_status.side_effect = mock_error
        mock_post.return_value = mock_context

        with caplog.at_level(logging.WARNING):
            with pytest.raises(RateLimitExhausted) as excinfo:
                client.chat([{"role": "user", "content": "hi"}])

        assert mock_post.call_count == 3
        assert "Rate limit exhausted" in str(excinfo.value)

        warnings = [record for record in caplog.records if record.levelname == 'WARNING' and 'rate limit hit' in record.message]
        assert len(warnings) == 2
        assert "ollama rate limit hit (attempt 1)" in warnings[0].message

    @patch('core.model_clients.requests.post')
    def test_ollama_jitter_applied(self, mock_post):
        client = OllamaClient(self.cfg)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_error = requests.exceptions.HTTPError("429 Too Many Requests")
        mock_error.response = mock_response

        mock_context = MagicMock()
        mock_context.__enter__.return_value.raise_for_status.side_effect = mock_error
        mock_post.return_value = mock_context

        with patch('time.sleep') as mock_sleep:
            with pytest.raises(RateLimitExhausted):
                client.chat([{"role": "user", "content": "hi"}])

            assert mock_sleep.call_count == 2
            sleep_args = [call.args[0] for call in mock_sleep.mock_calls]
            assert sleep_args[0] >= 0.01 and sleep_args[0] < 0.011
            assert sleep_args[1] >= 0.02 and sleep_args[1] < 0.022
            assert sleep_args[0] != 0.01

    @patch('core.model_clients.os.environ.get')
    def test_nvidia_429_retries_and_exhaustion(self, mock_env_get, caplog):
        def side_effect(k, default=""):
            if k == "NVIDIA_API_KEY":
                return "fake_key"
            return default
        mock_env_get.side_effect = side_effect

        with patch('openai.OpenAI'):
            client = NvidiaClient(self.cfg)

        client.api_key = "fake_key"

        from openai import RateLimitError
        import httpx

        mock_create = MagicMock()
        mock_create.side_effect = RateLimitError(
            message="Rate limit reached",
            response=httpx.Response(429, request=httpx.Request("POST", "https://test.com")),
            body=None
        )

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_create
        client._client = mock_client_instance

        with caplog.at_level(logging.WARNING):
            with pytest.raises(RateLimitExhausted) as excinfo:
                client.chat([{"role": "user", "content": "hi"}])

        assert mock_create.call_count == 3
        assert "Rate limit exhausted" in str(excinfo.value)

        warnings = [record for record in caplog.records if record.levelname == 'WARNING' and 'rate limit hit' in record.message]
        assert len(warnings) == 2
        assert "nvidia rate limit hit (attempt 1)" in warnings[0].message


class TestAdditionalModelClients:
    def setup_method(self):
        self.cfg = {
            "agent": {"stream": False, "default_model": "test"},
            "cloud": {
                "gemini": {"model": "gemini-flash"},
                "groq": {"model": "llama-3"},
                "openai": {"model": "gpt-4"},
                "openrouter": {"model": "router-model"},
                "github": {"model": "gh-model"},
                "deepseek": {"model": "ds-model"}
            }
        }

    @patch("core.model_clients.os.environ.get")
    def test_gemini_client(self, mock_env_get):
        def side_effect(k, default=""):
            return "fake_key" if k == "GEMINI_API_KEY" else default
        mock_env_get.side_effect = side_effect

        mock_genai = MagicMock()
        mock_client_inst = MagicMock()
        mock_genai.Client.return_value = mock_client_inst
        
        mock_response = MagicMock()
        mock_response.text = "gemini response"
        mock_client_inst.models.generate_content.return_value = mock_response

        # list models
        mock_model = MagicMock()
        mock_model.name = "models/gemini-flash"
        mock_model.supported_actions = ["generateContent"]
        mock_client_inst.models.list.return_value = [mock_model]

        mock_google = MagicMock()
        mock_google.genai = mock_genai
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai, "google.genai.types": MagicMock()}):
            from core.model_clients import GeminiClient
            client = GeminiClient(self.cfg)
            res = client.chat([{"role": "user", "content": "hi"}])
            assert "gemini response" in res
            
            # list_models test
            models = client.list_models()
            assert "gemini-flash" in models

    @patch("core.model_clients.os.environ.get")
    def test_groq_client(self, mock_env_get):
        def side_effect(k, default=""):
            return "fake_key" if k == "GROQ_API_KEY" else default
        mock_env_get.side_effect = side_effect

        mock_groq = MagicMock()
        mock_client_inst = MagicMock()
        mock_groq.Groq.return_value = mock_client_inst
        
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "groq response"
        mock_client_inst.chat.completions.create.return_value = mock_completion

        # list models
        mock_m = MagicMock()
        mock_m.id = "llama-3"
        mock_client_inst.models.list.return_value.data = [mock_m]

        with patch.dict("sys.modules", {"groq": mock_groq}):
            from core.model_clients import GroqClient
            client = GroqClient(self.cfg)
            res = client.chat([{"role": "user", "content": "hi"}])
            assert "groq response" in res
            
            models = client.list_models()
            assert "llama-3" in models

    @patch("core.model_clients.os.environ.get")
    def test_openai_client(self, mock_env_get):
        def side_effect(k, default=""):
            return "fake_key" if k == "OPENAI_API_KEY" else default
        mock_env_get.side_effect = side_effect

        mock_openai = MagicMock()
        mock_client_inst = MagicMock()
        mock_openai.OpenAI.return_value = mock_client_inst
        
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "openai response"
        mock_client_inst.chat.completions.create.return_value = mock_completion

        with patch.dict("sys.modules", {"openai": mock_openai}):
            from core.model_clients import OpenAIClient
            client = OpenAIClient(self.cfg)
            res = client.chat([{"role": "user", "content": "hi"}])
            assert "openai response" in res

    @patch("core.model_clients.os.environ.get")
    def test_other_openai_compatible_clients(self, mock_env_get):
        def side_effect(k, default=""):
            if k == "OPENROUTER_API_KEY":
                return "router_key"
            if k == "GITHUB_TOKEN":
                return "gh_key"
            if k == "DEEPSEEK_API_KEY":
                return "ds_key"
            return default
        mock_env_get.side_effect = side_effect

        mock_openai = MagicMock()
        mock_client_inst = MagicMock()
        mock_openai.OpenAI.return_value = mock_client_inst
        
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "compatible response"
        mock_client_inst.chat.completions.create.return_value = mock_completion

        with patch.dict("sys.modules", {"openai": mock_openai}):
            from core.model_clients import OpenRouterClient, GithubClient, DeepseekClient
            
            # OpenRouter
            or_client = OpenRouterClient(self.cfg)
            assert or_client.chat([{"role": "user", "content": "hi"}]) == "compatible response"
            
            # GitHub
            gh_client = GithubClient(self.cfg)
            assert gh_client.chat([{"role": "user", "content": "hi"}]) == "compatible response"
            
            # Deepseek
            ds_client = DeepseekClient(self.cfg)
            assert ds_client.chat([{"role": "user", "content": "hi"}]) == "compatible response"

    def test_tiered_client_fallback(self):
        from core.model_clients import TieredClient
        
        primary = MagicMock()
        primary.provider = "primary"
        primary.model = "model-a"
        primary.chat.side_effect = Exception("Primary failed")
        
        fallback1 = MagicMock()
        fallback1.provider = "fallback1"
        fallback1.model = "model-b"
        fallback1.chat.return_value = "fallback response"
        
        client = TieredClient(primary, [fallback1])
        res = client.chat([{"role": "user", "content": "hi"}])
        
        assert "fallback response" in res
        assert client._active == fallback1
        assert client._failure_count["primary"] == 1
        
        # Test other properties/methods of TieredClient
        assert client.provider == "fallback1"
        assert client.model == "model-b"
        client.model = "model-c"
        assert fallback1.model == "model-c"
        
        client.list_models()
        fallback1.list_models.assert_called_once()
        
        assert client.get_active_provider() == "fallback1"
        stats = client.get_failure_stats()
        assert stats["primary"] == 1

def test_model_clients_rate_limit_helpers():
    from core.model_clients import _get_nested, _configured_rpm, _wait_for_rate_limit, _RATE_LIMIT_HISTORY
    
    cfg = {
        "rate_limits": {
            "enabled": True,
            "default_rpm": 60,
            "safety_factor": 0.5,
            "window_seconds": 2,
            "providers": {
                "ollama": {"rpm": 120}
            },
            "models": {
                "ollama:llama2": {"rpm": 240}
            }
        }
    }
    
    # 1. _get_nested
    assert _get_nested(cfg, "rate_limits.providers.ollama.rpm") == 120
    assert _get_nested(cfg, "rate_limits.nonexistent") is None
    
    # 2. _configured_rpm
    # With model match
    assert _configured_rpm(cfg, "ollama", "llama2") == 120.0  # 240 * 0.5 safety
    # With provider match
    assert _configured_rpm(cfg, "ollama", "nonexistent") == 60.0  # 120 * 0.5 safety
    # With default match
    assert _configured_rpm(cfg, "other", "nonexistent") == 30.0  # 60 * 0.5 safety
    
    # 3. _wait_for_rate_limit
    _wait_for_rate_limit(cfg, "other", "nonexistent")  # First request, shouldn't block
    
    # Trigger pacing sleep
    key = "other:nonexistent"
    _RATE_LIMIT_HISTORY[key].append(0.0) # Add a past request to trigger limit
    # Set max requests artificially
    with patch("time.sleep") as mock_sleep:
        _wait_for_rate_limit(cfg, "other", "nonexistent")
        # Should call sleep because window has old requests
        mock_sleep.assert_called()

def test_dotenv_parser_fallback():
    # Simulate importing without dotenv package using sys.modules mock
    with patch.dict("sys.modules", {"dotenv": None}):
        # Mock os.path.exists to return True for .env and builtins.open to read dummy env
        def mock_exists(path):
            return path.endswith(".env")
        mock_open_content = mock_open(read_data="TEST_DOTENV_KEY = dotenv_value\n# Comment\nINVALID_LINE")
        
        with patch("os.path.exists", side_effect=mock_exists), \
             patch("builtins.open", mock_open_content):
                 # Reload module or run the code block again
                 import importlib
                 import core.model_clients
                 importlib.reload(core.model_clients)
                 
                 assert os.environ.get("TEST_DOTENV_KEY") == "dotenv_value"

@patch('core.model_clients.requests.get')
def test_ollama_list_models(mock_get, caplog):
    cfg = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "llama2",
            "timeout": 10,
            "temperature": 0.7,
            "num_ctx": 4096
        },
        "agent": {"stream": False}
    }
    client = OllamaClient(cfg)
    
    # 1. Success path
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "models": [
            {"name": "llama2"},
            {"name": "llama3"}
        ]
    }
    mock_get.return_value = mock_resp
    assert client.list_models() == ["llama2", "llama3"]
    
    # 2. Failure path
    mock_get.side_effect = Exception("Connection refused")
    assert client.list_models() == []
    assert "Connection refused" in client.last_list_error

@patch('core.model_clients.requests.post')
def test_ollama_chat_streaming(mock_post):
    cfg = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "llama2",
            "timeout": 10,
            "temperature": 0.7,
            "num_ctx": 4096
        },
        "agent": {"stream": True}
    }
    client = OllamaClient(cfg)
    
    mock_resp = MagicMock()
    # Mock iter_lines to stream chunks
    mock_resp.iter_lines.return_value = [
        b'{"message": {"content": "Hello "}}',
        b'{"message": {"content": "World!"}}'
    ]
    
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_resp
    mock_post.return_value = mock_context
    
    res = client.chat([{"role": "user", "content": "hi"}])
    assert res == "Hello World!"

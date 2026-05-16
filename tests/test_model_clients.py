import pytest
from unittest.mock import patch, MagicMock, Mock
from core.model_clients import OllamaClient, NvidiaClient
from core.exceptions import RateLimitExhausted
import requests
import logging

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

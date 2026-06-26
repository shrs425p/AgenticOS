from unittest.mock import patch, MagicMock
from kernel.models import NvidiaClient

@patch('kernel.models.os.environ.get')
def test_nvidia_thinking_hidden(mock_env_get):
    mock_env_get.side_effect = lambda k, default="": "fake_key" if k == "NVIDIA_API_KEY" else default

    cfg = {
        "cloud": {
            "nvidia": {
                "base_url": "https://api.nvidia.com",
                "model": "llama-3.1-nemotron-70b-instruct",
                "timeout": 10,
                "temperature": 0.7,
                "top_p": 1.0,
                "max_tokens": 1000
            }
        },
        "agent": {
            "stream": True,
            "verbose_thinking": False
        },
        "performance": {
            "max_retries": 3,
            "base_retry_delay": 0.01
        }
    }

    with patch('openai.OpenAI'):
        client = NvidiaClient(cfg)

    # Mock chunk response
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(reasoning_content="Think step 1", content=None))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(reasoning_content=None, content="Final answer"))]

    mock_create = MagicMock(return_value=[chunk1, chunk2])
    client._client = MagicMock()
    client._client.chat.completions.create = mock_create

    with patch('sys.stdout.write') as mock_write:
        res = client.chat([{"role": "user", "content": "hi"}])
        assert res == "Final answer"
        # Since verbose_thinking is False, sys.stdout.write should NOT be called with "Think step 1" or "~  "
        written_strs = [call.args[0] for call in mock_write.mock_calls]
        assert not any("Think step 1" in s for s in written_strs)
        assert not any("~  " in s for s in written_strs)
        assert any("Final answer" in s for s in written_strs)

@patch('kernel.models.os.environ.get')
def test_nvidia_thinking_shown(mock_env_get):
    mock_env_get.side_effect = lambda k, default="": "fake_key" if k == "NVIDIA_API_KEY" else default

    cfg = {
        "cloud": {
            "nvidia": {
                "base_url": "https://api.nvidia.com",
                "model": "llama-3.1-nemotron-70b-instruct",
                "timeout": 10,
                "temperature": 0.7,
                "top_p": 1.0,
                "max_tokens": 1000
            }
        },
        "agent": {
            "stream": True,
            "verbose_thinking": True
        },
        "performance": {
            "max_retries": 3,
            "base_retry_delay": 0.01
        }
    }

    with patch('openai.OpenAI'):
        client = NvidiaClient(cfg)

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(reasoning_content="Think step 1", content=None))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(reasoning_content=None, content="Final answer"))]

    mock_create = MagicMock(return_value=[chunk1, chunk2])
    client._client = MagicMock()
    client._client.chat.completions.create = mock_create

    with patch('sys.stdout.write') as mock_write:
        res = client.chat([{"role": "user", "content": "hi"}])
        assert res == "Final answer"
        # Since verbose_thinking is True, sys.stdout.write should be called with reasoning text
        written_strs = [call.args[0] for call in mock_write.mock_calls]
        assert any("Think step 1" in s for s in written_strs)
        assert any("~  " in s for s in written_strs)
        assert any("Final answer" in s for s in written_strs)

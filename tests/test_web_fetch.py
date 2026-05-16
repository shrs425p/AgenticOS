from unittest.mock import MagicMock, patch
from tools.web.fetch import FetchMixin

class DummyWebTool(FetchMixin):
    def __init__(self, workspace_dir=None):
        self.workspace_dir = workspace_dir
    def _network_error(self, *args, **kwargs):
        return ""
    def _get_session(self):
        import requests
        return requests.Session()
    def _get_timeout(self, *args, **kwargs):
        return 5
    def _resolve_path_in_base(self, path):
        from pathlib import Path
        if self.workspace_dir:
            return Path(self.workspace_dir) / path
        return Path(path)


@patch("tools.web.fetch.requests_module")
def test_fetch_url(mock_req):
    tool = DummyWebTool()

    mock_resp = MagicMock()
    mock_resp.text = "Hello world"
    mock_req.return_value.get.return_value = mock_resp

    res = tool.fetch_url("http://example.com")
    assert res == "Hello world"

    mock_req.return_value.get.side_effect = Exception("timeout")
    res = tool.fetch_url("http://example.com")
    assert "Fetch error" in res


@patch("requests.Session.get")
@patch("tools.web.fetch.bs4_beautifulsoup")
def test_get_page_text(mock_bs4, mock_get):
    tool = DummyWebTool()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>Hello</body></html>"
    mock_get.return_value = mock_resp

    mock_soup = MagicMock()
    mock_soup.get_text.return_value = "Hello"
    mock_bs4.return_value = MagicMock(return_value=mock_soup)

    res = tool.get_page_text("http://example.com")
    assert res == "Hello"

    mock_resp.status_code = 404
    res = tool.get_page_text("http://example.com")
    assert "Error: status 404" in res


@patch("requests.Session.get")
@patch("tools.web.fetch.bs4_beautifulsoup")
def test_get_page_links(mock_bs4, mock_get):
    tool = DummyWebTool()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><a href='/foo'>Foo</a><a href='#bar'>Bar</a></body></html>"
    mock_get.return_value = mock_resp

    from bs4 import BeautifulSoup
    mock_bs4.return_value = BeautifulSoup

    res = tool.get_page_links("http://example.com")
    assert "http://example.com/foo" in res
    assert "#bar" not in res

    # Error path
    mock_get.side_effect = Exception("network fail")
    res = tool.get_page_links("http://example.com")
    assert "Error: network fail" in res


@patch("requests.Session.get")
@patch("tools.web.fetch.bs4_beautifulsoup")
def test_get_page_images(mock_bs4, mock_get):
    tool = DummyWebTool()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><img src='/img.png'/></body></html>"
    mock_get.return_value = mock_resp

    from bs4 import BeautifulSoup
    mock_bs4.return_value = BeautifulSoup

    res = tool.get_page_images("http://example.com")
    assert "http://example.com/img.png" in res


@patch("requests.Session.get")
def test_download_file(mock_get, tmp_path):
    tool = DummyWebTool(workspace_dir=str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"chunk1", b"chunk2"]
    mock_get.return_value = mock_resp

    res = tool.download_file("http://example.com/file", "out.txt")
    assert "Downloaded 12 bytes" in res
    assert (tmp_path / "out.txt").exists()

    mock_get.side_effect = Exception("fail")
    res = tool.download_file("http://example.com/file", "out.txt")
    assert "Download error: fail" in res

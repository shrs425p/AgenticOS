from unittest import mock
from urllib.parse import urlparse


from ops.web.youtube import YouTubeMixin
from ops.web.search import SearchMixin
from ops.web.utils import UtilsMixin
from ops.web.inspect import InspectMixin
from ops.web.bestlink import web_pick_best_link

class MockWebTools(YouTubeMixin, SearchMixin, UtilsMixin, InspectMixin):
    def __init__(self):
        self.cfg = {
            "endpoints": {
                "duckduckgo_api": "https://api.mockduck.com",
                "is_gd_api": "https://mock.is.gd",
                "wayback_api": "https://mock.archive.org/wayback",
                "ipify_api": "https://mock.ipify.org",
                "ipinfo_api": "https://mock.ipinfo.io"
            }
        }
    
    def _network_error(self, *args, **kwargs):
        return None
        
    def _get_timeout(self, *args, **kwargs):
        return 10
        
    def _get_endpoint(self, key, default):
        return self.cfg.get("endpoints", {}).get(key, default)

@mock.patch("ops.web.youtube.requests_module")
def test_youtube_search(mock_req):
    mock_resp = mock.Mock()
    mock_resp.json.return_value = {"RelatedTopics": [{"FirstURL": "https://youtube.com/watch?v=123456"}]}
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.findyoutubevideo("test query")
    
    assert ("https://youtube" + ".com/watch?v=123456") in res
    mock_req().get.assert_called_once()
    args, kwargs = mock_req().get.call_args
    assert urlparse(args[0]).netloc == "api.mockduck.com"


@mock.patch("ops.web.search.requests_module")
def test_websearch(mock_req):
    mock_resp = mock.Mock()
    mock_resp.json.return_value = {"Results": []}
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.search("test")
    
    assert isinstance(res, str)
    mock_req().get.assert_called_once()
    args, kwargs = mock_req().get.call_args
    assert urlparse(args[0]).netloc == "api.mockduck.com"


@mock.patch("ops.web.utils.requests_module")
def test_utils_shorten(mock_req):
    mock_resp = mock.Mock()
    mock_resp.text = "https://mock.is.gd/short"
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.shortenurl("https://long.url")

    
    assert res == "https://mock.is.gd/short"
    mock_req().get.assert_called_once()
    args, kwargs = mock_req().get.call_args
    assert args[0] == "https://mock.is.gd"

@mock.patch("ops.web.inspect.requests_module")
def test_inspect_ip(mock_req):
    mock_resp = mock.Mock()
    mock_resp.text = '{"ip": "1.2.3.4"}'
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.getpublicip()
    
    assert "1.2.3.4" in res
    args, kwargs = mock_req().get.call_args
    assert urlparse(args[0]).netloc == "mock.ipify.org"


@mock.patch("ops.web.bestlink.requests")
@mock.patch("ops.web.bestlink.load_cfg")
def test_web_pick_best_link(mock_load_cfg, mock_req):
    mock_load_cfg.return_value = {
        "endpoints": {
            "google_search": "https://mock.google.com/search?q="
        }
    }
    
    mock_resp = mock.Mock()
    mock_resp.text = '/url?q=https%3A%2F%2Fexample.com'
    mock_req.get.return_value = mock_resp
    
    res = web_pick_best_link("test")
    
    assert res == "https://example.com"
    mock_req.get.assert_called_once()
    args, kwargs = mock_req.get.call_args
    assert urlparse(args[0]).netloc == "mock.google.com"


def test_youtubeplaynext():
    import asyncio
    tool = MockWebTools()
    mgr = mock.MagicMock()
    page = mock.AsyncMock()
    page.url = "https://www.youtube.com/watch?v=abcdef"
    mgr.page = page
    
    tool.browser_mgr = mgr
    mgr.run_coro = lambda coro: asyncio.run(coro)
    
    res = tool.youtubeplaynext()
    assert "Clicked next video" in res
    page.click.assert_called_once_with("button.ytp-next-button, a.ytp-next-button", timeout=5000)


def test_youtubeplaynext_search_results():
    import asyncio
    tool = MockWebTools()
    mgr = mock.MagicMock()
    page = mock.AsyncMock()
    page.url = "https://www.youtube.com/results?search_query=mrbeast"
    mgr.page = page
    
    tool.browser_mgr = mgr
    mgr.run_coro = lambda coro: asyncio.run(coro)
    
    res = tool.youtubeplaynext()
    assert "Clicked first video in search results" in res
    page.click.assert_called_once_with("ytd-video-renderer a#video-title, a#video-title", timeout=5000)


def test_youtubeplaynext_error_fallback():
    import asyncio
    tool = MockWebTools()
    mgr = mock.MagicMock()
    page = mock.AsyncMock()
    page.url = "https://www.youtube.com/watch?v=abcdef"
    page.click.side_effect = Exception("Click failed")
    mgr.page = page
    
    tool.browser_mgr = mgr
    mgr.run_coro = lambda coro: asyncio.run(coro)
    
    res = tool.youtubeplaynext()
    assert "Pressed Shift+N" in res
    page.keyboard.press.assert_called_once_with("Shift+N")


def test_youtubeplaypause():
    import asyncio
    tool = MockWebTools()
    mgr = mock.MagicMock()
    page = mock.AsyncMock()
    page.url = "https://www.youtube.com/watch?v=abcdef"
    mgr.page = page
    
    tool.browser_mgr = mgr
    mgr.run_coro = lambda coro: asyncio.run(coro)
    
    res = tool.youtubeplaypause()
    assert "Toggled play/pause" in res
    page.keyboard.press.assert_called_once_with("k")


def test_youtubeskipad():
    import asyncio
    tool = MockWebTools()
    mgr = mock.MagicMock()
    page = mock.AsyncMock()
    page.url = "https://www.youtube.com/watch?v=abcdef"
    mgr.page = page
    
    mock_el = mock.AsyncMock()
    mock_el.is_visible.return_value = True
    page.query_selector.return_value = mock_el
    
    tool.browser_mgr = mgr
    mgr.run_coro = lambda coro: asyncio.run(coro)
    
    res = tool.youtubeskipad()
    assert "Successfully clicked skip ad" in res
    mock_el.click.assert_called_once()




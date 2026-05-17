from unittest import mock
from urllib.parse import urlparse


from tools.web.youtube import YouTubeMixin
from tools.web.search import SearchMixin
from tools.web.utils import UtilsMixin
from tools.web.inspect import InspectMixin
from tools.web.web_pick_best_link import web_pick_best_link

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

@mock.patch("tools.web.youtube.requests_module")
def test_youtube_search(mock_req):
    mock_resp = mock.Mock()
    mock_resp.json.return_value = {"RelatedTopics": [{"FirstURL": "https://youtube.com/watch?v=123456"}]}
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.find_youtube_video("test query")
    
    assert ("https://youtube" + ".com/watch?v=123456") in res
    mock_req().get.assert_called_once()
    args, kwargs = mock_req().get.call_args
    assert urlparse(args[0]).netloc == "api.mockduck.com"


@mock.patch("tools.web.search.requests_module")
def test_web_search(mock_req):
    mock_resp = mock.Mock()
    mock_resp.json.return_value = {"Results": []}
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.search("test")
    
    assert isinstance(res, str)
    mock_req().get.assert_called_once()
    args, kwargs = mock_req().get.call_args
    assert urlparse(args[0]).netloc == "api.mockduck.com"


@mock.patch("tools.web.utils.requests_module")
def test_utils_shorten(mock_req):
    mock_resp = mock.Mock()
    mock_resp.text = "https://mock.is.gd/short"
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.shorten_url("https://long.url")

    
    assert res == "https://mock.is.gd/short"
    mock_req().get.assert_called_once()
    args, kwargs = mock_req().get.call_args
    assert args[0] == "https://mock.is.gd"

@mock.patch("tools.web.inspect.requests_module")
def test_inspect_ip(mock_req):
    mock_resp = mock.Mock()
    mock_resp.text = '{"ip": "1.2.3.4"}'
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.get_public_ip()
    
    assert "1.2.3.4" in res
    args, kwargs = mock_req().get.call_args
    assert urlparse(args[0]).netloc == "mock.ipify.org"


@mock.patch("tools.web.web_pick_best_link.requests")
@mock.patch("tools.web.web_pick_best_link.load_config")
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


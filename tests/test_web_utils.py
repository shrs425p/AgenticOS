from unittest import mock
from tools.web.utils import UtilsMixin

class MockWebTools(UtilsMixin):
    def __init__(self):
        self.cfg = {
            "endpoints": {
                "is_gd_api": "https://is.gd/create.php",
                "wayback_api": "https://archive.org/wayback/available"
            }
        }
        self._network_err = None

    def _network_error(self, *args, **kwargs):
        return self._network_err
        
    def _get_timeout(self, *args, **kwargs):
        return 10
        
    def _get_endpoint(self, key, default):
        return self.cfg.get("endpoints", {}).get(key, default)
        
    def _get_session(self):
        m = mock.MagicMock()
        return m

@mock.patch("tools.web.utils.requests_module")
def test_shorten_url(mock_req):
    mock_resp = mock.MagicMock()
    mock_resp.text = " https://is.gd/short "
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    assert tool.shorten_url("http://google.com") == "https://is.gd/short"
    
    # Network error
    tool._network_err = "No Network"
    assert tool.shorten_url("http://google.com") == "No Network"

@mock.patch("tools.web.utils.requests_module")
def test_expand_url(mock_req):
    mock_resp = mock.MagicMock()
    mock_resp.url = "https://google.com"
    mock_req().head.return_value = mock_resp
    
    tool = MockWebTools()
    assert tool.expand_url("https://is.gd/short") == "https://google.com"
    
    # Exception handling
    mock_req().head.side_effect = Exception("Expand failed")
    assert "Expand error" in tool.expand_url("https://is.gd/short")

@mock.patch("tools.web.utils.bs4_beautifulsoup")
@mock.patch("tools.web.utils.requests_module")
def test_rss_feed(mock_req, mock_bs4):
    mock_resp = mock.MagicMock()
    mock_resp.text = "<rss><item><title>A</title><link>B</link><pubDate>C</pubDate></item></rss>"
    mock_req().get.return_value = mock_resp
    
    soup = mock.MagicMock()
    mock_bs4.return_value = lambda text, parser: soup
    
    item = mock.MagicMock()
    title = mock.MagicMock()
    title.get_text.return_value = "A"
    link = mock.MagicMock()
    link.get_text.return_value = "B"
    pub = mock.MagicMock()
    pub.get_text.return_value = "C"
    
    item.find.side_effect = lambda tag: {
        "title": title,
        "link": link,
        "pubDate": pub
    }.get(tag)
    
    soup.find_all.return_value = [item]
    
    tool = MockWebTools()
    assert "A | B | C" in tool.rss_feed("https://feed.xml")

@mock.patch("tools.web.utils.requests_module")
def test_wayback_snapshot(mock_req):
    mock_resp = mock.MagicMock()
    mock_resp.text = '{"snapshot": "ok"}'
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    assert tool.wayback_snapshot("http://google.com") == '{"snapshot": "ok"}'

@mock.patch("tools.web.utils.bs4_beautifulsoup")
def test_scrape_table(mock_bs4):
    tool = MockWebTools()
    session = tool._get_session()
    
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<table></table>"
    session.get.return_value = mock_resp
    
    soup = mock.MagicMock()
    mock_bs4.return_value = lambda text, parser: soup
    
    table = mock.MagicMock()
    tr = mock.MagicMock()
    td = mock.MagicMock()
    td.get_text.return_value = "Cell content"
    tr.find_all.return_value = [td]
    table.find_all.return_value = [tr]
    soup.find_all.return_value = [table]
    
    with mock.patch.object(tool, "_get_session", return_value=session):
        # Successful table scrape
        res = tool.scrape_table("http://table.com")
        assert "Cell content" in res
        
        # Table out of range
        assert "out of range" in tool.scrape_table("http://table.com", "5")
        
        # No tables found
        soup.find_all.return_value = []
        assert "No tables found" in tool.scrape_table("http://table.com")

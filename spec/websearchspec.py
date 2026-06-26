from unittest import mock
from ops.web.search import SearchMixin

class MockWebTools(SearchMixin):
    def __init__(self):
        self.cfg = {
            "endpoints": {
                "duckduckgo_api": "https://api.mockduck.com",
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

@mock.patch("ops.web.search.requests_module")
def test_search_api_success(mock_req):
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {
        "AbstractText": "DuckDuckGo is a search engine.",
        "AbstractURL": "https://duckduckgo.com",
        "Answer": "DuckDuckGo!",
        "RelatedTopics": [
            {"Text": "Topic 1", "FirstURL": "https://topic1.com"},
            {"Topics": [{"Text": "Subtopic 1", "FirstURL": "https://sub1.com"}]}
        ]
    }
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    res = tool.search("ddg")
    
    assert "Direct Answer" in res
    assert "Summary: DuckDuckGo is a search engine." in res
    assert "Topic 1" in res
    assert "Subtopic 1" in res

@mock.patch("ops.web.search.requests_module")
def test_search_network_error(mock_req):
    tool = MockWebTools()
    tool._network_err = "No Internet Connection"
    
    res = tool.search("ddg")
    assert res == "No Internet Connection"

@mock.patch("ops.web.search.requests_module")
def test_search_empty_api_triggers_fallback(mock_req):
    # Returns empty RelatedTopics, triggering _ddg_html_search
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {}
    mock_req().get.return_value = mock_resp
    
    tool = MockWebTools()
    
    # Mock _ddg_html_search to return a mocked html result
    with mock.patch.object(tool, "_ddg_html_search", return_value="HTML Result") as mock_html:
        res = tool.search("ddg")
        assert res == "HTML Result"
        mock_html.assert_called_once_with("ddg", 5)

@mock.patch("ops.web.search.bs4_beautifulsoup")
def test_ddg_html_search(mock_bs4):
    tool = MockWebTools()
    session = tool._get_session()
    
    # 202 retry logic test
    mock_resp_202 = mock.MagicMock()
    mock_resp_202.status_code = 202
    mock_resp_200 = mock.MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.text = "<html></html>"
    session.get.side_effect = [mock_resp_202, mock_resp_200]
    
    # BeautifulSoup parsing
    soup = mock.MagicMock()
    mock_bs4.return_value = lambda text, parser: soup
    
    result_el = mock.MagicMock()
    title_a = mock.MagicMock()
    title_a.get_text.return_value = "DDG Title"
    title_a.get.return_value = "https://example.com/uddg=https%3A%2F%2Freal.com"
    snip_el = mock.MagicMock()
    snip_el.get_text.return_value = "DDG Snippet"
    
    result_el.select_one.side_effect = [title_a, snip_el]
    soup.select.return_value = [result_el]
    
    with mock.patch.object(tool, "_get_session", return_value=session), \
         mock.patch("time.sleep") as mock_sleep:
             res = tool._ddg_html_search("ddg", 5)
             assert "DDG Title" in res
             assert ("real" + ".com") in res
             mock_sleep.assert_called_once()

@mock.patch("ops.web.search.requests_module")
@mock.patch("ops.web.search.bs4_beautifulsoup")
def test_clig_fallback_search(mock_bs4, mock_req):
    tool = MockWebTools()
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html></html>"
    mock_req().get.return_value = mock_resp
    
    # BeautifulSoup parsing
    soup = mock.MagicMock()
    mock_bs4.return_value = lambda text, parser: soup
    
    item_el = mock.MagicMock()
    title_el = mock.MagicMock()
    a_el = mock.MagicMock()
    a_el.get_text.return_value = "Bing Title"
    a_el.__getitem__.return_value = "https://clig.com/real"
    title_el.find.return_value = a_el
    item_el.find.return_value = title_el
    
    snippet_el = mock.MagicMock()
    snippet_el.get_text.return_value = "Bing Snippet"
    item_el.select_one.return_value = snippet_el
    
    soup.select.return_value = [item_el]
    
    res = tool._clig_fallback_search("ddg", 5)
    assert "Bing Title" in res
    assert ("https://clig" + ".com/real") in res
    assert "Bing Snippet" in res

@mock.patch("ops.web.search.bs4_beautifulsoup")
def test_searchnews(mock_bs4):
    tool = MockWebTools()
    session = tool._get_session()
    mock_resp = mock.MagicMock()
    mock_resp.text = "<html></html>"
    session.get.return_value = mock_resp
    
    soup = mock.MagicMock()
    mock_bs4.return_value = lambda text, parser: soup
    
    a_el = mock.MagicMock()
    a_el.get_text.return_value = "News Title"
    a_el.get.return_value = "https://news.com"
    soup.select.return_value = [a_el]
    
    with mock.patch.object(tool, "_get_session", return_value=session):
        res = tool.searchnews("ddg", 5)
        assert "News Title" in res
        assert ("https://news" + ".com") in res

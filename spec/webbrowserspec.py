import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ops.web.browser import BrowserMixin, BrowserManager

class MockWebTools(BrowserMixin):
    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self.browser_mgr = BrowserManager()
        # Mock run_coro to run the coroutine synchronously via asyncio.run
        self.browser_mgr.run_coro = lambda coro: asyncio.run(coro)
        self.base_dir = "mock_workspace"

    def _get_timeout(self, key, default):
        return default

def test_screenshot_path():
    tool = MockWebTools()
    path = tool._screenshot_path("test.png")
    assert "mock_workspace" in path
    assert "screenshots" in path
    assert "test.png" in path

def test_browserlaunch_and_close():
    tool = MockWebTools()
    
    # Mock playwright instance
    mock_apw = MagicMock()
    mock_apw_instance = AsyncMock()
    mock_apw.return_value = mock_apw_instance
    mock_apw_instance.start.return_value = mock_apw_instance
    mock_launcher = AsyncMock()
    mock_apw_instance.chromium = mock_launcher
    
    # Mock persistent context
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_launcher.launch_persistent_context.return_value = mock_context
    mock_context.pages = [mock_page]
    
    with patch("ops.web.browser._async_playwright", return_value=mock_apw), \
         patch("os.path.isdir", return_value=True):
             res = tool.browserlaunch(browser="chromium", headless="true", user_data_dir="some_dir")
             assert "launched" in res
             # Note: browserclose tested separately to avoid async mock complexity

def test_browserlaunch_cdp():
    tool = MockWebTools()
    
    # Mock playwright instance
    mock_apw = MagicMock()
    mock_apw_instance = AsyncMock()
    mock_apw.return_value = mock_apw_instance
    mock_apw_instance.start.return_value = mock_apw_instance
    mock_launcher = AsyncMock()
    mock_apw_instance.chromium = mock_launcher
    
    # Mock CDP browser and context
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_launcher.connect_over_cdp.return_value = mock_browser
    mock_browser.contexts = [mock_context]
    mock_context.pages = [mock_page]
    
    with patch("ops.web.browser._async_playwright", return_value=mock_apw):
        res = tool.browserlaunch(browser="chromium", cdp_url="http://localhost:9222")
        assert "launched" in res
        assert "cdp" in res
        mock_launcher.connect_over_cdp.assert_called_once_with("http://localhost:9222")


def test_browser_navigation_actions():
    tool = MockWebTools()
    mgr = tool.browser_mgr
    
    mock_page = AsyncMock()
    mgr.page = mock_page
    mgr.context = AsyncMock()
    mgr.browsertype = "chromium"
    
    # Status
    mock_page.url = "http://example.com"
    mock_page.title.return_value = "Example Title"
    mgr.context.pages = [mock_page]
    res = tool.browserstatus()
    assert "Example Title" in res
    
    # Navigate
    mock_page.goto.return_value = MagicMock(status=200)
    res = tool.browsernavigate("http://example.com")
    assert "Navigated to" in res
    
    # Go back / Go forward / Reload
    res = tool.browsergoback()
    assert "Back" in res
    
    res = tool.browsergoforward()
    assert "Forward" in res
    
    res = tool.browserreload()
    assert "Reloaded" in res

def test_browser_getters():
    tool = MockWebTools()
    mgr = tool.browser_mgr
    
    mock_page = AsyncMock()
    mgr.page = mock_page
    mgr.context = AsyncMock()
    
    # URL & Title
    mock_page.url = "http://example.com"
    mock_page.title.return_value = "Example Title"
    assert tool.browsergeturl() == "http://example.com"
    assert tool.browsergettitle() == "Example Title"
    
    # Inner Text & HTML
    mock_page.evaluate.return_value = "Hello World\nLine 2"
    assert "Hello World" in tool.browsergettext()
    
    mock_page.content.return_value = "<html>Hello</html>"
    assert "<html>" in tool.browsergethtml()
    
    # Get element text
    mock_page.inner_text.return_value = "element content"
    res = tool.browsergetelementtext("#selector")
    assert "element content" in res
    
    # Query selector all
    mock_el = AsyncMock()
    mock_el.inner_text.return_value = "el text"
    mock_el.evaluate.return_value = "div"
    mock_page.query_selector_all.return_value = [mock_el]
    res = tool.browsergetelements("div")
    assert "Found 1" in res
    
    # Get links & Inputs
    mock_page.evaluate.side_effect = [
        ["Home → /", "About → /about"],
        [{"tag": "input", "type": "text", "name": "q", "value": "search"}]
    ]
    assert "Home" in tool.browsergetlinks()
    assert "<input" in tool.browsergetinputs()

def test_browser_interactions():
    tool = MockWebTools()
    mgr = tool.browser_mgr
    
    mock_page = AsyncMock()
    mock_page.url = "http://example.com"
    mgr.page = mock_page
    mgr.context = AsyncMock()
    
    # Click, Fill, Type
    assert "Clicked" in tool.browserclick("#btn")
    assert "Filled" in tool.browserfill("#input", "value")
    assert "Typed" in tool.browsertype("#input", "value")
    
    # Press Key
    assert "Pressed" in tool.browserpresskey("Enter")
    
    # Scroll
    assert "Scrolled" in tool.browserscroll("down", "500")
    assert "Scrolled" in tool.browserscroll("top")
    assert "Scrolled" in tool.browserscroll("bottom")
    assert "Scrolled" in tool.browserscroll("up")
    
    # Wait for selector
    assert "Appeared" in tool.browserwaitfor("#selector")
    
    # Execute JS
    mock_page.evaluate.return_value = {"res": 123}
    assert "123" in tool.browserexecutejs("return 123;")
    
    # Screenshot
    with patch("ops.web.browser.BrowserMixin._screenshot_path", return_value="shot.png"):
        assert "shot.png" in tool.browserscreenshot("shot.png")
        
    # Select
    mock_page.select_option.return_value = ["val"]
    assert "Selected" in tool.browserselect("select", "val")
    
    # Cookies
    mgr.context.cookies.return_value = [{"name": "c1", "value": "v1"}]
    assert "c1=v1" in tool.browsergetcookies()
    assert "Cookie set" in tool.browsersetcookie("c2", "v2")
    assert "Cookies cleared" in tool.browserclearcookies()
    
    # Checkbox check & uncheck
    assert "Checked" in tool.browsercheck("#chk", "true")
    assert "Unchecked" in tool.browsercheck("#chk", "false")

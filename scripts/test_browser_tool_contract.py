import inspect
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.web.browser import BrowserMixin


def test_browser_fill_accepts_value_and_text_alias():
    signature = inspect.signature(BrowserMixin.browser_fill.__wrapped__)

    assert "value" in signature.parameters
    assert signature.parameters["value"].default == ""
    assert "text" in signature.parameters
    assert signature.parameters["text"].default == ""

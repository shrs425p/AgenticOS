# AgenticOS: Web Automation & Browser Intelligence

AgenticOS is equipped with a powerful suite of web tools, ranging from simple static scrapers to a full-featured Playwright browser automation engine. This document explains how the agent interacts with the internet and how to configure browser environments.

---

## [WEB] The Web Tool Stack

AgenticOS categorizes its web capabilities into three levels of complexity:

### Level 1: Static Web Fetching
-   **Tools**: `web_search`, `fetch_url`, `get_page_text`.
-   **Method**: Uses standard Python `requests` or `httpx`.
-   **Best For**: Reading blogs, documentation, news, and Wikipedia. It is fast and uses minimal resources.

### Level 2: Smart Extraction & APIs
-   **Tools**: `get_json_api`, `rss_feed`, `scrape_table`, `wayback_snapshot`.
-   **Method**: Specialized parsers (e.g., BeautifulSoup) to extract structured data.
-   **Best For**: Financial data, competitive research, and historical analysis.

### Level 3: Full Browser Automation (Playwright)
-   **Tools**: `browser_launch`, `browser_navigate`, `browser_click`, `browser_fill`.
-   **Method**: Headless (or headed) Chromium/Firefox/WebKit controlled by Playwright.
-   **Best For**: Logging into accounts, interacting with SPAs (Single Page Apps), taking screenshots, and bypassing complex JavaScript challenges.

---

## [BOT] Browser Automation (Playwright)

The `browser_*` tools allow the agent to "drive" a web browser just like a human.

### The Browser Lifecycle:
1.  **Launch**: `browser_launch(browser="chromium", headless="false")`.
2.  **Interact**: `browser_navigate(url)`, `browser_click(selector)`, `browser_fill(selector, text)`.
3.  **Read**: `browser_get_text()` or `browser_screenshot()`.
4.  **Close**: `browser_close()`.

### Inheriting Your Sessions (Cookies/Logins)
If you want the agent to interact with your existing accounts (e.g., GitHub, Gmail, or LinkedIn), you can provide a `user_data_dir`:
```yaml
# Internal implementation detail for the agent
args: { "user_data_dir": "C:\\Users\\shrs\\AppData\\Local\\Google\\Chrome\\User Data" }
```
*Note: This allows the agent to act as "You" on the web. Use with caution.*

---

## [LAUNCH] Smart Downloads & Resilience

Downloading files from the web can be unreliable. AgenticOS uses a "Smart Download" strategy:
1.  **Attempt 1**: `curl` (Fastest, native).
2.  **Attempt 2**: `PowerShell` (Native Windows fallback).
3.  **Attempt 3**: `Python Requests` (Cross-platform fallback).
4.  **Validation**: After downloading, the agent automatically checks the file size and mime-type to ensure the download wasn't a "404" page disguised as a file.

---

## [SEARCH] Deep Intelligence Tools

AgenticOS includes several specialized tools for web-based threat intelligence and research:

| Tool | Capability |
| :--- | :--- |
| `get_ssl_info` | Inspects a website's certificate for validity and expiration. |
| `whois_lookup` | Retrieves registration data for domains. |
| `resolve_dns` | Performs A, MX, and TXT record lookups. |
| `wayback_snapshot` | Fetches the oldest or newest version of a page from the Internet Archive. |
| `web_pick_best_link` | Searches the web and autonomously picks the most relevant URL to visit. |

---

## [SECURE] Web Safety & Privacy

To protect the user and the system, the web tools are governed by the following rules:
-   **Confirmation**: If `require_confirm_network` is true in `config.yaml`, the agent will ask before every external request.
-   **Timeout**: All web requests are hard-capped at 30 seconds to prevent the agent from hanging on a slow server.
-   **User Agent**: The agent uses a modern, standard User-Agent string to avoid being blocked by anti-bot measures.

---

## [CONFIG] Web Configuration (`config.yaml`)

```yaml
timeouts:
  web_fetch: 15
  web_search: 15
  web_download: 120 # Larger timeout for downloads

rules:
  allow_web_search: true
  allow_web_download: true
  require_confirm_network: false
```

---

## [END] Summary of Web Best Practices
1.  **Search First**: Always use `web_search` before `fetch_url` to find the most accurate URL.
2.  **Prefer Text**: Use `get_page_text` instead of `fetch_url` (raw HTML) to save model tokens.
3.  **Screenshot for Debugging**: If the agent is stuck on a dynamic page, tell it to call `browser_screenshot` so you can see what it sees.
4.  **Batch News**: Use `rss_feed` to read 10 articles at once instead of visiting 10 separate websites.

---

*Last Updated: 2026-05-13*
*Status: Web Enabled*

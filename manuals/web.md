# AgenticOS: Web Automation and Browser Intelligence

AgenticOS is equipped with a powerful suite of web ops, ranging from simple static scrapers to a full-featured Playwright browser automation engine. This document explains how the agent interacts with the internet and how to configure browser environments.

---

## The Web Tool Stack

AgenticOS categorizes its web capabilities into three levels of complexity:

### Level 1: Static Web Fetching
-   **Tools**: `websearch`, `fetchurl`, `getpagetext`.
-   **Method**: Uses standard Python `requests` or `httpx`.
-   **Best For**: Reading blogs, documentation, news, and Wikipedia. It is fast and uses minimal resources.

### Level 2: Smart Extraction and APIs
-   **Tools**: `getjsonapi`, `rssfeed`, `scrapetable`, `waybacksnapshot`.
-   **Method**: Specialized parsers (e.g., BeautifulSoup) to extract structured data.
-   **Best For**: Financial data, competitive research, and historical analysis.

### Level 3: Full Browser Automation (Playwright)
-   **Tools**: `browserlaunch`, `browsernavigate`, `browserclick`, `browserfill`.
-   **Method**: Headless (or headed) Chromium/Firefox/WebKit controlled by Playwright.
-   **Best For**: Logging into accounts, interacting with SPAs (Single Page Apps), taking screenshots, and bypassing complex JavaScript challenges.

---

## Browser Automation (Playwright)

The `browser_*` ops allow the agent to "drive" a web browser just like a human.

### The Browser Lifecycle:
1.  **Launch**: `browserlaunch(browser="chromium", headless="false")`.
2.  **Interact**: `browsernavigate(url)`, `browserclick(selector)`, `browserfill(selector, text)`.
3.  **Read**: `browsergettext()` or `browserscreenshot()`.
4.  **Close**: `browserclose()`.

### Inheriting Your Sessions (Cookies/Logins)
If you want the agent to interact with your existing accounts (e.g., GitHub, Gmail, or LinkedIn), you can provide a `user_data_dir`:
```yaml
# Internal implementation detail for the agent
args: { "user_data_dir": "<USER_PROFILE>\\AppData\\Local\\Google\\Chrome\\User Data" }
```
*Note: This allows the agent to act as "You" on the web. Use with caution.*

---

## Smart Downloads and Resilience

Downloading files from the web can be unreliable. AgenticOS uses a "Smart Download" strategy:
1.  **Attempt 1**: `curl` (Fastest, native).
2.  **Attempt 2**: `PowerShell` (Native Windows fallback).
3.  **Attempt 3**: `Python Requests` (Cross-platform fallback).
4.  **Validation**: After downloading, the agent automatically checks the file size and mime-type to ensure the download wasn't a "404" page disguised as a file.

---

## Deep Intelligence Tools

AgenticOS includes several specialized ops for web-based threat intelligence and research:

| Tool | Capability |
| :--- | :--- |
| `getsslinfo` | Inspects a website's certificate for validity and expiration. |
| `whoislookup` | Retrieves registration data for domains. |
| `resolvedns` | Performs A, MX, and TXT record lookups. |
| `waybacksnapshot` | Fetches the oldest or newest version of a page from the Internet Archive. |
| `web_pick_best_link` | Searches the web and autonomously picks the most relevant URL to visit. |

---

## Web Safety and Privacy

To protect the user and the system, the web ops are governed by the following rules:
-   **Confirmation**: If `require_confirm_network` is true in `cfg.yaml`, the agent will ask before every external request.
-   **Timeout**: All web requests are hard-capped at 30 seconds to prevent the agent from hanging on a slow server.
-   **User Agent**: The agent uses a modern, standard User-Agent string to avoid being blocked by anti-bot measures.

---

## Web Configuration (`cfg.yaml`)

```yaml
timeouts:
  web_fetch: 15
  websearch: 15
  web_download: 120 # Larger timeout for downloads

rules:
  allow_websearch: true
  allow_web_download: true
  require_confirm_network: false
```

---

## Summary of Web Best Practices
1.  **Search First**: Always use `websearch` before `fetchurl` to find the most accurate URL.
2.  **Prefer Text**: Use `getpagetext` instead of `fetchurl` (raw HTML) to save model tokens.
3.  **Screenshot for Debugging**: If the agent is stuck on a dynamic page, tell it to call `browserscreenshot` so you can see what it sees.
4.  **Batch News**: Use `rssfeed` to read 10 articles at once instead of visiting 10 separate websites.

---

*Last Updated: 2026-05-13*
*Status: Web Enabled*

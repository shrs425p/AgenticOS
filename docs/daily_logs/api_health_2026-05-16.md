# API Health Report (2026-05-16)

## 1. API Call Points Found

- `core/model_clients.py:112` - Endpoint: `<ollama_base_url>/api/tags`
- `core/model_clients.py:134` - Endpoint: `<ollama_base_url>/api/chat`
- `core/runtime.py:1158` - Endpoint: `<ollama_base_url>/api/tags`
- `core/tool_registry.py:357` - Endpoint: `<user_provided_url>`
- `tools/web/web_pick_best_link.py:40` - Endpoint: `<google_search_base_url><query>`

## 2. Validation, Timeout, Retry Analysis

### Calls missing response validation (JSON schema/parse validation missing or lacking try/except for JSON error before use):
- `core/model_clients.py:112` - Validation relies on `response.json().get("models", [])`, but no specific try/except for `json.decoder.JSONDecodeError`. Exception block is broad.
- `core/runtime.py:1158` - Similar, relies on `(resp.json() or {}).get("models", [])`.

### Calls missing timeout:
- None. All calls pass a `timeout=` kwarg.

### Calls missing retry logic:
- `core/model_clients.py:112` (Ollama list models)
- `core/model_clients.py:134` (Ollama chat)
- `core/runtime.py:1158` (Ollama listing)
- `core/tool_registry.py:357` (Web download)
- `tools/web/web_pick_best_link.py:40` (Web search)

## 3. Live Ping Results

| Endpoint | Response Time (ms) | Status Code | Reachable |
|---|---|---|---|
| http://localhost:11434/api/tags | N/A | N/A | No |
| http://localhost:11434/api/chat | N/A | N/A | No |
| https://www.google.com | 99.78 | 200 | Yes |
| http://localhost:11434/api/tags | N/A | N/A | No |
| https://www.google.com/search?q=test | 83.99 | 200 | Yes |

## 4. API Health Status

**Status: GOOD**

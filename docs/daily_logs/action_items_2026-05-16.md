# Recommended Action Items (2026-05-16)

- Implement retry logic using `tenacity` or `requests.adapters.HTTPAdapter` for:
  - `core/model_clients.py:112`
  - `core/model_clients.py:134`
  - `core/runtime.py:1158`
  - `core/tool_registry.py:357`
  - `tools/web/web_pick_best_link.py:40`
- Add explicit JSON decode error handling (e.g., `requests.exceptions.JSONDecodeError`) to `core/model_clients.py:112` and `core/runtime.py:1158`.

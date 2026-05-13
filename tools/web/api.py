"""JSON/GraphQL API helper methods for WebTools."""

from __future__ import annotations

import json

from tools.web.session import parse_headers_json, requests_module


class ApiMixin:
    def get_json_api(self, url: str, headers: str = "") -> str:
        try:
            r = requests_module()
            timeout = self._get_timeout("web_api", 20)
            resp = r.get(url, headers=parse_headers_json(headers), timeout=timeout)
            return json.dumps(resp.json(), indent=2)
        except Exception as e:
            return f"API error: {e}"

    def post_json_api(self, url: str, body: str, headers: str = "") -> str:
        try:
            payload = json.loads(body) if body else {}
            r = requests_module()
            timeout = self._get_timeout("web_api", 20)
            resp = r.post(
                url, json=payload, headers=parse_headers_json(headers), timeout=timeout
            )
            try:
                return json.dumps(resp.json(), indent=2)
            except Exception:
                return resp.text
        except Exception as e:
            return f"API error: {e}"

    def put_json_api(self, url: str, body: str, headers: str = "") -> str:
        try:
            payload = json.loads(body) if body else {}
            r = requests_module()
            timeout = self._get_timeout("web_api", 20)
            resp = r.put(
                url, json=payload, headers=parse_headers_json(headers), timeout=timeout
            )
            try:
                return json.dumps(resp.json(), indent=2)
            except Exception:
                return resp.text
        except Exception as e:
            return f"API error: {e}"

    def delete_api(self, url: str, headers: str = "") -> str:
        try:
            r = requests_module()
            timeout = self._get_timeout("web_api", 20)
            resp = r.delete(url, headers=parse_headers_json(headers), timeout=timeout)
            try:
                return json.dumps(resp.json(), indent=2)
            except Exception:
                return resp.text
        except Exception as e:
            return f"API error: {e}"

    def graphql_query(self, url: str, query: str, variables: str = "") -> str:
        try:
            payload = {
                "query": query,
                "variables": json.loads(variables) if variables else {},
            }
            r = requests_module()
            timeout = self._get_timeout("web_graphql", 25)
            resp = r.post(url, json=payload, timeout=timeout)
            return json.dumps(resp.json(), indent=2)
        except Exception as e:
            return f"GraphQL error: {e}"

"""JSON/GraphQL API helper methods for WebTools."""

from __future__ import annotations

import json

from tools.web.session import parse_headers_json, requests_module


from core.tool_base import tool
class ApiMixin:
    @tool(name="get_json_api", desc="GET a JSON API. Args: url, headers (optional JSON)", category="Web")
    def get_json_api(self, url: str, headers: str = "") -> str:
        """get_json_api function."""
        err = self._network_error()
        if err:
            return err
        try:
            r = requests_module()
            timeout = self._get_timeout("web_api", 20)
            resp = r.get(url, headers=parse_headers_json(headers), timeout=timeout)
            return json.dumps(resp.json(), indent=2)
        except Exception as e:
            return f"API error: {e}"

    @tool(name="post_json_api", desc="POST JSON to API. Args: url, body (JSON), headers (optional)", category="Web")
    def post_json_api(self, url: str, body: str, headers: str = "") -> str:
        """post_json_api function."""
        err = self._network_error()
        if err:
            return err
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

    @tool(name="put_json_api", desc="PUT JSON to API. Args: url, body (JSON), headers (optional)", category="Web")
    def put_json_api(self, url: str, body: str, headers: str = "") -> str:
        """put_json_api function."""
        err = self._network_error()
        if err:
            return err
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

    @tool(name="delete_api", desc="DELETE request. Args: url, headers (optional)", category="Web")
    def delete_api(self, url: str, headers: str = "") -> str:
        """delete_api function."""
        err = self._network_error()
        if err:
            return err
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

    @tool(name="graphql_query", desc="GraphQL query. Args: url, query, variables (optional)", category="Web")
    def graphql_query(self, url: str, query: str, variables: str = "") -> str:
        """graphql_query function."""
        err = self._network_error()
        if err:
            return err
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

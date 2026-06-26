"""JSON/GraphQL API helper methods for WebTools."""

from __future__ import annotations

import json

from ops.web.session import parse_headers_json, requests_module


from kernel.base import tool
class ApiMixin:
    @tool(name="getjsonapi", desc="GET a JSON API. Args: url, headers (optional JSON)", category="Web")
    def getjsonapi(self, url: str, headers: str = "") -> str:
        """getjsonapi function."""
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

    @tool(name="postjsonapi", desc="POST JSON to API. Args: url, body (JSON), headers (optional)", category="Web")
    def postjsonapi(self, url: str, body: str, headers: str = "") -> str:
        """postjsonapi function."""
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

    @tool(name="putjsonapi", desc="PUT JSON to API. Args: url, body (JSON), headers (optional)", category="Web")
    def putjsonapi(self, url: str, body: str, headers: str = "") -> str:
        """putjsonapi function."""
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

    @tool(name="deleteapi", desc="DELETE request. Args: url, headers (optional)", category="Web")
    def deleteapi(self, url: str, headers: str = "") -> str:
        """deleteapi function."""
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

    @tool(name="graphqlquery", desc="GraphQL query. Args: url, query, variables (optional)", category="Web")
    def graphqlquery(self, url: str, query: str, variables: str = "") -> str:
        """graphqlquery function."""
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

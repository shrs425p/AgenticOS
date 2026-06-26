"""Inspection methods (headers, SSL, whois, DNS, IP helpers) for WebTools."""

from __future__ import annotations

import json
import socket
import ssl

from ops.web.session import requests_module


from kernel.base import tool
class InspectMixin:
    @tool(name="checkurl", desc="Check if URL is reachable. Args: url", category="Web")
    def checkurl(self, url: str) -> str:
        """checkurl function."""
        err = self._network_error()
        if err:
            return err
        try:
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 15)
            resp = r.get(url, timeout=timeout, allow_redirects=True)
            return f"Status: {resp.status_code}\nFinal URL: {resp.url}"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="httpheaders", desc="Get HTTP headers. Args: url", category="Web")
    def httpheaders(self, url: str) -> str:
        """httpheaders function."""
        err = self._network_error()
        if err:
            return err
        try:
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 15)
            resp = r.head(url, timeout=timeout, allow_redirects=True)
            headers = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
            return headers or "(no headers)"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="getsslinfo", desc="Get SSL certificate info. Args: hostname", category="Web")
    def getsslinfo(self, hostname: str) -> str:
        """getsslinfo function."""
        err = self._network_error()
        if err:
            return err
        try:
            ctx = ssl.create_default_context()
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2  # DevSkim: ignore


            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:

                    cert = ssock.getpeercert()
            return json.dumps(cert, indent=2, default=str)
        except Exception as e:
            return f"SSL error: {e}"

    @tool(name="whoislookup", desc="WHOIS lookup. Args: domain", category="Web")
    def whoislookup(self, domain: str) -> str:
        """whoislookup function."""
        err = self._network_error()
        if err:
            return err
        try:
            import whois

            info = whois.whois(domain)
            return str(info)
        except Exception as e:
            return f"WHOIS error: {e}"

    @tool(name="resolvedns", desc="DNS lookup. Args: hostname, record_type (optional)", category="Web")
    def resolvedns(self, hostname: str, record_type: str = "A") -> str:
        """resolvedns function."""
        err = self._network_error()
        if err:
            return err
        rt = (record_type or "A").upper().strip()
        try:
            if rt != "A":
                return "Only A-record lookup is supported in this lightweight resolver."
            return socket.gethostbyname(hostname)
        except Exception as e:
            return f"DNS error: {e}"

    @tool(name="getpublicip", desc="Get public IP of this machine.", category="Web")
    def getpublicip(self) -> str:
        """getpublicip function."""
        err = self._network_error()
        if err:
            return err
        try:
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 10)
            api = self.cfg.get("endpoints", {}).get("ipify_api", "https://api.ipify.org")
            resp = r.get(f"{api}?format=json", timeout=timeout)
            return resp.text
        except Exception as e:
            return f"IP error: {e}"

    @tool(name="getipinfo", desc="Get IP geolocation. Args: ip (optional)", category="Web")
    def getipinfo(self, ip: str = "") -> str:
        """getipinfo function."""
        err = self._network_error()
        if err:
            return err
        try:
            target = ip.strip()
            if not target:
                raw = self.getpublicip()
                try:
                    target = json.loads(raw).get("ip", "")
                except Exception:
                    target = ""
            if not target:
                return "Error: Could not determine IP."
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 15)
            api_base = self.cfg.get("endpoints", {}).get("ipinfo_api", "https://ipinfo.io")
            resp = r.get(f"{api_base}/{target}/json", timeout=timeout)
            return resp.text
        except Exception as e:
            return f"IP info error: {e}"

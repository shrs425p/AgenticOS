"""Inspection methods (headers, SSL, whois, DNS, IP helpers) for WebTools."""

from __future__ import annotations

import json
import socket
import ssl

from tools.web.session import requests_module


class InspectMixin:
    def check_url(self, url: str) -> str:
        try:
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 15)
            resp = r.get(url, timeout=timeout, allow_redirects=True)
            return f"Status: {resp.status_code}\nFinal URL: {resp.url}"
        except Exception as e:
            return f"Error: {e}"

    def http_headers(self, url: str) -> str:
        try:
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 15)
            resp = r.head(url, timeout=timeout, allow_redirects=True)
            headers = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
            return headers or "(no headers)"
        except Exception as e:
            return f"Error: {e}"

    def get_ssl_info(self, hostname: str) -> str:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
            return json.dumps(cert, indent=2, default=str)
        except Exception as e:
            return f"SSL error: {e}"

    def whois_lookup(self, domain: str) -> str:
        try:
            import whois

            info = whois.whois(domain)
            return str(info)
        except Exception as e:
            return f"WHOIS error: {e}"

    def resolve_dns(self, hostname: str, record_type: str = "A") -> str:
        rt = (record_type or "A").upper().strip()
        try:
            if rt != "A":
                return "Only A-record lookup is supported in this lightweight resolver."
            return socket.gethostbyname(hostname)
        except Exception as e:
            return f"DNS error: {e}"

    def get_public_ip(self) -> str:
        try:
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 10)
            resp = r.get("https://api.ipify.org?format=json", timeout=timeout)
            return resp.text
        except Exception as e:
            return f"IP error: {e}"

    def get_ip_info(self, ip: str = "") -> str:
        try:
            target = ip.strip()
            if not target:
                raw = self.get_public_ip()
                try:
                    target = json.loads(raw).get("ip", "")
                except Exception:
                    target = ""
            if not target:
                return "Error: Could not determine IP."
            r = requests_module()
            timeout = self._get_timeout("web_inspect", 15)
            resp = r.get(f"https://ipinfo.io/{target}/json", timeout=timeout)
            return resp.text
        except Exception as e:
            return f"IP info error: {e}"

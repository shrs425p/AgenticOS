"""Tests for the urlsafetycheck plugin."""
from unittest.mock import MagicMock, patch
import datetime
from ops.addons.urlsafe import (
    _parse_whois_creation_year,
    urlsafetycheck,
)


def test_parse_whois_creation_year_valid():
    """Verify registration year extraction from raw WHOIS logs."""
    raw_payload = (
        "Domain Name: google.com\n"
        "Registry Domain ID: 2138514_DOMAIN_COM-VRSN\n"
        "Creation Date: 1997-09-15T04:00:00Z\n"
        "Updated Date: 2019-09-09T15:39:04Z\n"
    )
    year = _parse_whois_creation_year(raw_payload)
    assert year == 1997


def test_parse_whois_creation_year_invalid():
    """Verify parsing fallback when no registration date is returned."""
    raw_payload = "No Match for google.com"
    year = _parse_whois_creation_year(raw_payload)
    assert year == 0


@patch("ops.addons.urlsafe._get_raw_whois")
@patch("ssl.create_default_context")
def test_urlsafetycheck_secure_and_old(mock_ssl_context, mock_whois):
    """Test safe host with active SSL and old established domain registration."""
    # 1. Mock WHOIS registration date to 2010 (established domain)
    mock_whois.return_value = "Creation Date: 2010-05-15T00:00:00Z"

    # 2. Mock SSL context to simulate valid active cert
    mock_context = MagicMock()
    mock_socket = MagicMock()
    mock_context.wrap_socket.return_value = mock_socket

    # Mock peer cert returning expiration date in the future
    future_year = datetime.datetime.now().year + 1
    mock_socket.getpeercert.return_value = {
        "notAfter": f"May 15 00:00:00 {future_year} GMT"
    }
    mock_ssl_context.return_value = mock_context

    result = urlsafetycheck("https://secure-domain.com")

    assert "Core Heuristics Check" in result
    assert "SSL Certificate Status**: Valid" in result
    assert "Domain Registration Year: 2010" in result
    assert "Final Risk Skernel**: `0 / 10`" in result
    assert "SECURE & SAFE" in result


@patch("ops.addons.urlsafe._get_raw_whois")
def test_urlsafetycheck_insecure_http_new_domain(mock_whois):
    """Test unsafe host using insecure HTTP and fresh domain registration."""
    # Mock WHOIS registration to current year (fresh/suspicious domain)
    current_year = datetime.datetime.now().year
    mock_whois.return_value = f"Creation Date: {current_year}-01-01T00:00:00Z"

    result = urlsafetycheck("http://insecure-fresh-domain-highly-complex-redirect-phishing-url.com")

    # Should flag protocol (HTTP) and new registration age
    assert "Insecure Protocol: URL uses unencrypted HTTP instead of HTTPS" in result
    assert "Fresh/New Domain Registration" in result
    assert "Final Risk Skernel" in result
    assert int(result.split("Final Risk Skernel**: `")[1].split(" / 10`")[0]) >= 5

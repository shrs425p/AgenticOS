"""Plugin module for validating URL safety, SSL certificates, and domain registration age."""
import datetime
import socket
import ssl
from urllib.parse import urlparse
from core.tool_registry import tool


def _get_raw_whois(domain: str) -> str:
    """Connects directly to IANA/Verisign WHOIS servers via raw socket on Port 43."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(("whois.verisign-grs.com", 43))
        # Verisign expects "domain <domain>\r\n" or just "<domain>\r\n"
        s.sendall(f"domain {domain}\r\n".encode("utf-8"))

        response = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            response.append(data.decode("utf-8", errors="ignore"))
        s.close()
        return "".join(response)
    except Exception:
        # Fallback to root registrar query if Verisign times out or is invalid for TLD
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect(("whois.iana.org", 43))
            s.sendall(f"{domain}\r\n".encode("utf-8"))
            response = []
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response.append(data.decode("utf-8", errors="ignore"))
            s.close()
            return "".join(response)
        except Exception:
            return ""


def _parse_whois_creation_year(raw_data: str) -> int:
    """Extracts the creation/registration year from raw WHOIS payload."""
    if not raw_data:
        return 0
    for line in raw_data.splitlines():
        line_lower = line.lower()
        if "creation date" in line_lower or "created" in line_lower or "registered" in line_lower:
            parts = line.split(":")
            if len(parts) >= 2:
                date_str = parts[1].strip()
                # Extract the 4-digit year
                for token in date_str.replace("-", " ").replace("/", " ").split():
                    if token.isdigit() and len(token) == 4:
                        return int(token)
    return 0


@tool(name="url_safety_check", category="Security")
def url_safety_check(url: str) -> str:
    """Performs a comprehensive security and cryptographic audit of a URL.

    Checks SSL certificate validity, registers WHOIS age, runs domain heuristics,
    and returns a risk score (0 to 10) with a detailed assessment report.

    Args:
        url (str): The absolute URL (including protocol, e.g., https://example.com) to analyze.

    Returns:
        str: A detailed markdown report containing the security analysis and threat scores.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        return "Error: Invalid URL. Could not parse hostname."

    report = [
        f"# Security & Threat Audit: {hostname}",
        "",
        "## Core Heuristics Check",
        ""
    ]

    risk_score = 0
    reasons = []

    # Heuristic 1: Protocol Check
    if parsed.scheme != "https":
        risk_score += 3
        reasons.append("Insecure Protocol: URL uses unencrypted HTTP instead of HTTPS.")
        report.append("- [X] **Protocol Security**: Insecure (HTTP) [+3 Risk]")
    else:
        report.append("- [ ] **Protocol Security**: Secure (HTTPS)")

    # Heuristic 2: Suspicious Domain Length & Structure
    if len(hostname) > 50:
        risk_score += 2
        reasons.append("Suspicious Hostname Length: Domain name is unusually long.")
        report.append("- [X] **Domain Complexity**: Long Hostname (>50 characters) [+2 Risk]")
    else:
        report.append("- [ ] **Domain Complexity**: Normal Hostname Length")

    # Heuristic 3: Subdomain Count
    subdomains = hostname.split(".")
    if len(subdomains) > 4:
        risk_score += 2
        reasons.append("Excessive Subdomains: Might indicate a phishing redirect layer.")
        report.append(f"- [X] **Subdomain Sprawl**: Found {len(subdomains)} subdomains [+2 Risk]")
    else:
        report.append("- [ ] **Subdomain Sprawl**: Low Subdomain Count")

    # 2. Cryptographic Peer SSL Handshake Audit
    report.append("\n## Cryptographic SSL Peer Verification\n")
    ssl_ok = False
    cert_expired = False
    days_to_expire = 0

    if parsed.scheme == "https":
        try:
            context = ssl.create_default_context()
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            conn = context.wrap_socket(
                socket.socket(socket.AF_INET),
                server_hostname=hostname,
            )
            conn.settimeout(5.0)
            conn.connect((hostname, 443))
            cert = conn.getpeercert()
            conn.close()

            # Parse expiration date from peer cert
            not_after_str = cert.get("notAfter")
            if not_after_str:
                exp_date = datetime.datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                days_to_expire = (exp_date - now).days
                if days_to_expire < 0:
                    cert_expired = True
                ssl_ok = True
        except Exception as e:
            reasons.append(f"SSL Handshake Failure: {str(e)}")

    if parsed.scheme == "https" and not ssl_ok:
        risk_score += 4
        report.append("- [X] **SSL Certificate Validation**: Failed handshake or invalid peer [+4 Risk]")
    elif cert_expired:
        risk_score += 5
        report.append("- [X] **SSL Certificate Lifespan**: Expired SSL Certificate [+5 Risk]")
    elif parsed.scheme == "https" and ssl_ok:
        report.append(f"- [ ] **SSL Certificate Status**: Valid (Active for next {days_to_expire} days)")
    else:
        report.append("- [-] **SSL Certificate Status**: Bypassed (Non-HTTPS protocol)")

    # 3. WHOIS Registration Age Audit
    report.append("\n## Registration Age (WHOIS Lookup)\n")
    raw_whois = _get_raw_whois(hostname)
    creation_year = _parse_whois_creation_year(raw_whois)

    current_year = datetime.datetime.now().year
    if creation_year > 0:
        age = current_year - creation_year
        report.append(f"- Domain Registration Year: {creation_year} (~{age} years old)")
        if age <= 1:
            risk_score += 2
            reasons.append("Freshly Registered: Domain registration is less than 1 year old.")
            report.append("- [X] **Domain Lifecycle**: Fresh/New Domain Registration [+2 Risk]")
        else:
            report.append("- [ ] **Domain Lifecycle**: Established Domain")
    else:
        report.append("- WHOIS Registry Query: No creation date returned or domain not registered under monitored servers.")

    # Bound risk score between 0 and 10
    risk_score = min(max(risk_score, 0), 10)

    # 4. Threat Matrix & Final Risk Summary
    report.append("\n## Threat Matrix Summary\n")
    report.append(f"**Final Risk Score**: `{risk_score} / 10`")

    if risk_score >= 7:
        report.append("\n> [!CAUTION]")
        report.append("> HIGH THREAT DETECTED. Do not transmit credentials or high-value payloads to this destination.")
    elif risk_score >= 4:
        report.append("\n> [!WARNING]")
        report.append("> MODERATE SUSPICION. Exercise caution when performing operations against this host.")
    else:
        report.append("\n> [!NOTE]")
        report.append("> SECURE & SAFE. The tested destination domain appears highly trustworthy.")

    if reasons:
        report.append("\n### Identified Risk Factors:")
        for r in reasons:
            report.append(f"- {r}")

    return "\n".join(report)

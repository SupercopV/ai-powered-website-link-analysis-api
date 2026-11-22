import ipaddress
import re
import socket
from urllib.parse import urlparse
from typing import Tuple, List


class InvalidURLError(Exception):
    """Raised when a URL is structurally invalid or uses an unsupported scheme."""
    pass


class SSRFProtectionError(Exception):
    """Raised when a URL targets a private, loopback, or restricted internal network address."""
    pass


class WebsiteInaccessibleError(Exception):
    """Raised when a website cannot be reached, times out, or fails DNS resolution."""
    pass


class InsufficientBusinessContentError(Exception):
    """Raised when a website lacks substantive commercial, product, or business content."""
    pass


# Disallowed hostnames and domains
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}

BLOCKED_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
    ".lan",
    ".localdomain",
    ".home.arpa",
)

# Additional restricted CIDR blocks (RFC 6598, RFC 2544, etc.)
RESTRICTED_NETWORKS = [
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-Grade NAT (RFC 6598)
    ipaddress.ip_network("198.18.0.0/15"),     # Benchmarking (RFC 2544)
    ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),      # TEST-NET-1 (RFC 5737)
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2 (RFC 5737)
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3 (RFC 5737)
]


def is_ip_restricted(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """
    Check if an IP address belongs to private, loopback, link-local, multicast,
    reserved, unspecified, or restricted network ranges.
    """
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    # Check additional restricted CIDR networks
    for net in RESTRICTED_NETWORKS:
        if ip in net:
            return True

    return False


def validate_and_sanitize_url(url: str) -> str:
    """
    Validate that the provided string is a valid HTTP/HTTPS URL and does not target
    internal, loopback, or private network addresses (SSRF Protection).

    Returns:
        The normalized URL string if valid.

    Raises:
        InvalidURLError: If the URL is empty, malformed, or has an unsupported scheme.
        SSRFProtectionError: If the URL resolves to a restricted/private network address.
        WebsiteInaccessibleError: If DNS resolution fails.
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL must be a non-empty string.")

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise InvalidURLError(f"Malformed URL: {exc}")

    # Enforce HTTP or HTTPS
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidURLError(f"Unsupported URL scheme '{parsed.scheme}'. Only 'http' and 'https' are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLError("URL must contain a valid domain name or public host.")

    hostname_lower = hostname.lower()

    # Block well-known private/internal hostnames
    if hostname_lower in BLOCKED_HOSTNAMES:
        raise SSRFProtectionError(f"Access to '{hostname}' is blocked for security (internal hostname).")

    for suffix in BLOCKED_SUFFIXES:
        if hostname_lower.endswith(suffix):
            raise SSRFProtectionError(f"Access to host '{hostname}' ending in '{suffix}' is blocked (SSRF protection).")

    # If hostname is an IP address literal, validate immediately
    # Handle stripped brackets for IPv6 literals
    clean_host = hostname_lower.strip("[]")
    try:
        ip = ipaddress.ip_address(clean_host)
        if is_ip_restricted(ip):
            raise SSRFProtectionError(
                f"Access to IP address '{ip}' is blocked (private/loopback/restricted address)."
            )
        return url
    except ValueError:
        # Not a raw IP literal, proceed to DNS resolution
        pass

    # Resolve domain via DNS and verify all resolved IP addresses
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(hostname, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise WebsiteInaccessibleError(f"Could not resolve host '{hostname}': {e.strerror or 'DNS lookup failed'}")
    except Exception as e:
        raise WebsiteInaccessibleError(f"DNS resolution error for host '{hostname}': {str(e)}")

    if not addr_info:
        raise WebsiteInaccessibleError(f"Could not resolve host '{hostname}' to any IP address.")

    resolved_ips: List[str] = []
    for item in addr_info:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        resolved_ips.append(ip_str)
        try:
            ip = ipaddress.ip_address(ip_str)
            if is_ip_restricted(ip):
                raise SSRFProtectionError(
                    f"Domain '{hostname}' resolved to restricted IP address '{ip_str}' (SSRF protection)."
                )
        except ValueError:
            raise SSRFProtectionError(f"Invalid resolved IP '{ip_str}' for host '{hostname}'.")

    return url

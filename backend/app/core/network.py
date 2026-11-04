"""Who is calling: the client's IP, also behind reverse proxies."""

import ipaddress

from fastapi import Request

from app.core.config import get_settings

UNKNOWN_IP = "unknown"


def client_ip(request: Request) -> str:
    """The caller's IP, for rate limiting and audit records.

    Behind proxies the socket peer is the proxy and the real IP is in
    X-Forwarded-For. Anyone can send that header with invented values, and each
    proxy APPENDS the address it saw, so only the rightmost entries are
    trustworthy. TRUSTED_PROXY_HOPS says how many proxies are ours: we read that
    position from the right and ignore whatever the client wrote to its left.
    """
    peer = request.client.host if request.client else UNKNOWN_IP

    hops = get_settings().trusted_proxy_hops
    if hops == 0:
        return peer

    header = ",".join(request.headers.getlist("x-forwarded-for"))
    entries = [entry.strip() for entry in header.split(",") if entry.strip()]
    if len(entries) < hops:
        return peer
    candidate = entries[-hops]
    try:
        # Normalizes the value and keeps arbitrary text out of logs and the DB.
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return peer

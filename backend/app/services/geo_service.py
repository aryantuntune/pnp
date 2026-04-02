import logging

import httpx

logger = logging.getLogger("ssmspl")

_PRIVATE_PREFIXES = ("127.", "10.", "172.", "192.168.", "0.", "::1", "fd", "fe80")


async def resolve_city(ip: str | None) -> str | None:
    """Resolve an IP address to a city name via ip-api.com.

    Returns None on error, timeout, or private/localhost IPs.
    Free tier: 45 requests/minute — more than enough for login events.
    """
    if not ip:
        return None

    # Skip private/loopback IPs
    if any(ip.startswith(p) for p in _PRIVATE_PREFIXES):
        return None

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,city,regionName,country"},
            )
            if resp.status_code != 200:
                logger.debug("Geo lookup failed for %s: HTTP %s", ip, resp.status_code)
                return None
            data = resp.json()
            if data.get("status") != "success":
                return None
            parts = [data.get("city"), data.get("regionName"), data.get("country")]
            return ", ".join(p for p in parts if p) or None
    except Exception as exc:
        logger.debug("Geo lookup failed for %s: %s", ip, exc)
        return None

import logging

import httpx

logger = logging.getLogger("ssmspl")

_PRIVATE_PREFIXES = ("127.", "10.", "172.", "192.168.", "0.", "::1", "fd", "fe80")


async def resolve_geo(ip: str | None) -> dict:
    """Resolve an IP address to location data via ip-api.com.

    Returns a dict with keys: city_display, latitude, longitude, isp.
    Returns empty dict on error, timeout, or private/localhost IPs.
    Free tier: 45 requests/minute — more than enough for login events.
    """
    if not ip:
        return {}

    # Skip private/loopback IPs
    if any(ip.startswith(p) for p in _PRIVATE_PREFIXES):
        return {}

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,city,regionName,country,lat,lon,isp"},
            )
            if resp.status_code != 200:
                logger.debug("Geo lookup failed for %s: HTTP %s", ip, resp.status_code)
                return {}
            data = resp.json()
            if data.get("status") != "success":
                return {}
            parts = [data.get("city"), data.get("regionName"), data.get("country")]
            city_display = ", ".join(p for p in parts if p) or None
            return {
                "city_display": city_display,
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "isp": data.get("isp"),
            }
    except Exception as exc:
        logger.debug("Geo lookup failed for %s: %s", ip, exc)
        return {}


# Backward-compatible alias
async def resolve_city(ip: str | None) -> str | None:
    """Resolve an IP to 'City, Region, Country' string. Legacy wrapper."""
    geo = await resolve_geo(ip)
    return geo.get("city_display")

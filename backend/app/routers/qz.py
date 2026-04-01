"""
QZ Tray signing endpoint.
Signs messages with the SSMSPL private key so QZ Tray trusts our certificate.
The private key never leaves the server — browsers call this endpoint instead.
"""
import base64

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from app.dependencies import get_current_user

router = APIRouter(prefix="/api/qz", tags=["QZ Tray"])

# ── SSMSPL signing key ──
# Matches the ssmspl-qz.crt certificate embedded in the frontend qz-service.ts.
# The corresponding .crt must be imported into QZ Tray Site Manager once per machine
# (or auto-imported via tools/setup-direct-printing.bat).
_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDdA4z8N++ca9Xp
EYHPkhc6SfOa8+qYYMMxHp8L22B19AOe5WOya470Pk/dXVUYd4i6zZE+Yf87wZVj
cPEMXFeLI++yWmtjOeG2ka6UcMvpM6ALCs9bcmYHcaYfg/NkEt+5DeW3jYBj/Vin
pM95bklHptV9BhgNvklqB9L7fbNI2vaOrcdirL5w75lAxn7cwT3LWHT0sETYM60A
yAPadVg2KeZNcV9Ansjc9YYGdeLb14zCYrD5KG/cfh3mlzBKv4BkH3ca1+hKnaKq
3cb6lN18Yc1W8t3Weo5dkYx/xrp6E0EeRopkDnnCcGvP1JvRQd0KelatUmN/cra6
UnaUk1jVAgMBAAECggEAG6kvWry8dCkJ5WjfxIUN+6lYQAcxj/8iRtJEiRUcgj63
OkqO2vx7sIVg9P1SomSJfAmw2SwmJ8ovYnn27TtcaIlnnTyUTp+mqHUcsq7YUng3
2lHwyErtypY2eqDG1DpJfk1nN/0RedIyJ48ouVOsf7d5ZjOeTJAJe6f9h6TAjMhB
Hs14ow8vUyL6DBX+51A5+6t+GNj0JPUeiFwjuZpphOcza5JIAt/kgOgMG1qW7urP
WQ5ojubFVYxChlndZjA1qXquwXE61Jz65Toc2XMDH3xVDKcD8CBzcZUnavbmpskx
CSera14U+b8pcd/McsLa2oHR3VZvoqpSTLl1TtCYwQKBgQD++G2dASLRPQOedIVB
Z3whfSyudIugEvIUBcQjFzwHDHDJkdavkd5fCHOlqPU2CHn2cmpjIRYGvDNKFUDb
/u8MC2gEcR/47tg/dSiioEQWAIcltof2aG9/0NpH8nv19e/SDju5wM6VF04mnHSa
n9H/A/UoqGGIjM3CA7is0TYSFQKBgQDd6AU9vRgGnTXXqwGL8ag6L23RNf39N6LZ
6GJ3yOhmGn47Abqcy43094w+8AAtsAj1TJ1UEZlaBJTzfk3PBhPr7uaVr4AzB1nx
jnSmZioXTE4+UkVqttqfgASNyuJ8/Y3Ma13rbF910ANbkevF1/gZeJVB5VCUgGXl
MTRz9qmbwQKBgQCY6FWcTd0ajLPJ6Gkt8yjPUKlmKkC+C/6foWGiBcIbHAvb5plQ
i3NHnOL2G2CLOgQilzVUI7h46476w8o05StpFsIXv9wDxwFq9REcjm6mn0Rtioz5
amJLze3KLhLHS+m6GI0a9hUt9l8I6tVHEce3XyE8c9aiNIcE7oRnJ8R8jQKBgGjj
H38UHwQZUPbUtJFyMwL1oiGuNJR4tLfs+IYH55lDUoEPiyZLrJiqXZbuGBeASmuv
v/mZq/N5kPIatCpzg/0T2dfMsXrtMZ1UqVxxk9mZTq50cq1DKskTWJOw3ycXLev+
n9EEU4a7QKsKqPfF4lYfweT4wALBQeh4PoPFhlvBAoGAYNLiF6VvIjBkYsx4zAOM
Nj2JCC8mzSqUZ5Bvr2RlLvJrlsxTHbc87aFJLHJLpQIY66GCN0PNStLcIyk5G9cy
axQE1HXY8iI7MtuO1FzGxA4vd6uxVmNj9zb/PWl5Y1h80y0N9zLiFcGBYxgLJqEw
/xjroPVOHqdudhyYDUWgebk=
-----END PRIVATE KEY-----"""

# Cache the imported key object (RSA.import_key is not expensive but avoid repeating)
_rsa_key: RSA.RsaKey | None = None


def _get_rsa_key() -> RSA.RsaKey:
    global _rsa_key
    if _rsa_key is None:
        _rsa_key = RSA.import_key(_PRIVATE_KEY_PEM)
    return _rsa_key


class SignRequest(BaseModel):
    message: str


@router.post("/sign", summary="Sign a QZ Tray challenge message")
async def qz_sign(
    body: SignRequest,
    _current_user=Depends(get_current_user),
):
    """
    Signs the QZ Tray challenge string with the SSMSPL private key.
    Called by the frontend during QZ Tray connection — requires auth so
    only logged-in staff can trigger silent printing.
    """
    try:
        key = _get_rsa_key()
        h = SHA.new(body.message.encode("utf-8"))
        sig = pkcs1_15.new(key).sign(h)
        return {"signature": base64.b64encode(sig).decode("ascii")}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signing failed",
        )

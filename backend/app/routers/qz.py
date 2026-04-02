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

from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/qz", tags=["QZ Tray"])

_rsa_key: RSA.RsaKey | None = None


def _get_rsa_key() -> RSA.RsaKey:
    global _rsa_key
    if _rsa_key is None:
        pem = settings.QZ_PRIVATE_KEY_PEM
        if not pem:
            raise RuntimeError("QZ_PRIVATE_KEY_PEM is not configured")
        _rsa_key = RSA.import_key(pem)
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

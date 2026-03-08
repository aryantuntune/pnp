"""
SabPaisa payment gateway — hosted checkout via AES-128-CBC encrypted form POST.

Official docs: https://developer.sabpaisa.in/docs/python/

Flow:
  1. build_payment_request() → encrypts key=value payload, returns form data for POST
  2. Frontend POSTs form with encData + clientCode to SabPaisa checkout URL
  3. SabPaisa POSTs back to callback with encResponse parameter
  4. decrypt_callback() → decrypts key=value response, returns parsed dict
"""

import logging
import time
import uuid
from datetime import datetime
from urllib.parse import quote

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from app.config import settings

logger = logging.getLogger("ssmspl.sabpaisa")


def is_configured() -> bool:
    return bool(
        settings.SABPAISA_CLIENT_CODE
        and settings.SABPAISA_AUTH_KEY
        and settings.SABPAISA_AUTH_IV
    )


def _get_cipher():
    key = settings.SABPAISA_AUTH_KEY.encode("utf-8")
    iv = settings.SABPAISA_AUTH_IV.encode("utf-8")
    # Pad/truncate to exactly 16 bytes for AES-128
    key = key[:16].ljust(16, b"\0")
    iv = iv[:16].ljust(16, b"\0")
    return AES.new(key, AES.MODE_CBC, iv)


def _encrypt(plaintext: str) -> str:
    """AES-128-CBC encrypt, PKCS7 pad, return UPPERCASE HEX string."""
    cipher = _get_cipher()
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return encrypted.hex().upper()


def _decrypt(hex_string: str) -> str:
    """Decode hex, AES-128-CBC decrypt, PKCS7 unpad."""
    cipher = _get_cipher()
    decoded = bytes.fromhex(hex_string)
    decrypted = unpad(cipher.decrypt(decoded), AES.block_size)
    return decrypted.decode("utf-8")


def generate_client_txn_id(booking_id: int) -> str:
    return f"SSMSPL_{booking_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"


def build_payment_request(
    *,
    client_txn_id: str,
    amount: float,
    payer_name: str,
    payer_email: str,
    payer_mobile: str,
    callback_url: str,
    channel_id: str = "W",  # W=web, M=mobile
) -> dict:
    """
    Build encrypted payment request for SabPaisa hosted checkout.

    Returns dict with:
      - sabpaisa_url: the SabPaisa checkout form POST URL
      - enc_data: encrypted payload (hex string)
      - client_code: to be sent as separate form field
      - client_txn_id: for tracking
    """
    if not is_configured():
        raise RuntimeError("SabPaisa not configured")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build key=value& payload per SabPaisa spec
    plaintext = (
        f"payerName={payer_name.strip()}"
        f"&payerEmail={payer_email.strip()}"
        f"&payerMobile={payer_mobile.strip()}"
        f"&clientTxnId={client_txn_id.strip()}"
        f"&amount={amount:.2f}"
        f"&clientCode={settings.SABPAISA_CLIENT_CODE.strip()}"
        f"&transUserName={settings.SABPAISA_USERNAME.strip()}"
        f"&transUserPassword={settings.SABPAISA_PASSWORD.strip()}"
        f"&callbackUrl={callback_url.strip()}"
        f"&channelId={channel_id}"
        f"&transDate={now}"
    )

    enc_data = _encrypt(plaintext)

    # SabPaisa URL with version param
    base = settings.SABPAISA_BASE_URL.rstrip("/")
    sabpaisa_url = f"{base}/SabPaisa/sabPaisaInit?v=1"

    return {
        "sabpaisa_url": sabpaisa_url,
        "enc_data": enc_data,
        "client_code": settings.SABPAISA_CLIENT_CODE,
        "client_txn_id": client_txn_id,
    }


def decrypt_callback(enc_response: str) -> dict:
    """
    Decrypt SabPaisa callback response.

    SabPaisa POSTs back with `encResponse` parameter containing hex-encoded
    encrypted string. Decrypted format is key=value& pairs.

    Returns dict with all parsed fields.
    """
    try:
        decrypted = _decrypt(enc_response)
    except Exception as e:
        logger.error("Failed to decrypt SabPaisa callback: %s", e)
        return {"status_code": "DECRYPT_ERROR", "error": str(e)}

    logger.info("SabPaisa callback decrypted successfully")

    # Parse key=value& pairs
    result = {}
    for pair in decrypted.split("&"):
        if "=" in pair:
            key, _, value = pair.partition("=")
            result[key.strip()] = value.strip()

    # Normalize key names for our internal use
    return {
        "client_txn_id": result.get("clientTxnId", ""),
        "status": result.get("status", ""),
        "status_code": result.get("statusCode", ""),
        "amount": result.get("amount", ""),
        "paid_amount": result.get("paidAmount", ""),
        "sabpaisa_txn_id": result.get("sabpaisaTxnId", ""),
        "sabpaisa_message": result.get("sabpaisaMessage", ""),
        "payment_mode": result.get("paymentMode", ""),
        "bank_name": result.get("bankName", ""),
        "bank_message": result.get("bankMessage", ""),
        "bank_error_code": result.get("bankErrorCode", ""),
        "sabpaisa_error_code": result.get("sabpaisaErrorCode", ""),
        "bank_txn_id": result.get("bankTxnId", ""),
        "payer_name": result.get("payerName", ""),
        "payer_email": result.get("payerEmail", ""),
        "payer_mobile": result.get("payerMobile", ""),
        "challan_number": result.get("challanNumber", ""),
        "trans_date": result.get("transDate", ""),
        "raw": decrypted,
    }


def is_payment_successful(status_code: str) -> bool:
    """Check if payment status code indicates success."""
    return status_code == "0000"

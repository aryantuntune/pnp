"""
SabPaisa payment gateway integration.

Implements AES-128-CBC encryption/decryption for SabPaisa hosted checkout.
Builds pipe-delimited payment payloads, encrypts them, and parses
encrypted callback responses.
"""

import base64
import logging
import time
import uuid
from urllib.parse import urlencode

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration check
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    """Check if all required SabPaisa credentials are set."""
    return bool(
        settings.SABPAISA_CLIENT_CODE
        and settings.SABPAISA_AUTH_KEY
        and settings.SABPAISA_AUTH_IV
    )


# ---------------------------------------------------------------------------
# AES-128-CBC helpers
# ---------------------------------------------------------------------------

def _normalize_key(value: str, length: int = 16) -> bytes:
    """Ensure key/IV is exactly *length* bytes — pad with \\0 or truncate."""
    raw = value.encode("utf-8")
    if len(raw) < length:
        raw = raw + b"\x00" * (length - len(raw))
    return raw[:length]


def _get_cipher(encrypt: bool = True):
    """Create an AES-128-CBC cipher using the configured key and IV.

    Parameters
    ----------
    encrypt : bool
        ``True`` to create an encryptor, ``False`` for a decryptor.
        (PyCryptodome uses the same factory for both; the parameter is
        kept for interface clarity.)
    """
    key = _normalize_key(settings.SABPAISA_AUTH_KEY, 16)
    iv = _normalize_key(settings.SABPAISA_AUTH_IV, 16)
    return AES.new(key, AES.MODE_CBC, iv)


def _encrypt(plaintext: str) -> str:
    """AES-128-CBC encrypt *plaintext* with PKCS7 padding, return base64."""
    cipher = _get_cipher(encrypt=True)
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("utf-8")


def _decrypt(encoded: str) -> str:
    """Base64-decode, AES-128-CBC decrypt, PKCS7 unpad, return plaintext."""
    cipher = _get_cipher(encrypt=False)
    raw = base64.b64decode(encoded)
    decrypted = cipher.decrypt(raw)
    return unpad(decrypted, AES.block_size).decode("utf-8")


# ---------------------------------------------------------------------------
# Transaction ID
# ---------------------------------------------------------------------------

def generate_client_txn_id(booking_id: int) -> str:
    """Generate a unique client transaction ID for SabPaisa."""
    return f"SSMSPL_{booking_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def _safe_get(parts: list, index: int, default: str = "") -> str:
    """Safely get a list element by *index*, returning *default* on miss."""
    try:
        val = parts[index] if index < len(parts) else default
        return val.strip() if val else default
    except (IndexError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Build payment request
# ---------------------------------------------------------------------------

def build_payment_request(
    *,
    client_txn_id: str,
    amount: float,
    payer_name: str = "",
    payer_email: str = "",
    payer_mobile: str = "",
    callback_url: str = "",
) -> dict:
    """Build a SabPaisa hosted-checkout redirect request.

    Constructs the pipe-delimited payload per the SabPaisa spec, encrypts it,
    and returns the payment URL the frontend should redirect to.

    Returns
    -------
    dict
        ``{"payment_url": str, "client_txn_id": str, "method": "redirect"}``
    """
    client_code = settings.SABPAISA_CLIENT_CODE
    username = settings.SABPAISA_USERNAME
    password = settings.SABPAISA_PASSWORD
    auth_key = settings.SABPAISA_AUTH_KEY
    auth_iv = settings.SABPAISA_AUTH_IV

    # UDF fields 1-20 (all empty)
    udf_fields = "|".join([""] * 20)

    # Pipe-delimited payload per SabPaisa spec:
    # clientCode | transUserName | transUserPassword | authkey | authiv |
    # payerName | payerEmail | payerMobile | clientTxnId | amount |
    # payerAddress | callbackUrl | udf1..udf20 | channelId | programId | mcc
    payload = "|".join([
        client_code,       # 0  clientCode
        username,          # 1  transUserName
        password,          # 2  transUserPassword
        auth_key,          # 3  authkey
        auth_iv,           # 4  authiv
        payer_name,        # 5  payerName
        payer_email,       # 6  payerEmail
        payer_mobile,      # 7  payerMobile
        client_txn_id,     # 8  clientTxnId
        str(amount),       # 9  amount
        "",                # 10 payerAddress
        callback_url,      # 11 callbackUrl
        udf_fields,        # 12-31 udf1..udf20
        "",                # 32 channelId
        "",                # 33 programId
        "",                # 34 mcc
    ])

    enc_data = _encrypt(payload)

    base_url = settings.SABPAISA_BASE_URL.rstrip("/")
    params = urlencode({"encData": enc_data, "clientCode": client_code})
    payment_url = f"{base_url}/SabPaisaInit?{params}"

    return {
        "payment_url": payment_url,
        "client_txn_id": client_txn_id,
        "method": "redirect",
    }


# ---------------------------------------------------------------------------
# Decrypt callback
# ---------------------------------------------------------------------------

def decrypt_callback(enc_data: str) -> dict:
    """Decrypt and parse a SabPaisa callback response.

    Parameters
    ----------
    enc_data : str
        The base64-encoded encrypted payload from SabPaisa's callback.

    Returns
    -------
    dict
        Parsed fields including ``client_txn_id``, ``sabpaisa_txn_id``,
        ``status``, ``amount``, ``bank_name``, ``payment_mode``,
        ``sabpaisa_message``, and the full ``raw`` decrypted string.
    """
    try:
        decrypted = _decrypt(enc_data)
    except Exception:
        logger.exception("Failed to decrypt SabPaisa callback data")
        return {
            "client_txn_id": "",
            "sabpaisa_txn_id": "",
            "status": "DECRYPTION_FAILED",
            "amount": "",
            "bank_name": "",
            "payment_mode": "",
            "sabpaisa_message": "Failed to decrypt callback data",
            "payer_name": "",
            "payer_email": "",
            "payer_mobile": "",
            "client_code": "",
            "raw": "",
        }

    logger.debug("SabPaisa callback decrypted: %s", decrypted)

    parts = decrypted.split("|")

    result = {
        "client_code": _safe_get(parts, 0),
        "payer_name": _safe_get(parts, 5),
        "payer_email": _safe_get(parts, 6),
        "payer_mobile": _safe_get(parts, 7),
        "client_txn_id": _safe_get(parts, 8),
        "amount": _safe_get(parts, 9),
        "sabpaisa_txn_id": _safe_get(parts, 35),
        "status": _safe_get(parts, 36),
        "bank_name": _safe_get(parts, 37),
        "payment_mode": _safe_get(parts, 38),
        "sabpaisa_message": _safe_get(parts, 39),
        "raw": decrypted,
    }

    logger.info(
        "SabPaisa callback parsed — txn=%s status=%s amount=%s",
        result["client_txn_id"],
        result["status"],
        result["amount"],
    )

    return result

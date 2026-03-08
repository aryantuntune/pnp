# SabPaisa Payment Gateway Integration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the simulated payment mode with real SabPaisa hosted checkout across website and mobile app.

**Architecture:** SabPaisa hosted checkout with AES-128-CBC encrypted payloads. Backend creates encrypted payment data, frontend redirects to SabPaisa's checkout page, SabPaisa redirects back to our callback endpoint which decrypts the response, confirms the booking, and redirects to a frontend result page. A `payment_transactions` table logs every attempt for audit/reconciliation. A background task auto-cancels stale PENDING bookings after 15 minutes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, PyCryptodome (AES), Alembic, Next.js 16, React Native / Expo

---

## Task 1: Add `pycryptodome` dependency

**Files:**
- Modify: `backend/requirements-dev.txt`

**Step 1:** Add `pycryptodome` to requirements

Add this line to `backend/requirements-dev.txt`:

```
pycryptodome>=3.20,<4.0
```

**Step 2:** Install

```bash
cd backend && pip install pycryptodome
```

**Step 3:** Verify import works

```bash
cd backend && python -c "from Crypto.Cipher import AES; print('OK')"
```

Expected: `OK`

**Step 4:** Commit

```bash
git add backend/requirements-dev.txt
git commit -m "chore: add pycryptodome for SabPaisa AES encryption"
```

---

## Task 2: Add SabPaisa config fields

**Files:**
- Modify: `backend/app/config.py`

**Step 1:** Add `SABPAISA_USERNAME` and `SABPAISA_PASSWORD` fields to the `Settings` class, right after the existing SabPaisa fields:

```python
    # SabPaisa
    SABPAISA_CLIENT_CODE: str = ""
    SABPAISA_AUTH_KEY: str = ""
    SABPAISA_AUTH_IV: str = ""
    SABPAISA_BASE_URL: str = "https://securepay.sabpaisa.in"
    SABPAISA_USERNAME: str = ""
    SABPAISA_PASSWORD: str = ""
```

**Step 2:** Also add these to `.env.example` if it exists, or to `.env.development`:

```
SABPAISA_USERNAME=""
SABPAISA_PASSWORD=""
```

**Step 3:** Commit

```bash
git add backend/app/config.py
git commit -m "chore: add SabPaisa username/password config fields"
```

---

## Task 3: Create `payment_transactions` model

**Files:**
- Create: `backend/app/models/payment_transaction.py`
- Modify: `backend/app/models/__init__.py` (if it re-exports models)

**Step 1:** Create `backend/app/models/payment_transaction.py`:

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bookings.id"), nullable=False, index=True)
    client_txn_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    sabpaisa_txn_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(9, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="INITIATED")
    # status values: INITIATED, SUCCESS, FAILED, ABORTED
    payment_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # payment_mode from SabPaisa response: UPI, NETBANKING, CARD, etc.
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sabpaisa_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str] = mapped_column(String(10), nullable=False, default="web")
    # platform: "web" or "mobile"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
```

**Step 2:** Verify the model imports cleanly

```bash
cd backend && python -c "from app.models.payment_transaction import PaymentTransaction; print('OK')"
```

**Step 3:** Commit

```bash
git add backend/app/models/payment_transaction.py
git commit -m "feat: add PaymentTransaction model for SabPaisa audit trail"
```

---

## Task 4: Create Alembic migration

**Step 1:** Generate migration

```bash
cd backend && alembic revision --autogenerate -m "add payment_transactions table"
```

**Step 2:** Review the generated migration file, then apply:

```bash
cd backend && alembic upgrade head
```

**Step 3:** Verify table exists

```bash
cd backend && python -c "
import asyncio
from app.database import engine
from sqlalchemy import text
async def check():
    async with engine.connect() as conn:
        r = await conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='payment_transactions' ORDER BY ordinal_position\"))
        print([row[0] for row in r])
asyncio.run(check())
"
```

**Step 4:** Commit

```bash
git add backend/alembic/
git commit -m "chore: migration for payment_transactions table"
```

---

## Task 5: Implement real SabPaisa service

**Files:**
- Rewrite: `backend/app/services/sabpaisa_service.py`

**Step 1:** Replace the entire file with the real implementation:

```python
"""
SabPaisa payment gateway — hosted checkout via AES-128-CBC encrypted redirect.

Flow:
  1. build_payment_request() → returns {payment_url, encrypted_data, client_txn_id}
  2. Frontend redirects/POSTs customer to SabPaisa checkout
  3. SabPaisa redirects to our callback with encrypted response
  4. decrypt_response() → returns dict of transaction fields
"""

import base64
import hashlib
import json
import logging
import time
from urllib.parse import urlencode

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from app.config import settings

logger = logging.getLogger("ssmspl.sabpaisa")


def is_configured() -> bool:
    """Check if all required SabPaisa credentials are set."""
    return bool(
        settings.SABPAISA_CLIENT_CODE
        and settings.SABPAISA_AUTH_KEY
        and settings.SABPAISA_AUTH_IV
    )


def _get_cipher(encrypt: bool = True):
    """Create AES-128-CBC cipher using configured key and IV."""
    key = settings.SABPAISA_AUTH_KEY.encode("utf-8")
    iv = settings.SABPAISA_AUTH_IV.encode("utf-8")
    # SabPaisa uses 128-bit key — pad/truncate to 16 bytes
    key = key[:16].ljust(16, b"\0")
    iv = iv[:16].ljust(16, b"\0")
    return AES.new(key, AES.MODE_CBC, iv)


def _encrypt(plaintext: str) -> str:
    """AES-128-CBC encrypt and base64 encode."""
    cipher = _get_cipher(encrypt=True)
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("utf-8")


def _decrypt(encoded: str) -> str:
    """Base64 decode and AES-128-CBC decrypt."""
    cipher = _get_cipher(encrypt=False)
    decoded = base64.b64decode(encoded)
    decrypted = unpad(cipher.decrypt(decoded), AES.block_size)
    return decrypted.decode("utf-8")


def generate_client_txn_id(booking_id: int) -> str:
    """Generate a unique client transaction ID."""
    return f"SSMSPL_{booking_id}_{int(time.time())}"


def build_payment_request(
    *,
    client_txn_id: str,
    amount: float,
    payer_name: str,
    payer_email: str,
    payer_mobile: str,
    callback_url: str,
) -> dict:
    """
    Build encrypted payment request for SabPaisa hosted checkout.

    Returns:
        {
            "payment_url": "https://securepay.sabpaisa.in/SabPaisaInit?...",
            "client_txn_id": "SSMSPL_123_1709...",
            "method": "redirect",
        }
    """
    if not is_configured():
        raise RuntimeError("SabPaisa is not configured. Set SABPAISA_CLIENT_CODE, AUTH_KEY, AUTH_IV.")

    # Build pipe-delimited payload as per SabPaisa spec
    payload_parts = [
        settings.SABPAISA_CLIENT_CODE,        # clientCode
        settings.SABPAISA_USERNAME or "",      # transUserName
        settings.SABPAISA_PASSWORD or "",      # transUserPassword
        settings.SABPAISA_AUTH_KEY,            # authkey
        settings.SABPAISA_AUTH_IV,             # authiv
        payer_name,                            # payerName
        payer_email,                           # payerEmail
        payer_mobile,                          # payerMobile
        client_txn_id,                         # clientTxnId
        f"{amount:.2f}",                       # amount
        "",                                    # payerAddress (optional)
        callback_url,                          # callbackUrl
        "",                                    # udf1
        "",                                    # udf2
        "",                                    # udf3
        "",                                    # udf4
        "",                                    # udf5
        "",                                    # udf6
        "",                                    # udf7
        "",                                    # udf8
        "",                                    # udf9
        "",                                    # udf10
        "",                                    # udf11
        "",                                    # udf12
        "",                                    # udf13
        "",                                    # udf14
        "",                                    # udf15
        "",                                    # udf16
        "",                                    # udf17
        "",                                    # udf18
        "",                                    # udf19
        "",                                    # udf20
        "",                                    # channelId (optional)
        "",                                    # programId (optional)
        "",                                    # mcc (optional)
    ]
    plaintext = "|".join(payload_parts)
    enc_data = _encrypt(plaintext)

    payment_url = (
        f"{settings.SABPAISA_BASE_URL}/SabPaisaInit?"
        + urlencode({"encData": enc_data, "clientCode": settings.SABPAISA_CLIENT_CODE})
    )

    return {
        "payment_url": payment_url,
        "client_txn_id": client_txn_id,
        "method": "redirect",
    }


def decrypt_callback(enc_data: str) -> dict:
    """
    Decrypt SabPaisa callback response.

    SabPaisa sends back a pipe-delimited encrypted string.
    Returns a dict with parsed transaction fields.
    """
    try:
        decrypted = _decrypt(enc_data)
    except Exception as e:
        logger.error("Failed to decrypt SabPaisa callback: %s", e)
        return {"status": "DECRYPT_ERROR", "error": str(e)}

    parts = decrypted.split("|")
    logger.info("SabPaisa callback decrypted: %d parts", len(parts))

    # SabPaisa response fields (order per their documentation):
    # 0: clientCode, 1: transUserName, 2: transUserPassword,
    # 3: authkey, 4: authiv, 5: payerName, 6: payerEmail,
    # 7: payerMobile, 8: clientTxnId, 9: amount,
    # 10: payerAddress, 11: callbackUrl,
    # 12-31: udf1-udf20, 32: channelId, 33: programId, 34: mcc,
    # 35: sabpaisaTxnId, 36: status, 37: bankName,
    # 38: paymentMode, 39: sabpaisaMessage
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
    return result


def _safe_get(parts: list, index: int, default: str = "") -> str:
    """Safely get a value from a list by index."""
    return parts[index].strip() if index < len(parts) and parts[index] else default
```

**Step 2:** Verify it loads cleanly

```bash
cd backend && python -c "from app.services.sabpaisa_service import is_configured, build_payment_request, decrypt_callback; print('OK')"
```

**Step 3:** Commit

```bash
git add backend/app/services/sabpaisa_service.py
git commit -m "feat: implement real SabPaisa AES encryption service"
```

---

## Task 6: Rewrite payment router with callback endpoint

**Files:**
- Rewrite: `backend/app/routers/portal_payment.py`

**Step 1:** Replace the file with:

```python
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_portal_user
from app.models.booking import Booking
from app.models.payment_transaction import PaymentTransaction
from app.models.portal_user import PortalUser
from app.services import sabpaisa_service, booking_service
from app.services.email_service import send_booking_confirmation

logger = logging.getLogger("ssmspl.payment")

router = APIRouter(prefix="/api/portal/payment", tags=["Portal Payment"])


class CreateOrderRequest(BaseModel):
    booking_id: int = Field(..., description="Booking ID to pay for")
    platform: str = Field("web", description="Platform: 'web' or 'mobile'")


class CreateOrderResponse(BaseModel):
    payment_url: str
    client_txn_id: str
    method: str  # always "redirect"


@router.get("/config", summary="Get payment gateway config")
async def payment_config():
    return {
        "gateway": "sabpaisa",
        "configured": sabpaisa_service.is_configured(),
    }


@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
    summary="Create a SabPaisa payment order",
    description="Encrypts payment data and returns the SabPaisa checkout URL for redirect.",
)
async def create_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: PortalUser = Depends(get_current_portal_user),
):
    if not sabpaisa_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured",
        )

    booking = await booking_service.get_booking_by_id(db, body.booking_id, current_user.id)
    if booking["status"] != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is not in PENDING status",
        )

    # Generate unique transaction ID
    client_txn_id = sabpaisa_service.generate_client_txn_id(body.booking_id)

    # Build callback URL — SabPaisa will redirect here after payment
    backend_base = str(settings.FRONTEND_URL).rstrip("/").replace(":3000", ":8000")
    # Use the app's own base URL for the callback
    callback_url = f"{backend_base}/api/portal/payment/callback"

    # Build the encrypted payment request
    result = sabpaisa_service.build_payment_request(
        client_txn_id=client_txn_id,
        amount=float(booking["net_amount"]),
        payer_name=f"{current_user.first_name} {current_user.last_name}",
        payer_email=current_user.email,
        payer_mobile=current_user.mobile,
        callback_url=callback_url,
    )

    # Log the initiated transaction
    txn = PaymentTransaction(
        booking_id=body.booking_id,
        client_txn_id=client_txn_id,
        amount=booking["net_amount"],
        status="INITIATED",
        platform=body.platform,
    )
    db.add(txn)
    await db.flush()

    return result


@router.get(
    "/callback",
    summary="SabPaisa payment callback (redirect endpoint)",
    description="SabPaisa redirects the customer here after payment. No auth required. "
                "Decrypts response, updates booking, and redirects to frontend result page.",
    include_in_schema=False,  # Hide from Swagger — it's a redirect endpoint
)
async def payment_callback(
    background_tasks: BackgroundTasks,
    encData: str = Query(..., description="Encrypted response from SabPaisa"),
    clientCode: str = Query("", description="Client code echo"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle SabPaisa callback after customer completes/cancels payment.
    This endpoint:
      1. Decrypts the response
      2. Finds the PaymentTransaction by client_txn_id
      3. Updates transaction status
      4. Confirms booking if payment successful
      5. Redirects to frontend result page
    """
    # 1. Decrypt
    parsed = sabpaisa_service.decrypt_callback(encData)
    client_txn_id = parsed.get("client_txn_id", "")
    sabpaisa_status = parsed.get("status", "").upper()

    logger.info(
        "SabPaisa callback: client_txn_id=%s status=%s sabpaisa_txn_id=%s",
        client_txn_id, sabpaisa_status, parsed.get("sabpaisa_txn_id"),
    )

    if not client_txn_id:
        return _redirect_to_frontend(success=False, error="Invalid callback data")

    # 2. Find transaction record
    txn_result = await db.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.client_txn_id == client_txn_id
        )
    )
    txn = txn_result.scalar_one_or_none()
    if not txn:
        logger.error("No PaymentTransaction found for client_txn_id=%s", client_txn_id)
        return _redirect_to_frontend(success=False, error="Transaction not found")

    # Idempotency: if already processed, just redirect
    if txn.status in ("SUCCESS", "FAILED", "ABORTED"):
        is_success = txn.status == "SUCCESS"
        return _redirect_to_frontend(
            success=is_success,
            booking_id=txn.booking_id,
            platform=txn.platform,
        )

    # 3. Update transaction
    txn.sabpaisa_txn_id = parsed.get("sabpaisa_txn_id")
    txn.payment_mode = parsed.get("payment_mode")
    txn.bank_name = parsed.get("bank_name")
    txn.sabpaisa_message = parsed.get("sabpaisa_message")
    txn.raw_response = parsed.get("raw", "")

    is_success = sabpaisa_status == "SUCCESS"
    txn.status = "SUCCESS" if is_success else ("ABORTED" if sabpaisa_status == "ABORTED" else "FAILED")

    # 4. Confirm booking if successful
    if is_success:
        booking_result = await db.execute(
            select(Booking).where(Booking.id == txn.booking_id)
        )
        booking = booking_result.scalar_one_or_none()
        if booking and booking.status == "PENDING":
            booking.status = "CONFIRMED"

            # Fetch portal user for confirmation email
            portal_user_result = await db.execute(
                select(PortalUser).where(PortalUser.id == booking.portal_user_id)
            )
            portal_user = portal_user_result.scalar_one_or_none()

            if portal_user:
                enriched = await booking_service._enrich_booking(db, booking, include_items=True)
                background_tasks.add_task(
                    send_booking_confirmation, enriched, portal_user.email
                )

    await db.flush()

    # 5. Redirect to frontend
    return _redirect_to_frontend(
        success=is_success,
        booking_id=txn.booking_id,
        platform=txn.platform,
    )


def _redirect_to_frontend(
    *,
    success: bool,
    booking_id: int | None = None,
    platform: str = "web",
    error: str = "",
) -> RedirectResponse:
    """Build redirect URL to frontend payment result page."""
    status_str = "success" if success else "failed"

    if platform == "mobile":
        # Deep link for mobile app
        url = f"ssmspl://payment-callback?status={status_str}"
        if booking_id:
            url += f"&booking_id={booking_id}"
        if error:
            url += f"&error={error}"
    else:
        # Web portal redirect
        base = settings.FRONTEND_URL.rstrip("/")
        url = f"{base}/customer/payment/callback?status={status_str}"
        if booking_id:
            url += f"&booking_id={booking_id}"
        if error:
            url += f"&error={error}"

    return RedirectResponse(url=url, status_code=302)
```

**Step 2:** Verify it loads

```bash
cd backend && python -c "from app.routers.portal_payment import router; print('OK')"
```

**Step 3:** Commit

```bash
git add backend/app/routers/portal_payment.py
git commit -m "feat: SabPaisa payment router with create-order and callback endpoints"
```

---

## Task 7: Add PENDING booking expiry background task

**Files:**
- Create: `backend/app/services/booking_expiry_service.py`
- Modify: `backend/app/main.py` (add startup task)

**Step 1:** Create `backend/app/services/booking_expiry_service.py`:

```python
"""
Background task: auto-cancel PENDING bookings older than 15 minutes.
Runs every 5 minutes via asyncio loop started at app startup.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.booking import Booking
from app.models.booking_item import BookingItem

logger = logging.getLogger("ssmspl.booking_expiry")

EXPIRY_MINUTES = 15
CHECK_INTERVAL_SECONDS = 300  # 5 minutes


async def cancel_expired_bookings() -> int:
    """Cancel PENDING bookings older than EXPIRY_MINUTES. Returns count cancelled."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=EXPIRY_MINUTES)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Booking).where(
                    Booking.status == "PENDING",
                    Booking.created_at < cutoff,
                )
            )
            stale = result.scalars().all()

            if not stale:
                return 0

            for booking in stale:
                booking.status = "CANCELLED"
                booking.is_cancelled = True
                # Cancel items
                items_result = await db.execute(
                    select(BookingItem).where(BookingItem.booking_id == booking.id)
                )
                for item in items_result.scalars().all():
                    item.is_cancelled = True

            await db.commit()
            logger.info("Auto-cancelled %d expired PENDING bookings", len(stale))
            return len(stale)
        except Exception:
            await db.rollback()
            logger.exception("Error cancelling expired bookings")
            return 0


async def expiry_loop():
    """Run cancel_expired_bookings on a loop."""
    while True:
        await cancel_expired_bookings()
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
```

**Step 2:** Add the startup hook in `backend/app/main.py`. Add this after the existing router includes (before the `@app.get("/health")` endpoint):

```python
@app.on_event("startup")
async def start_booking_expiry():
    from app.services.booking_expiry_service import expiry_loop
    import asyncio
    asyncio.create_task(expiry_loop())
```

**Step 3:** Commit

```bash
git add backend/app/services/booking_expiry_service.py backend/app/main.py
git commit -m "feat: auto-cancel PENDING bookings after 15 minutes"
```

---

## Task 8: Remove the simulated `/pay` endpoint

**Files:**
- Modify: `backend/app/routers/portal_bookings.py`

**Step 1:** Remove the `POST /{booking_id}/pay` endpoint from `portal_bookings.py` (lines 60-82). This was the simulated payment — now payment goes through SabPaisa.

Keep all other endpoints intact (create, list, get, cancel, qr).

**Step 2:** Verify

```bash
cd backend && python -c "from app.routers.portal_bookings import router; print('OK')"
```

**Step 3:** Commit

```bash
git add backend/app/routers/portal_bookings.py
git commit -m "refactor: remove simulated /pay endpoint — payment now via SabPaisa"
```

---

## Task 9: Create frontend payment callback page

**Files:**
- Create: `frontend/src/app/customer/payment/callback/page.tsx`

**Step 1:** Create the directory and file:

```bash
mkdir -p frontend/src/app/customer/payment/callback
```

**Step 2:** Create `frontend/src/app/customer/payment/callback/page.tsx`:

```tsx
"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import CustomerLayout from "@/components/customer/CustomerLayout";
import { CheckCircle, XCircle, ArrowLeft, Loader2 } from "lucide-react";

function PaymentCallbackContent() {
  const params = useSearchParams();
  const status = params.get("status");
  const bookingId = params.get("booking_id");
  const error = params.get("error");

  const isSuccess = status === "success";

  return (
    <CustomerLayout>
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <div className="bg-white rounded-3xl shadow-xl border border-slate-100 p-8">
          {isSuccess ? (
            <>
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h1 className="text-2xl font-bold text-slate-800 mb-2">
                Payment Successful!
              </h1>
              <p className="text-slate-500 mb-8">
                Your booking has been confirmed. You will receive a confirmation
                email shortly.
              </p>
              {bookingId && (
                <Link
                  href={`/customer/history/${bookingId}`}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sky-600 text-white font-semibold hover:bg-sky-700 transition-colors"
                >
                  View Booking & Download Ticket
                </Link>
              )}
            </>
          ) : (
            <>
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center">
                <XCircle className="w-10 h-10 text-red-600" />
              </div>
              <h1 className="text-2xl font-bold text-slate-800 mb-2">
                Payment Failed
              </h1>
              <p className="text-slate-500 mb-2">
                {error || "Your payment could not be processed. Please try again."}
              </p>
              <p className="text-sm text-slate-400 mb-8">
                No money has been deducted from your account. If any amount was
                debited, it will be refunded within 5-7 business days.
              </p>
              {bookingId ? (
                <Link
                  href={`/customer/history/${bookingId}`}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sky-600 text-white font-semibold hover:bg-sky-700 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Retry Payment
                </Link>
              ) : (
                <Link
                  href="/customer/history"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sky-600 text-white font-semibold hover:bg-sky-700 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Go to My Bookings
                </Link>
              )}
            </>
          )}
        </div>
      </div>
    </CustomerLayout>
  );
}

export default function PaymentCallbackPage() {
  return (
    <Suspense
      fallback={
        <CustomerLayout>
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
          </div>
        </CustomerLayout>
      }
    >
      <PaymentCallbackContent />
    </Suspense>
  );
}
```

**Step 3:** Commit

```bash
git add frontend/src/app/customer/payment/
git commit -m "feat: add payment callback page for SabPaisa redirect"
```

---

## Task 10: Update web portal "Pay Now" to redirect to SabPaisa

**Files:**
- Modify: `frontend/src/app/customer/history/[id]/page.tsx`

**Step 1:** Replace the "Pay Now" button's `onClick` handler. Currently it calls `/api/portal/bookings/${bookingId}/pay` (simulated). Change it to:

1. Call `/api/portal/payment/create-order` with `{booking_id, platform: "web"}`
2. Redirect to the returned `payment_url`

Replace the existing pay button block (the `isPending && (...)` section around lines 366-386) with:

```tsx
{isPending && (
  <button
    onClick={async () => {
      setPaying(true);
      try {
        const res = await api.post(
          "/api/portal/payment/create-order",
          { booking_id: Number(bookingId), platform: "web" }
        );
        // Redirect to SabPaisa checkout
        window.location.href = res.data.payment_url;
      } catch {
        setErrorMsg("Unable to initiate payment. Please try again.");
        setTimeout(() => setErrorMsg(null), 4000);
        setPaying(false);
      }
    }}
    disabled={paying}
    className="flex items-center gap-2 px-6 py-3 rounded-xl bg-green-600 text-white font-semibold hover:bg-green-700 transition-colors disabled:opacity-50"
  >
    <IndianRupee className="w-5 h-5" />
    <span>{paying ? "Redirecting to payment..." : "Pay Now"}</span>
  </button>
)}
```

**Step 2:** Verify build

```bash
cd frontend && npm run build
```

**Step 3:** Commit

```bash
git add frontend/src/app/customer/history/\[id\]/page.tsx
git commit -m "feat: web portal Pay Now redirects to SabPaisa checkout"
```

---

## Task 11: Update mobile app payment flow

**Files:**
- Modify: `apps/customer/src/services/paymentService.ts`
- Modify: `apps/customer/src/screens/main/BookingScreen.tsx`
- Modify: `apps/customer/app.json` (add deep link scheme)

**Step 1:** Update `apps/customer/app.json` to register the `ssmspl` URL scheme:

Add to the `expo` object:

```json
"scheme": "ssmspl"
```

**Step 2:** Update `apps/customer/src/services/paymentService.ts`:

```typescript
import api from './api';

export interface PaymentConfig {
  gateway: string;
  configured: boolean;
}

export interface PaymentOrder {
  payment_url: string;
  client_txn_id: string;
  method: string;
}

export async function getPaymentConfig(): Promise<PaymentConfig> {
  const { data } = await api.get<PaymentConfig>('/api/portal/payment/config');
  return data;
}

export async function createPaymentOrder(bookingId: number): Promise<PaymentOrder> {
  const { data } = await api.post<PaymentOrder>('/api/portal/payment/create-order', {
    booking_id: bookingId,
    platform: 'mobile',
  });
  return data;
}
```

**Step 3:** Update `BookingScreen.tsx` `handlePay` function. Replace the payment section (around lines 193-231) where it calls `simulatePayment` with:

```typescript
import { Linking } from 'react-native';
import { createPaymentOrder } from '../../services/paymentService';

// Inside handlePay, replace from "// Simulate payment..." to the Alert:
      // Initiate SabPaisa payment
      const order = await createPaymentOrder(result.id);
      setIsProcessingPayment(false);

      // Open SabPaisa checkout in external browser
      const canOpen = await Linking.canOpenURL(order.payment_url);
      if (canOpen) {
        await Linking.openURL(order.payment_url);
      } else {
        Alert.alert('Error', 'Unable to open payment page. Please try from the bookings list.');
      }

      // Clear form — user will return via deep link
      dispatch(clearBookingForm());
      navigation.goBack();
```

Also remove the `import { simulatePayment }` line at the top of the file.

**Step 4:** Commit

```bash
git add apps/customer/
git commit -m "feat: mobile app payment redirects to SabPaisa via Linking.openURL"
```

---

## Task 12: Handle deep link return in mobile app

**Files:**
- Modify: `apps/customer/src/navigation/MainNavigator.tsx` (or equivalent)

**Step 1:** Add a deep link handler. In the app's navigation config or root component, handle the `ssmspl://payment-callback` URL:

```typescript
import { Linking, Alert } from 'react-native';

// In useEffect at app root or navigation container:
useEffect(() => {
  const handleDeepLink = (event: { url: string }) => {
    const url = new URL(event.url);
    if (url.hostname === 'payment-callback' || url.pathname === '/payment-callback') {
      const status = url.searchParams.get('status');
      const bookingId = url.searchParams.get('booking_id');

      if (status === 'success') {
        Alert.alert(
          'Payment Successful!',
          'Your booking has been confirmed.',
          [{ text: 'View Booking', onPress: () => {
            // Navigate to booking detail if possible
          }}],
        );
      } else {
        Alert.alert(
          'Payment Failed',
          'Your payment could not be processed. You can retry from My Bookings.',
        );
      }
    }
  };

  const sub = Linking.addEventListener('url', handleDeepLink);

  // Handle cold start deep link
  Linking.getInitialURL().then((url) => {
    if (url) handleDeepLink({ url });
  });

  return () => sub.remove();
}, []);
```

**Step 2:** Commit

```bash
git add apps/customer/
git commit -m "feat: handle SabPaisa payment deep link return in mobile app"
```

---

## Task 13: Add "Online" payment mode to seed data

**Files:**
- Modify: `backend/scripts/seed_data.sql`

**Step 1:** Check if an "Online" payment mode already exists in the seed data. If not, add:

```sql
INSERT INTO payment_modes (id, description, is_active, created_at)
VALUES (4, 'Online', true, NOW())
ON CONFLICT (id) DO NOTHING;
```

The booking service already looks for `PaymentMode.description == "Online"` when creating portal bookings.

**Step 2:** Commit

```bash
git add backend/scripts/seed_data.sql
git commit -m "chore: add Online payment mode to seed data"
```

---

## Task 14: Verify end-to-end flow

**Step 1:** Start backend

```bash
cd backend && uvicorn app.main:app --reload
```

**Step 2:** Start frontend

```bash
cd frontend && npm run dev
```

**Step 3:** Manual test checklist:

- [ ] `GET /api/portal/payment/config` returns `{"gateway": "sabpaisa", "configured": false}` (no keys yet)
- [ ] `POST /api/portal/payment/create-order` returns 503 when SabPaisa is not configured
- [ ] Payment callback page renders at `/customer/payment/callback?status=success&booking_id=1`
- [ ] Payment callback page renders at `/customer/payment/callback?status=failed&error=test`
- [ ] PENDING bookings created > 15 min ago get auto-cancelled (check logs)
- [ ] The old `/api/portal/bookings/{id}/pay` endpoint returns 404 (removed)

**Step 4:** Final commit / tag

```bash
git add -A
git commit -m "feat: SabPaisa payment gateway integration complete"
```

---

## Notes for Production

When you receive SabPaisa credentials, set these env vars:
```
SABPAISA_CLIENT_CODE=your_client_code
SABPAISA_AUTH_KEY=your_16_char_auth_key
SABPAISA_AUTH_IV=your_16_char_auth_iv
SABPAISA_USERNAME=your_username
SABPAISA_PASSWORD=your_password
SABPAISA_BASE_URL=https://securepay.sabpaisa.in
```

The system will automatically switch from "not configured" to live once these are set. No code changes needed.

**Branch-wise routing (future):** When you decide whether SabPaisa supports sub-merchant or payment routing, the `build_payment_request()` function in `sabpaisa_service.py` is the single place to add the sub-merchant ID or split settlement parameters.

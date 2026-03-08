import logging
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from typing import Literal
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal/payment", tags=["Portal Payment"])


# ── Request / Response schemas ───────────────────────────────────────────────


class CreateOrderRequest(BaseModel):
    booking_id: int = Field(..., description="Booking ID to pay for")
    platform: Literal["web", "mobile"] = Field("web", description="Platform: 'web' or 'mobile'")


class CreateOrderResponse(BaseModel):
    payment_url: str
    client_txn_id: str
    method: str  # always "redirect"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _redirect_to_frontend(
    *, success: bool, booking_id: int | None = None, platform: str = "web", error: str = ""
) -> RedirectResponse:
    status_str = "success" if success else "failed"
    if platform == "mobile":
        url = f"ssmspl://payment-callback?status={status_str}"
    else:
        base = settings.FRONTEND_URL.rstrip("/")
        url = f"{base}/customer/payment/callback?status={status_str}"
    if booking_id:
        url += f"&booking_id={booking_id}"
    if error:
        url += f"&error={quote(error)}"
    return RedirectResponse(url=url, status_code=302)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/config", summary="Get payment gateway config")
async def payment_config():
    return {
        "gateway": "sabpaisa",
        "configured": sabpaisa_service.is_configured(),
    }


@router.post(
    "/create-order",
    summary="Create a payment order",
    response_model=CreateOrderResponse,
)
async def create_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: PortalUser = Depends(get_current_portal_user),
):
    # 1. Check SabPaisa is configured
    if not sabpaisa_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured",
        )

    # 2. Get booking (validates ownership)
    booking_data = await booking_service.get_booking_by_id(
        db, body.booking_id, current_user.id
    )

    # 3. Check booking is PENDING
    if booking_data["status"] != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is not in PENDING status",
        )

    # 4. Generate client transaction ID
    client_txn_id = sabpaisa_service.generate_client_txn_id(body.booking_id)

    # 5. Build callback URL — point to this backend's own URL
    callback_url = f"{settings.BACKEND_URL.rstrip('/')}/api/portal/payment/callback"

    # 6. Build payment request
    payer_name = f"{current_user.first_name} {current_user.last_name}".strip()
    result = sabpaisa_service.build_payment_request(
        client_txn_id=client_txn_id,
        amount=float(booking_data["net_amount"]),
        payer_name=payer_name,
        payer_email=current_user.email,
        payer_mobile=current_user.mobile,
        callback_url=callback_url,
    )

    # 7. Create PaymentTransaction record
    txn = PaymentTransaction(
        booking_id=body.booking_id,
        client_txn_id=client_txn_id,
        amount=booking_data["net_amount"],
        status="INITIATED",
        platform=body.platform,
    )
    db.add(txn)
    await db.flush()

    logger.info(
        "Payment order created — booking_id=%s client_txn_id=%s",
        body.booking_id,
        client_txn_id,
    )

    # 8. Return result
    return result


@router.get(
    "/callback",
    summary="SabPaisa payment callback",
    include_in_schema=False,
)
async def payment_callback(
    background_tasks: BackgroundTasks,
    encData: str = Query(..., description="Encrypted callback data from SabPaisa"),
    clientCode: str = Query(None, description="Client code from SabPaisa"),
    db: AsyncSession = Depends(get_db),
):
    # 1. Decrypt callback data
    parsed = sabpaisa_service.decrypt_callback(encData)

    client_txn_id = parsed.get("client_txn_id", "")
    sabpaisa_status = parsed.get("status", "").upper()

    logger.info(
        "Payment callback received — client_txn_id=%s sabpaisa_status=%s",
        client_txn_id,
        sabpaisa_status,
    )

    if not client_txn_id:
        logger.error("Callback missing client_txn_id — cannot process")
        return _redirect_to_frontend(success=False, error="Invalid callback data")

    # 2-3. Find PaymentTransaction by client_txn_id
    result = await db.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.client_txn_id == client_txn_id
        )
    )
    txn = result.scalar_one_or_none()

    if not txn:
        logger.error("No PaymentTransaction found for client_txn_id=%s", client_txn_id)
        return _redirect_to_frontend(success=False, error="Transaction not found")

    # 4. Idempotency — if already processed, just redirect
    if txn.status in ("SUCCESS", "FAILED", "ABORTED"):
        logger.info(
            "Transaction %s already processed (status=%s), skipping update",
            client_txn_id,
            txn.status,
        )
        return _redirect_to_frontend(
            success=(txn.status == "SUCCESS"),
            booking_id=txn.booking_id,
            platform=txn.platform,
        )

    # 5. Update transaction with callback data
    txn.sabpaisa_txn_id = parsed.get("sabpaisa_txn_id", "")
    txn.payment_mode = parsed.get("payment_mode", "")
    txn.bank_name = parsed.get("bank_name", "")
    txn.sabpaisa_message = parsed.get("sabpaisa_message", "")

    # Strip sensitive fields (positions 0-4: clientCode, username, password, authKey, authIV)
    raw = parsed.get("raw", "")
    if raw:
        parts = raw.split("|")
        if len(parts) > 5:
            parts[:5] = ["***"] * 5
        raw = "|".join(parts)
    txn.raw_response = raw

    # 6. Set status based on SabPaisa response
    is_success = sabpaisa_status == "SUCCESS"
    if is_success:
        callback_amount = parsed.get("amount", "")
        if callback_amount:
            try:
                if abs(float(callback_amount) - float(txn.amount)) > 0.01:
                    logger.error(
                        "Amount mismatch for %s: expected %s, got %s",
                        client_txn_id, txn.amount, callback_amount,
                    )
                    is_success = False
                    txn.sabpaisa_message = f"Amount mismatch: expected {txn.amount}, got {callback_amount}"
            except (ValueError, TypeError):
                pass

    if is_success:
        txn.status = "SUCCESS"
    elif sabpaisa_status == "ABORTED":
        txn.status = "ABORTED"
    else:
        txn.status = "FAILED"

    await db.flush()

    # 7. If SUCCESS, confirm the booking and send email
    if txn.status == "SUCCESS":
        booking_result = await db.execute(
            select(Booking).where(Booking.id == txn.booking_id)
        )
        booking = booking_result.scalar_one_or_none()

        if booking and booking.status == "PENDING":
            booking.status = "CONFIRMED"
            await db.flush()

            logger.info("Booking %s confirmed via payment callback", booking.id)

            # Enrich booking for email and send in background
            enriched = await booking_service._enrich_booking(
                db, booking, include_items=True
            )

            # Look up customer email
            portal_user_result = await db.execute(
                select(PortalUser).where(PortalUser.id == booking.portal_user_id)
            )
            portal_user = portal_user_result.scalar_one_or_none()
            if portal_user:
                background_tasks.add_task(
                    send_booking_confirmation, enriched, portal_user.email
                )

    # 8. Redirect to frontend
    return _redirect_to_frontend(
        success=(txn.status == "SUCCESS"),
        booking_id=txn.booking_id,
        platform=txn.platform,
    )

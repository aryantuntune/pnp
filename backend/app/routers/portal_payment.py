import html as html_mod
import logging
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
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
from app.services import ccavenue_service, booking_service
from app.services.email_service import send_booking_confirmation
from app.services.ccavenue_service import is_payment_successful

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal/payment", tags=["Portal Payment"])


# ── Request / Response schemas ───────────────────────────────────────────────


class CreateOrderRequest(BaseModel):
    booking_id: int = Field(..., description="Booking ID to pay for")
    platform: Literal["web", "mobile"] = Field("web", description="Platform: 'web' or 'mobile'")


class CreateOrderResponse(BaseModel):
    ccavenue_url: str
    enc_request: str
    access_code: str
    order_id: str


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
        "gateway": "ccavenue",
        "configured": ccavenue_service.is_configured(),
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
    if not ccavenue_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured",
        )

    booking_data = await booking_service.get_booking_by_id(
        db, body.booking_id, current_user.id
    )

    if booking_data["status"] != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is not in PENDING status",
        )

    order_id = ccavenue_service.generate_order_id(body.booking_id)

    backend_base = settings.BACKEND_URL.rstrip("/")
    redirect_url = f"{backend_base}/api/portal/payment/callback"
    cancel_url = f"{backend_base}/api/portal/payment/callback"

    payer_name = f"{current_user.first_name} {current_user.last_name}".strip()
    result = ccavenue_service.build_payment_request(
        order_id=order_id,
        amount=float(booking_data["net_amount"]),
        billing_name=payer_name,
        billing_email=current_user.email,
        billing_tel=current_user.mobile,
        redirect_url=redirect_url,
        cancel_url=cancel_url,
        merchant_param1=body.platform,
    )

    txn = PaymentTransaction(
        booking_id=body.booking_id,
        client_txn_id=order_id,
        amount=booking_data["net_amount"],
        status="INITIATED",
        platform=body.platform,
    )
    db.add(txn)
    await db.flush()

    logger.info(
        "Payment order created — booking_id=%s order_id=%s",
        body.booking_id,
        order_id,
    )

    return result


@router.get(
    "/initiate/{order_id}",
    include_in_schema=False,
)
async def initiate_checkout(
    order_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Serve auto-submitting HTML form for CCAvenue checkout.

    Used by the mobile app: after calling /create-order, the app opens this
    URL via Linking.openURL to POST the encrypted payment data to CCAvenue
    without needing a WebView or native SDK.
    """
    txn_result = await db.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.client_txn_id == order_id,
            PaymentTransaction.status == "INITIATED",
        )
    )
    txn = txn_result.scalar_one_or_none()
    if not txn:
        return HTMLResponse("<h1>Invalid or expired payment link</h1>", status_code=404)

    booking_result = await db.execute(
        select(Booking).where(Booking.id == txn.booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    if not booking:
        return HTMLResponse("<h1>Booking not found</h1>", status_code=404)

    portal_user_result = await db.execute(
        select(PortalUser).where(PortalUser.id == booking.portal_user_id)
    )
    portal_user = portal_user_result.scalar_one_or_none()

    backend_base = settings.BACKEND_URL.rstrip("/")
    redirect_url = f"{backend_base}/api/portal/payment/callback"
    cancel_url = f"{backend_base}/api/portal/payment/callback"

    result = ccavenue_service.build_payment_request(
        order_id=order_id,
        amount=float(txn.amount),
        billing_name=(
            f"{portal_user.first_name} {portal_user.last_name}".strip()
            if portal_user
            else "Customer"
        ),
        billing_email=portal_user.email if portal_user else "",
        billing_tel=portal_user.mobile if portal_user else "",
        redirect_url=redirect_url,
        cancel_url=cancel_url,
        merchant_param1=txn.platform,
    )

    ccavenue_url = html_mod.escape(result["ccavenue_url"])
    enc_request = html_mod.escape(result["enc_request"])
    access_code = html_mod.escape(result["access_code"])

    html_content = (
        "<!DOCTYPE html>"
        "<html>"
        "<head><title>Redirecting to payment...</title>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<style>body{display:flex;align-items:center;justify-content:center;"
        "min-height:100vh;margin:0;font-family:sans-serif;background:#f5f5f5}"
        "p{font-size:18px;color:#333}</style>"
        "</head>"
        '<body onload="document.getElementById(\'pf\').submit()">'
        "<p>Redirecting to payment gateway&#8230;</p>"
        f'<form id="pf" method="POST" action="{ccavenue_url}">'
        f'<input type="hidden" name="encRequest" value="{enc_request}">'
        f'<input type="hidden" name="access_code" value="{access_code}">'
        "</form>"
        "</body>"
        "</html>"
    )
    return HTMLResponse(html_content)


@router.post(
    "/callback",
    summary="CCAvenue payment callback",
    include_in_schema=False,
)
async def payment_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Handle CCAvenue redirect POST with encrypted response."""
    form = await request.form()
    enc_resp = form.get("encResp", "")

    if not enc_resp:
        logger.error("Callback missing encResp form field")
        return _redirect_to_frontend(success=False, error="Missing encResp")

    parsed = ccavenue_service.decrypt_response(enc_resp)

    order_id = parsed.get("order_id", "")
    order_status = parsed.get("order_status", "")

    logger.info(
        "Payment callback — order_id=%s order_status=%s tracking_id=%s",
        order_id,
        order_status,
        parsed.get("tracking_id", ""),
    )

    if not order_id:
        logger.error("Callback missing order_id — cannot process")
        return _redirect_to_frontend(success=False, error="Invalid callback data")

    # Find PaymentTransaction by order_id (stored as client_txn_id)
    result = await db.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.client_txn_id == order_id
        )
    )
    txn = result.scalar_one_or_none()

    if not txn:
        logger.error("No PaymentTransaction found for order_id=%s", order_id)
        return _redirect_to_frontend(success=False, error="Transaction not found")

    # Idempotency — if already processed, just redirect
    if txn.status in ("SUCCESS", "FAILED", "ABORTED"):
        return _redirect_to_frontend(
            success=(txn.status == "SUCCESS"),
            booking_id=txn.booking_id,
            platform=txn.platform,
        )

    # Update transaction with callback data
    txn.gateway_txn_id = parsed.get("tracking_id", "")
    txn.payment_mode = parsed.get("payment_mode", "")
    txn.bank_name = parsed.get("card_name", "")
    txn.gateway_message = parsed.get("status_message", "")

    # Store raw response (exclude sensitive fields)
    raw_pairs = [
        f"{k}={v}" for k, v in parsed.items()
        if k not in ("encResp",)
    ]
    txn.raw_response = "&".join(raw_pairs)

    # Determine success
    is_success = is_payment_successful(order_status)

    if is_success:
        # Verify amount matches
        callback_amount = parsed.get("amount", "")
        if callback_amount:
            try:
                if abs(float(callback_amount) - float(txn.amount)) > 0.01:
                    logger.error(
                        "Amount mismatch for %s: expected %s, got %s",
                        order_id, txn.amount, callback_amount,
                    )
                    is_success = False
                    txn.gateway_message = f"Amount mismatch: expected {txn.amount}, got {callback_amount}"
            except (ValueError, TypeError):
                pass

    if is_success:
        txn.status = "SUCCESS"
    elif order_status == "Aborted":
        txn.status = "ABORTED"
    else:
        txn.status = "FAILED"

    await db.flush()

    # If SUCCESS, confirm the booking and send email
    if txn.status == "SUCCESS":
        booking_result = await db.execute(
            select(Booking).where(Booking.id == txn.booking_id)
        )
        booking = booking_result.scalar_one_or_none()

        if booking and booking.status == "PENDING":
            booking.status = "CONFIRMED"
            await db.flush()

            logger.info("Booking %s confirmed via payment callback", booking.id)

            enriched = await booking_service._enrich_booking(
                db, booking, include_items=True
            )

            portal_user_result = await db.execute(
                select(PortalUser).where(PortalUser.id == booking.portal_user_id)
            )
            portal_user = portal_user_result.scalar_one_or_none()
            if portal_user:
                background_tasks.add_task(
                    send_booking_confirmation, enriched, portal_user.email
                )

    # Determine platform from merchant_param1 or stored value
    platform = parsed.get("merchant_param1", txn.platform) or "web"

    return _redirect_to_frontend(
        success=(txn.status == "SUCCESS"),
        booking_id=txn.booking_id,
        platform=platform,
    )

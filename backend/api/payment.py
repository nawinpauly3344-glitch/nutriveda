"""Payment API - Razorpay integration (ready to activate when keys are available)."""

import os
import hmac
import hashlib
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import get_db, ClientSubmission, AppSettings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payment", tags=["Payment"])

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")


class CreateOrderRequest(BaseModel):
    submission_id: int
    currency: str = "INR"


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    submission_id: int


@router.get("/config")
async def get_payment_config(db: AsyncSession = Depends(get_db)):
    """Public endpoint — returns active price config (no auth required)."""
    result = await db.execute(select(AppSettings).where(AppSettings.key == "active_price_inr"))
    setting = result.scalar_one_or_none()
    price_inr = int(setting.value) if setting else 1999
    orig_result = await db.execute(select(AppSettings).where(AppSettings.key == "original_price_inr"))
    orig_setting = orig_result.scalar_one_or_none()
    original_price = int(orig_setting.value) if orig_setting else 0
    discount_pct = round((original_price - price_inr) / original_price * 100) if original_price > price_inr > 0 else 0
    return {
        "active_price_inr": price_inr,
        "original_price_inr": original_price,
        "discount_pct": discount_pct,
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "payment_enabled": bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),
    }


@router.post("/create-order")
async def create_order(req: CreateOrderRequest, db: AsyncSession = Depends(get_db)):
    """Create a Razorpay order for a submission."""
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment gateway not configured yet. Please contact support.")

    try:
        import razorpay
    except ImportError:
        raise HTTPException(status_code=503, detail="Payment library not installed.")

    # Get active price
    result = await db.execute(select(AppSettings).where(AppSettings.key == "active_price_inr"))
    setting = result.scalar_one_or_none()
    price_inr = int(setting.value) if setting else 1999

    # Create Razorpay order
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    amount_paise = price_inr * 100  # Razorpay uses smallest currency unit

    order_data = {
        "amount": amount_paise,
        "currency": req.currency,
        "receipt": f"nutriveda_{req.submission_id}",
        "notes": {"submission_id": str(req.submission_id)},
    }

    try:
        order = client.order.create(data=order_data)
        log.info(f"Razorpay order created: {order['id']} for submission {req.submission_id}")
        return {"order_id": order["id"], "amount": amount_paise, "currency": req.currency, "key_id": RAZORPAY_KEY_ID}
    except Exception as e:
        log.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment order.")


@router.post("/verify")
async def verify_payment(req: VerifyPaymentRequest, db: AsyncSession = Depends(get_db)):
    """Verify Razorpay payment signature and mark submission as paid."""
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment gateway not configured.")

    # Verify signature
    message = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, req.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment verification failed — invalid signature.")

    # Update submission payment status
    result = await db.execute(select(ClientSubmission).where(ClientSubmission.id == req.submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    submission.payment_id = req.razorpay_payment_id
    submission.payment_status = "paid"
    await db.commit()

    log.info(f"Payment verified for submission {req.submission_id}: {req.razorpay_payment_id}")
    return {"success": True, "submission_id": req.submission_id}

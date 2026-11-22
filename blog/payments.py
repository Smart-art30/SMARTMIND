# blog/payments.py

import base64
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================
# MPESA ACCESS TOKEN
# ============================================================

def get_mpesa_access_token():
    """
    Obtain an OAuth access token from Safaricom Daraja.
    Returns the token string, or None on failure.
    """

    url = (
        f"{settings.MPESA_BASE_URL}"
        "/oauth/v1/generate?grant_type=client_credentials"
    )

    try:
        response = requests.get(
            url,
            auth=(
                settings.MPESA_CONSUMER_KEY,
                settings.MPESA_CONSUMER_SECRET,
            ),
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()
        token = data.get("access_token")

        if not token:
            logger.error(
                "M-Pesa auth response missing access_token: %s", data
            )
            return None

        return token

    except requests.RequestException:
        logger.exception("Failed to obtain M-Pesa access token.")
        return None


# ============================================================
# PHONE NORMALIZATION
# ============================================================

def normalize_mpesa_phone(phone):
    """
    Convert Kenyan phone numbers into Safaricom-compatible format:
    2547XXXXXXXX or 2541XXXXXXXX.

    Idempotent: same output for every valid input form.

    Handles:
        0712345678          -> 254712345678
        +254712345678       -> 254712345678
        254712345678        -> 254712345678
        712345678           -> 254712345678
        254712345678 (int)  -> 254712345678
        254712345678.0      -> 254712345678   (Daraja sometimes sends float)
        00254712345678      -> 254712345678
        "0712 345 678"      -> 254712345678
        "0712-345-678"      -> 254712345678

    Returns "" for invalid input — never None.
    (Returning None previously caused the callback's phone check to
     silently fail and reject every real payment.)
    """

    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())

    if not digits:
        return ""

    # Strip international prefix 00254 -> 254
    if digits.startswith("00254"):
        digits = digits[2:]

    # Already canonical: 2547XXXXXXXX / 2541XXXXXXXX
    if digits.startswith("254") and len(digits) == 12:
        return digits

    # Local 10-digit: 07XXXXXXXX / 01XXXXXXXX
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]

    # Bare 9-digit: 7XXXXXXXX / 1XXXXXXXX
    if len(digits) == 9 and (
        digits.startswith("7") or digits.startswith("1")
    ):
        return "254" + digits

    # Anything else — best-effort, do not return None
    return digits


# ============================================================
# PASSWORD GENERATION
# ============================================================

def generate_mpesa_password():
    """
    Generate the Daraja STK Push password.

    Password = Base64(BusinessShortCode + Passkey + Timestamp)

    NOTE: The password must be built from the SAME shortcode that is
    sent as BusinessShortCode in the STK request. For Buy Goods (Till)
    payments, that is the Head Office / Store Number bound at Go Live,
    NOT the Till Number itself.
    """

    shortcode = str(settings.MPESA_SHORTCODE)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    raw_password = (
        shortcode
        + settings.MPESA_PASSKEY
        + timestamp
    )

    password = base64.b64encode(
        raw_password.encode("utf-8")
    ).decode("utf-8")

    return password, timestamp


# ============================================================
# STK PUSH
# ============================================================

def initiate_stk_push(
    *,
    phone,
    amount,
    account_reference,
    transaction_description,
    callback_url,
):
    """
    Initiate an M-Pesa STK Push.

    Supports two modes, selected by MPESA_TRANSACTION_TYPE in settings:

    - "CustomerBuyGoodsOnline" -> Buy Goods / Till
                                  (BusinessShortCode = Store Number,
                                   PartyB = Till Number)
    - "CustomerPayBillOnline"  -> Paybill
                                  (BusinessShortCode = PartyB = Paybill)

    This only initiates a payment request.
    It does NOT confirm that payment has been made.
    """

    # --- Normalize phone ---
    normalized_phone = normalize_mpesa_phone(phone)

    if not normalized_phone or len(normalized_phone) != 12:
        return {
            "success": False,
            "error": "Invalid Kenyan phone number.",
        }

    # --- Validate amount ---
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return {
            "success": False,
            "error": "Invalid payment amount.",
        }

    if amount <= 0 or amount != amount.to_integral_value():
        return {
            "success": False,
            "error": "Payment amount must be a positive whole number.",
        }

    # --- Validate callback URL ---
    if not callback_url or not str(callback_url).startswith("https://"):
        return {
            "success": False,
            "error": "A publicly accessible HTTPS callback URL is required.",
        }

    # --- Resolve transaction mode and PartyB up front ---
    business_shortcode = str(settings.MPESA_SHORTCODE).strip()

    if not business_shortcode:
        return {
            "success": False,
            "error": "M-Pesa is not configured: MPESA_SHORTCODE is missing.",
        }

    transaction_type = str(
        getattr(
            settings,
            "MPESA_TRANSACTION_TYPE",
            "CustomerBuyGoodsOnline",
        )
    ).strip()

    if transaction_type not in (
        "CustomerBuyGoodsOnline",
        "CustomerPayBillOnline",
    ):
        return {
            "success": False,
            "error": (
                "M-Pesa is misconfigured: MPESA_TRANSACTION_TYPE must be "
                "'CustomerBuyGoodsOnline' or 'CustomerPayBillOnline'."
            ),
        }

    if transaction_type == "CustomerBuyGoodsOnline":
        till_number = str(
            getattr(settings, "MPESA_TILL_NUMBER", "") or ""
        ).strip()

        if not till_number:
            return {
                "success": False,
                "error": (
                    "M-Pesa is misconfigured: MPESA_TILL_NUMBER is required "
                    "for CustomerBuyGoodsOnline (Till) payments."
                ),
            }

        party_b = till_number
    else:
        party_b = business_shortcode

    # --- Authenticate ---
    access_token = get_mpesa_access_token()

    if not access_token:
        return {
            "success": False,
            "error": "Could not authenticate with M-Pesa.",
        }

    password, timestamp = generate_mpesa_password()

    url = (
        f"{settings.MPESA_BASE_URL}"
        "/mpesa/stkpush/v1/processrequest"
    )

    payload = {
        "BusinessShortCode": business_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": transaction_type,
        "Amount": int(amount),
        "PartyA": normalized_phone,
        "PartyB": party_b,
        "PhoneNumber": normalized_phone,
        "CallBackURL": callback_url,
        "AccountReference": str(account_reference)[:12],
        "TransactionDesc": str(transaction_description)[:20],
    }

    logger.info(
        "STK Push payload: BusinessShortCode=%s PartyB=%s "
        "TransactionType=%s Amount=%s Phone=%s",
        business_shortcode,
        party_b,
        transaction_type,
        int(amount),
        normalized_phone,
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        logger.info("STK Push raw Daraja response: %s", data)

        if data.get("ResponseCode") == "0":
            logger.info(
                "STK Push initiated. CheckoutRequestID=%s",
                data.get("CheckoutRequestID"),
            )

            return {
                "success": True,
                "data": data,
            }

        logger.warning("STK Push rejected: %s", data)

        return {
            "success": False,
            "error": data.get(
                "errorMessage",
                data.get(
                    "ResponseDescription",
                    "STK Push failed.",
                ),
            ),
            "data": data,
        }

    except requests.RequestException as exc:
        logger.exception("M-Pesa STK Push request failed.")

        response = getattr(exc, "response", None)
        if response is not None:
            logger.error(
                "Daraja STK Push HTTP error body: %s",
                response.text,
            )

        return {
            "success": False,
            "error": "Could not contact M-Pesa.",
        }
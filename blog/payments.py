# blog/payments.py

import base64
import logging
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_mpesa_access_token():
    """
    Obtain an OAuth access token from Safaricom Daraja.
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
        return data.get("access_token")

    except requests.RequestException:
        logger.exception("Failed to obtain M-Pesa access token.")
        return None


def normalize_mpesa_phone(phone):
    """
    Convert Kenyan phone numbers into Safaricom-compatible format:
    2547XXXXXXXX or 2541XXXXXXXX.
    """

    phone = str(phone).strip().replace(" ", "").replace("-", "")

    if phone.startswith("+254"):
        phone = phone[1:]

    elif phone.startswith("0"):
        phone = "254" + phone[1:]

    elif len(phone) == 9:
        phone = "254" + phone

    if (
        len(phone) != 12
        or not phone.startswith("254")
        or phone[3] not in ("7", "1")
        or not phone.isdigit()
    ):
        return None

    return phone


def generate_mpesa_password():
    """
    Generate the Daraja STK Push password.

    Password = Base64(Shortcode + Passkey + Timestamp)
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

    This only initiates a payment request.
    It does NOT confirm that payment has been made.
    """

    phone = normalize_mpesa_phone(phone)

    if not phone:
        return {
            "success": False,
            "error": "Invalid Kenyan phone number.",
        }

    amount = Decimal(str(amount))

    if amount <= 0 or amount != amount.to_integral_value():
        return {
            "success": False,
            "error": "Payment amount must be a positive whole number.",
        }

    if not callback_url.startswith("https://"):
        return {
            "success": False,
            "error": "A publicly accessible HTTPS callback URL is required.",
        }

    access_token = get_mpesa_access_token()

    if not access_token:
        return {
            "success": False,
            "error": "Could not authenticate with M-Pesa.",
        }

    password, timestamp = generate_mpesa_password()

    shortcode = str(settings.MPESA_SHORTCODE)

    url = (
        f"{settings.MPESA_BASE_URL}"
        "/mpesa/stkpush/v1/processrequest"
    )

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": str(account_reference)[:12],
        "TransactionDesc": str(transaction_description)[:20],
    }

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

        if data.get("ResponseCode") == "0":
            logger.info(
                "STK Push initiated. CheckoutRequestID=%s",
                data.get("CheckoutRequestID"),
            )

            return {
                "success": True,
                "data": data,
            }

        logger.warning(
            "STK Push rejected: %s",
            data,
        )

        return {
            "success": False,
            "error": data.get(
                "errorMessage",
                data.get("ResponseDescription", "STK Push failed."),
            ),
            "data": data,
        }

    except requests.RequestException:
        logger.exception("M-Pesa STK Push request failed.")

        return {
            "success": False,
            "error": "Could not contact M-Pesa.",
        }
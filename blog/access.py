
# blog/access.py

from .models import AttachmentPurchase


def user_has_paid_for_post(user, post, guest_token=None) -> bool:

    # 1. Free post → everyone entitled
    if (
        not post.is_monetized
        or not post.attachment_price
        or post.attachment_price <= 0
    ):
        return True

    # 2. Author / staff / superuser always allowed
    if user.is_authenticated:
        if user == post.author or user.is_staff or user.is_superuser:
            return True

    # 3. Registered buyer — only verified purchase counts
    if user.is_authenticated:
        if AttachmentPurchase.objects.filter(
            user=user,
            post=post,
            paid=True,
        ).exists():
            return True

    # 4. Guest buyer — only the same session token with verified purchase
    if guest_token:
        if AttachmentPurchase.objects.filter(
            guest_token=guest_token,
            post=post,
            paid=True,
        ).exists():
            return True

    return False


def user_can_download(user, attachment, guest_token=None) -> bool:

    """
    Per-attachment entitlement check.

    Paid attachments require a verified purchase.
    Guest purchasers are identified by their session token.
    Explicitly free attachments remain downloadable.
    """

    post = attachment.post

    # Free post → anyone reaching this view may download
    if (
        not post.is_monetized
        or not post.attachment_price
        or post.attachment_price <= 0
    ):
        return True

    # Author / staff / superuser → full access
    if user.is_authenticated:
        if user == post.author or user.is_staff or user.is_superuser:
            return True

    # Explicit free attachment on a paid post
    if attachment.is_free:
        return True

    # Registered purchaser
    if user.is_authenticated:
        if AttachmentPurchase.objects.filter(
            user=user,
            post=post,
            paid=True,
        ).exists():
            return True

    # Guest purchaser
    if guest_token:
        if AttachmentPurchase.objects.filter(
            guest_token=guest_token,
            post=post,
            paid=True,
        ).exists():
            return True

    # No verified purchase
    return False

# blog/access.py
from .models import AttachmentPurchase


def user_has_paid_for_post(user, post) -> bool:
    """
    True if `user` is entitled to ALL paid attachments on `post`.

    Entitlement rules (in order):
      1. Post is not monetized, or has no positive price  → free for all.
      2. Anonymous user                                    → not entitled.
      3. Author / staff / superuser                        → entitled.
      4. User has a VERIFIED (paid=True) purchase record   → entitled.
      5. Otherwise                                         → not entitled.
    """
    # 1. Free post → everyone entitled
    if not post.is_monetized or not post.attachment_price or post.attachment_price <= 0:
        return True

    # 2. Anonymous → never entitled to a paid post
    if not user.is_authenticated:
        return False

    # 3. Author / staff / superuser always allowed
    if user == post.author or user.is_staff or user.is_superuser:
        return True

    # 4. Only a *verified* purchase counts
    return AttachmentPurchase.objects.filter(
        user=user,
        post=post,
        paid=True,
    ).exists()


def user_can_download(user, attachment) -> bool:
    """
    Per-attachment entitlement check.

    IMPORTANT: monetization is evaluated FIRST. If the parent post is
    monetized, `attachment.is_free` is honoured only as an explicit
    opt-out set by the author — it can never silently bypass the paywall
    just because the model default was left as True.
    """
    post = attachment.post

    # Free post → anyone reaching this view may download
    if not post.is_monetized or not post.attachment_price or post.attachment_price <= 0:
        return True

    # Author / staff / superuser → full access
    if user.is_authenticated and (
        user == post.author or user.is_staff or user.is_superuser
    ):
        return True

    # Explicit free attachment on a paid post
    if attachment.is_free:
        return True

    # Otherwise must have paid
    return user_has_paid_for_post(user, post)
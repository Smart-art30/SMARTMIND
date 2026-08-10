
import markdown

from .models import ChatMessage


# ============================================================
# SAVE USER MESSAGE
# ============================================================

def save_user_message(user, message):
    """
    Save the learner's message.

    Learner messages are stored as plain text.
    """

    if user and user.is_authenticated:

        ChatMessage.objects.create(
            user=user,
            role="user",
            message=message,
        )


# ============================================================
# CONVERT AI MARKDOWN TO HTML
# ============================================================

def convert_ai_response_to_html(message):
    """
    Convert Gemini Markdown response into HTML suitable
    for CKEditor5Field.
    """

    if not message:
        return ""

    html = markdown.markdown(
        message,
        extensions=[
            "extra",
            "nl2br",
            "sane_lists",
        ],
    )

    return html


# ============================================================
# SAVE AI MESSAGE
# ============================================================

def save_ai_message(user, message):
    """
    Convert SmartMind's Markdown response to HTML
    and save it in the CKEditor5Field.
    """

    if user and user.is_authenticated:

        html_message = convert_ai_response_to_html(
            message
        )

        ChatMessage.objects.create(
            user=user,
            role="assistant",
            message=html_message,
        )


# ============================================================
# GET CONVERSATION
# ============================================================

def get_conversation(user, limit=10):
    """
    Return recent conversation as plain text.

    HTML stored in CKEditor5Field is stripped before
    being supplied to Gemini's conversation memory.
    """

    if not user or not user.is_authenticated:
        return ""


    messages = (
        ChatMessage.objects
        .filter(user=user)
        .order_by("-created_at")[:limit]
    )


    messages = list(messages)[::-1]


    conversation = []


    for msg in messages:

        speaker = "Student"

        if msg.role == "assistant":
            speaker = "SmartMind AI"


        # ----------------------------------------------------
        # Remove HTML from rich-text AI messages
        # ----------------------------------------------------

        if msg.role == "assistant":

            from django.utils.html import strip_tags

            clean_message = strip_tags(
                msg.message or ""
            )

        else:

            clean_message = msg.message or ""


        conversation.append(
            f"{speaker}: {clean_message}"
        )


    return "\n".join(conversation)

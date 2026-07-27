from .models import ChatMessage


def save_user_message(user, message):
    """
    Save the learner's message.
    """
    if user and user.is_authenticated:
        ChatMessage.objects.create(
            user=user,
            role="user",
            message=message,
        )


def save_ai_message(user, message):
    """
    Save SmartMind's reply.
    """
    if user and user.is_authenticated:
        ChatMessage.objects.create(
            user=user,
            role="assistant",
            message=message,
        )


def get_conversation(user, limit=10):
    """
    Return recent conversation as plain text.
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

        conversation.append(
            f"{speaker}: {msg.message}"
        )

    return "\n".join(conversation)
from .intents import detect_intent


def choose_tool(question):
    """
    Decide which SmartMind tool should answer.
    Returns:
        tool, intent
    """

    intent = detect_intent(question)

    tool_map = {
        "conversation": "chat",
        "greeting": "chat",
        "tutor": "tutor",
        "quiz": "quiz",
        "mark": "marker",
        "teacher": "teacher",
        "notes": "notes",
    }
    tool = tool_map.get(intent, "tutor")

    return tool, intent
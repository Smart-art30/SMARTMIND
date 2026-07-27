from library.models import Progress


def build_progress_context(user):
    """
    Build a summary of the learner's recent progress
    for the AI prompt.
    """

    if not user or not user.is_authenticated:
        return ""

    progress = (
        Progress.objects
        .filter(learner=user)
        .select_related("topic", "subtopic")
        .order_by("-date_completed", "-id")[:15]
    )

    if not progress.exists():
        return ""

    context = []

    for p in progress:

        topic = (
            p.topic.title
            if p.topic
            else "Unknown Topic"
        )

        subtopic = (
            p.subtopic.title
            if p.subtopic
            else "General"
        )

        status = (
            "Completed"
            if p.completed
            else "In Progress"
        )

        score = f"{p.score}%"

        context.append(f"""
TOPIC:
{topic}

SUBTOPIC:
{subtopic}

SCORE:
{score}

STATUS:
{status}
""")

    return "\n----------------------------------------\n".join(context)
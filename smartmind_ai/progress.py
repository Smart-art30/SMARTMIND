from library.models import LessonProgress


def build_progress_context(user):
    """
    Build a summary of the learner's recent lesson progress
    for the AI prompt.
    """

    if not user or not user.is_authenticated:
        return ""

    progress = (
        LessonProgress.objects
        .filter(learner=user)
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
        )
        .order_by("-last_accessed")[:15]
    )

    if not progress.exists():
        return ""

    context = []

    for p in progress:
        lesson = p.lesson
        subtopic = lesson.subtopic
        topic = subtopic.topic
        subject = topic.subject

        context.append(f"""
SUBJECT:
{subject.name}

TOPIC:
{topic.title}

SUBTOPIC:
{subtopic.title}

LESSON:
{lesson.title}

PROGRESS:
{p.percentage}%

STATUS:
{p.get_status_display()}
""")

    return "\n----------------------------------------\n".join(context)
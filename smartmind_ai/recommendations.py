from library.models import LessonProgress, Resource


def recommend_resources(user, limit=5):
    """
    Recommend resources from lessons the learner has not yet completed.
    """

    if not user or not user.is_authenticated:
        return Resource.objects.none()

    lesson_ids = (
        LessonProgress.objects
        .filter(
            learner=user,
            percentage__lt=100,
        )
        .values_list("lesson_id", flat=True)
    )

    return (
        Resource.objects
        .filter(lesson_id__in=lesson_ids)
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
        )[:limit]
    )


def build_recommendation_context(resources):
    """
    Build recommendation context for the AI.
    """

    if not resources:
        return ""

    text = []

    for resource in resources:
        lesson = resource.lesson
        subtopic = lesson.subtopic
        topic = subtopic.topic
        subject = topic.subject

        text.append(f"""
Recommended Resource

Title:
{resource.title}

Lesson:
{lesson.title}

Subtopic:
{subtopic.title}

Topic:
{topic.title}

Subject:
{subject.name}
""")

    return "\n".join(text)
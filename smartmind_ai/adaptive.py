from library.models import LessonProgress, Resource


def get_learning_recommendations(user):
    """
    Recommend resources from lessons that are not yet completed.
    """

    if not user or not user.is_authenticated:
        return []

    progress_records = (
        LessonProgress.objects
        .filter(
            learner=user,
            percentage__lt=100
        )
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
        )
    )

    recommendations = []

    for progress in progress_records:
        resources = (
            Resource.objects
            .filter(
                lesson=progress.lesson
            )
            .select_related(
                "lesson",
                "lesson__subtopic",
                "lesson__subtopic__topic",
                "lesson__subtopic__topic__subject",
            )[:3]
        )

        recommendations.extend(resources)

    return recommendations


def build_adaptive_context(user):
    """
    Build recommendation text for Gemini.
    """

    recommendations = get_learning_recommendations(user)

    if not recommendations:
        return ""

    context = []

    for resource in recommendations:
        lesson = resource.lesson
        subtopic = lesson.subtopic
        topic = subtopic.topic
        subject = topic.subject

        context.append(
            f"""
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
"""
        )

    return "\n--------------------------------\n".join(context)
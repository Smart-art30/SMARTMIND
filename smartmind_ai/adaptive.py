from library.models import Progress, Resource


def get_learning_recommendations(user):
    """
    Recommend what the learner should study next.
    """

    if not user or not user.is_authenticated:
        return []

    weak_topics = (
        Progress.objects
        .filter(
            learner=user,
            score__lt=60
        )
        .select_related("topic")
    )

    recommendations = []

    for progress in weak_topics:

        if progress.topic:

            lessons = Resource.objects.filter(
                topic=progress.topic
            )[:3]

            recommendations.extend(lessons)

    return recommendations


def build_adaptive_context(user):
    """
    Build recommendation text for Gemini.
    """

    recommendations = get_learning_recommendations(user)

    if not recommendations:
        return ""

    text = []

    for lesson in recommendations:

        text.append(f"""
Recommended Lesson

Title:
{lesson.title}

Topic:
{lesson.topic}

Subject:
{lesson.subject}
""")

    return "\n--------------------------------\n".join(text)
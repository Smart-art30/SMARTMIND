from library.models import ResourceView, Progress, Resource


def recommend_resources(user, limit=5):

    if not user or not user.is_authenticated:
        return []

    viewed = ResourceView.objects.filter(
        learner=user
    ).values_list(
        "resource_id",
        flat=True,
    )

    weak_topics = Progress.objects.filter(
        learner=user,
        score__lt=50,
    ).values_list(
        "topic_id",
        flat=True,
    )

    recommendations = (
        Resource.objects.filter(
            topic_id__in=weak_topics
        )
        .exclude(id__in=viewed)
        .select_related(
            "level",
            "subject",
            "topic",
        )[:limit]
    )

    return recommendations


def build_recommendation_context(resources):

    if not resources:
        return ""

    text = []

    for resource in resources:

        text.append(f"""
Recommended Lesson

Title:
{resource.title}

Subject:
{resource.subject}

Topic:
{resource.topic}
""")

    return "\n".join(text)
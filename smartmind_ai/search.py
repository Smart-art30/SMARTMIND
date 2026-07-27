from django.db.models import Q
from library.models import Resource

# Common words that do not help searching
STOP_WORDS = {
    "what", "who", "where", "when", "why", "how",
    "is", "are", "was", "were", "be", "being",
    "the", "a", "an",
    "of", "to", "for", "and", "or", "in", "on", "at",
    "can", "could", "would", "should",
    "please", "tell", "explain", "define", "describe",
    "show", "give", "me", "about", "with", "using",
}


def clean_query(question):
    """
    Convert a learner's question into useful search keywords.
    """

    if not question:
        return []

    words = []

    for word in question.lower().split():

        word = word.strip(
            ".,?!()[]{}:;'\""
        )

        if len(word) < 3:
            continue

        if word in STOP_WORDS:
            continue

        words.append(word)

    return list(dict.fromkeys(words))


def build_search_query(words):
    """
    Build a Django Q object.
    """

    query = Q()

    for word in words:

        query |= Q(title__icontains=word)
        query |= Q(description__icontains=word)

        query |= Q(subject__name__icontains=word)

        query |= Q(topic__title__icontains=word)
        query |= Q(topic__description__icontains=word)

        query |= Q(subtopic__title__icontains=word)
        query |= Q(subtopic__description__icontains=word)

    return query

def search_resources(
    question,
    learner_class=None,
    subject=None,
    limit=5,
):
    """
    Search SmartMind lesson resources.
    """

    queryset = (
        Resource.objects
        .select_related(
            "level",
            "subject",
            "topic",
            "subtopic",
        )
        .only(
            "id",
            "title",
            "description",
            "views",
            "created_at",
            "level__name",
            "subject__name",
            "topic__title",
            "topic__description",
            "subtopic__title",
            "subtopic__description",
        )
    )

    # Filter by learner level
    if learner_class:
        queryset = queryset.filter(
            level__name__icontains=learner_class
        )

    # Filter by subject
    if subject:
        queryset = queryset.filter(
            subject__name__icontains=subject
        )

    words = clean_query(question)

    if not words:
        return []

    query = build_search_query(words)

    resources = (
        queryset
        .filter(query)
        .distinct()
        .order_by("-views", "-created_at")[:limit]
    )

    return list(resources)


def build_context(resources):
    """
    Convert SmartMind resources into context for Gemini.
    """

    if not resources:
        return ""

    sections = []

    for resource in resources:

        level = resource.level.name if resource.level else "Unknown"
        subject = resource.subject.name if resource.subject else "Unknown"

        topic = (
            resource.topic.title
            if resource.topic
            else "Unknown"
        )

        subtopic = (
            resource.subtopic.title
            if resource.subtopic
            else "Unknown"
        )

        description = resource.description or ""

        sections.append(
f"""
==================================================

SMARTMIND LESSON

Title:
{resource.title}

Level:
{level}

Subject:
{subject}

Topic:
{topic}

Subtopic:
{subtopic}

Lesson Notes:

{description}

==================================================
"""
        )

    return "\n".join(sections)


def search_titles(question, limit=10):
    """
    Search lesson titles only.
    Useful for recommendations.
    """

    words = clean_query(question)

    query = Q()

    for word in words:
        query |= Q(title__icontains=word)

    return (
        Resource.objects
        .filter(query)
        .distinct()[:limit]
    )


def search_subject(subject_name):
    """
    Return all resources for a subject.
    """

    return (
        Resource.objects
        .filter(subject__name__icontains=subject_name)
        .select_related(
            "level",
            "subject",
            "topic",
            "subtopic",
        )
    )


def search_topic(topic_name):
    """
    Return all resources in a topic.
    """

    return (
        Resource.objects
        .filter(topic__title__icontains=topic_name)
        .select_related(
            "level",
            "subject",
            "topic",
            "subtopic",
        )
    )
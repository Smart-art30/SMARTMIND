from django.db.models import Q
from library.models import Resource


# ============================================================
# COMMON WORDS
# ============================================================

STOP_WORDS = {
    "what", "who", "where", "when", "why", "how",
    "is", "are", "was", "were", "be", "being",
    "the", "a", "an",
    "of", "to", "for", "and", "or", "in", "on", "at",
    "can", "could", "would", "should",
    "please", "tell", "explain", "define", "describe",
    "show", "give", "me", "about", "with", "using",
}


# ============================================================
# CLEAN SEARCH QUERY
# ============================================================

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

    # Remove duplicates while preserving order
    return list(dict.fromkeys(words))


# ============================================================
# BUILD SEARCH QUERY
# ============================================================

def build_search_query(words):
    """
    Build a Django Q object using the CURRENT
    SmartMind curriculum structure.

    Resource
        -> Lesson
            -> SubTopic
                -> Topic
                    -> Subject
                        -> CurriculumClass
                            -> Level
    """

    query = Q()

    for word in words:

        # Resource fields
        query |= Q(title__icontains=word)
        query |= Q(description__icontains=word)

        # Lesson
        query |= Q(
            lesson__title__icontains=word
        )

        query |= Q(
            lesson__introduction__icontains=word
        )

        query |= Q(
            lesson__learning_objectives__icontains=word
        )

        query |= Q(
            lesson__summary__icontains=word
        )

        # SubTopic
        query |= Q(
            lesson__subtopic__title__icontains=word
        )

        query |= Q(
            lesson__subtopic__description__icontains=word
        )

        # Topic
        query |= Q(
            lesson__subtopic__topic__title__icontains=word
        )

        query |= Q(
            lesson__subtopic__topic__description__icontains=word
        )

        # Subject
        query |= Q(
            lesson__subtopic__topic__subject__name__icontains=word
        )

        # Curriculum Class
        query |= Q(
            lesson__subtopic__topic__subject__curriculum_class__name__icontains=word
        )

        # Level
        query |= Q(
            lesson__subtopic__topic__subject__curriculum_class__level__name__icontains=word
        )

    return query


# ============================================================
# SEARCH RESOURCES
# ============================================================

def search_resources(
    question,
    learner_class=None,
    subject=None,
    limit=5,
):
    """
    Search SmartMind lesson resources.

    Uses the current relationship:

    Resource
        -> Lesson
        -> SubTopic
        -> Topic
        -> Subject
        -> CurriculumClass
        -> Level
    """

    queryset = (
        Resource.objects
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
            "lesson__subtopic__topic__subject__curriculum_class",
            "lesson__subtopic__topic__subject__curriculum_class__level",
        )
    )

    # --------------------------------------------------------
    # Filter by learner class
    # --------------------------------------------------------

    if learner_class:

        queryset = queryset.filter(
            lesson__subtopic__topic__subject__curriculum_class__name__icontains=learner_class
        )

    # --------------------------------------------------------
    # Filter by subject
    # --------------------------------------------------------

    if subject:

        queryset = queryset.filter(
            lesson__subtopic__topic__subject__name__icontains=subject
        )

    # --------------------------------------------------------
    # Clean learner question
    # --------------------------------------------------------

    words = clean_query(question)

    if not words:
        return []

    # --------------------------------------------------------
    # Build search query
    # --------------------------------------------------------

    query = build_search_query(words)

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    resources = (
        queryset
        .filter(query)
        .distinct()
        .order_by(
            "-views",
            "-created_at",
        )[:limit]
    )

    return list(resources)


# ============================================================
# BUILD GEMINI CONTEXT
# ============================================================

def build_context(resources):
    """
    Convert SmartMind resources into context for Gemini.
    """

    if not resources:
        return ""

    sections = []

    for resource in resources:

        # ----------------------------------------------------
        # Lesson
        # ----------------------------------------------------

        lesson = resource.lesson

        if lesson:
            lesson_title = lesson.title
        else:
            lesson_title = "Unknown"

        # ----------------------------------------------------
        # SubTopic
        # ----------------------------------------------------

        subtopic = None

        if lesson:
            subtopic = lesson.subtopic

        subtopic_title = (
            subtopic.title
            if subtopic
            else "Unknown"
        )

        # ----------------------------------------------------
        # Topic
        # ----------------------------------------------------

        topic = None

        if subtopic:
            topic = subtopic.topic

        topic_title = (
            topic.title
            if topic
            else "Unknown"
        )

        # ----------------------------------------------------
        # Subject
        # ----------------------------------------------------

        subject = None

        if topic:
            subject = topic.subject

        subject_name = (
            subject.name
            if subject
            else "Unknown"
        )

        # ----------------------------------------------------
        # Curriculum Class
        # ----------------------------------------------------

        curriculum_class = None

        if subject:
            curriculum_class = subject.curriculum_class

        class_name = (
            curriculum_class.name
            if curriculum_class
            else "Unknown"
        )

        # ----------------------------------------------------
        # Level
        # ----------------------------------------------------

        level = None

        if curriculum_class:
            level = curriculum_class.level

        level_name = (
            level.name
            if level
            else "Unknown"
        )

        # ----------------------------------------------------
        # Resource description
        # ----------------------------------------------------

        description = resource.description or ""

        # ----------------------------------------------------
        # Build context
        # ----------------------------------------------------

        sections.append(
            f"""
SMARTMIND LESSON

Resource:
{resource.title}

Lesson:
{lesson_title}

Level:
{level_name}

Class:
{class_name}

Subject:
{subject_name}

Topic:
{topic_title}

Subtopic:
{subtopic_title}

Lesson Notes:

{description}

==================================================
"""
        )

    return "\n".join(sections)


# ============================================================
# SEARCH RESOURCE TITLES
# ============================================================

def search_titles(question, limit=10):
    """
    Search lesson/resource titles only.

    Useful for recommendations.
    """

    words = clean_query(question)

    if not words:
        return []

    query = Q()

    for word in words:

        query |= Q(
            title__icontains=word
        )

        query |= Q(
            lesson__title__icontains=word
        )

        query |= Q(
            lesson__subtopic__title__icontains=word
        )

        query |= Q(
            lesson__subtopic__topic__title__icontains=word
        )

    return list(
        Resource.objects
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
        )
        .filter(query)
        .distinct()[:limit]
    )


# ============================================================
# SEARCH BY SUBJECT
# ============================================================

def search_subject(subject_name):
    """
    Return all resources belonging to a subject.
    """

    return (
        Resource.objects
        .filter(
            lesson__subtopic__topic__subject__name__icontains=subject_name
        )
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
            "lesson__subtopic__topic__subject__curriculum_class",
            "lesson__subtopic__topic__subject__curriculum_class__level",
        )
    )


# ============================================================
# SEARCH BY TOPIC
# ============================================================

def search_topic(topic_name):
    """
    Return all resources belonging to a topic.
    """

    return (
        Resource.objects
        .filter(
            lesson__subtopic__topic__title__icontains=topic_name
        )
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
            "lesson__subtopic__topic__subject__curriculum_class",
            "lesson__subtopic__topic__subject__curriculum_class__level",
        )
    )


# ============================================================
# SEARCH BY SUBTOPIC
# ============================================================

def search_subtopic(subtopic_name):
    """
    Return all resources belonging to a subtopic.
    """

    return (
        Resource.objects
        .filter(
            lesson__subtopic__title__icontains=subtopic_name
        )
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
        )
    )


# ============================================================
# SEARCH BY LESSON
# ============================================================

def search_lesson(lesson_name):
    """
    Return all resources belonging to a lesson.
    """

    return (
        Resource.objects
        .filter(
            lesson__title__icontains=lesson_name
        )
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
        )
    )

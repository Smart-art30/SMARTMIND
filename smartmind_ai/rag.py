from .search import search_resources, build_context

from .adaptive import build_adaptive_context
from .quiz import build_quiz_context
from .recommendations import (
    recommend_resources,
    build_recommendation_context,
)
from .progress import build_progress_context


def retrieve_context(question, user, learner_class, intent):
    """
    Retrieve SmartMind context using a lightweight Hybrid RAG.

    Strategy:
    1. Use keyword search first (fast).
    2. Only use vector search if keyword search finds nothing.
    3. Send at most 3 lessons to Gemini.
    """

    lesson_context = ""
    question_context = ""
    resources = []

    recommendation_context = ""
    progress_context = ""
    adaptive_context = ""

    # ---------------------------------------
    # Quiz Mode
    # ---------------------------------------

    if intent == "quiz":

        question_context = build_quiz_context(
            question,
            learner_class,
        )

    # ---------------------------------------
    # Lesson Retrieval
    # ---------------------------------------

    # ---------------------------------------
# Lesson Retrieval
# ---------------------------------------

else:

    # Step 1: Fast keyword search
    resources = search_resources(
        question=question,
        learner_class=learner_class,
    )[:3]

    # Step 2: Fall back to vector search only if needed
    if not resources:
        from .vector_search import vector_search

        resources = vector_search(
            question=question,
            limit=3,
        )

    # Step 3: Build lesson context
    lesson_context = build_context(resources)

    # ---------------------------------------
    # Personalisation (only for logged-in users)
    # ---------------------------------------

    if user and user.is_authenticated:

        recommendation_context = build_recommendation_context(
            recommend_resources(user)
        )

        progress_context = build_progress_context(user)

        adaptive_context = build_adaptive_context(user)

    # ---------------------------------------
    # Return
    # ---------------------------------------

    return {
        "resources": resources,
        "lesson_context": lesson_context,
        "question_context": question_context,
        "recommendation_context": recommendation_context,
        "progress_context": progress_context,
        "adaptive_context": adaptive_context,
    }
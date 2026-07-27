from .search import (
    search_resources,
    build_context,
)

from .question_search import (
    search_questions,
    build_question_context,
)


def build_teacher_context(question, learner_class=None):
    """
    Build SmartMind teaching context for Teacher AI.
    """

    resources = search_resources(
        question=question,
        learner_class=learner_class,
    )

    questions = search_questions(
        question=question,
        learner_class=learner_class,
    )

    lesson_context = build_context(resources)

    question_context = build_question_context(
        questions
    )

    return f"""
==================================================

SMARTMIND LESSONS

{lesson_context if lesson_context else "No matching lessons found."}

==================================================

SMARTMIND QUESTION BANK

{question_context if question_context else "No matching questions found."}
"""
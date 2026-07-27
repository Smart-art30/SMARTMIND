from .search import (
    search_resources,
    build_context,
)


def build_lesson_context(
    question,
    learner_class=None,
):

    lessons = search_resources(
        question=question,
        learner_class=learner_class,
    )

    return build_context(lessons)
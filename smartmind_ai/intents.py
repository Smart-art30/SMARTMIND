"""
SmartMind AI Intent Detection
"""

QUIZ_WORDS = {
    "quiz",
    "question",
    "questions",
    "mcq",
    "exercise",
    "test",
    "revision",
    "practice",
    "practice questions",
    "past paper",
}

MARK_WORDS = {
    "mark",
    "marking",
    "grade",
    "grading",
    "score",
    "evaluate",
    "check",
    "correct",
    "mark this",
    "check my answers",
    "mark my work",
}

NOTE_WORDS = {
    "summary",
    "summarize",
    "summarise",
    "notes",
    "revision notes",
    "short notes",
}

TEACHER_WORDS = {
    "teacher",
    "lesson plan",
    "lesson plans",
    "scheme",
    "scheme of work",
    "cbc",
    "rubric",
    "assessment",
    "exam",
    "exam paper",
    "test paper",
    "cat",
    "assignment",
    "homework",
    "marking scheme",
}

LESSON_WORDS = {
    "teach",
    "explain",
    "define",
    "what",
    "why",
    "how",
    "describe",
    "differentiate",
    "compare",
    "give examples",
    "meaning",
    "learn",
    "lesson",
}


def detect_intent(question):
    """
    Detect the learner's intent.
    """

    if not question:
        return "tutor"

    q = question.lower().strip()

    # -------------------------
    # Teacher AI
    # -------------------------
    if any(word in q for word in TEACHER_WORDS):
        return "teacher"

    # -------------------------
    # AI Marking
    # -------------------------
    if any(word in q for word in MARK_WORDS):
        return "mark"

    # -------------------------
    # Quiz AI
    # -------------------------
    if any(word in q for word in QUIZ_WORDS):
        return "quiz"

    # -------------------------
    # Notes AI
    # -------------------------
    if any(word in q for word in NOTE_WORDS):
        return "notes"

    # -------------------------
    # Tutor AI
    # -------------------------
    if any(word in q for word in LESSON_WORDS):
        return "tutor"

    # -------------------------
    # Default
    # -------------------------
    return "tutor"
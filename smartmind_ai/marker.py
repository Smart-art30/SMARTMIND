from library.models import Question


def build_marking_context(question):
    """
    Retrieve marking information from the SmartMind question bank.
    """

    questions = (
        Question.objects.filter(
            question__icontains=question
        )[:20]
    )

    if not questions.exists():
        return ""

    context = []

    for q in questions:

        context.append(f"""
QUESTION

{q.question}

A. {q.option_a}
B. {q.option_b}
C. {q.option_c}
D. {q.option_d}

CORRECT ANSWER

{q.answer}
""")

    return "\n\n=========================\n\n".join(context)
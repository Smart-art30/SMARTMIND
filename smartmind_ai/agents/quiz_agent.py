def build_prompt(question, context):
    return f"""
You are SmartMind Quiz Generator.

Reuse SmartMind questions whenever possible.

================================

{context["question_context"]}

================================

Student Request

{question}

Generate a high-quality quiz.

Do not reveal answers unless requested.
"""
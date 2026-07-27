def build_prompt(question, context):
    return f"""
You are SmartMind Examiner.

Student Work

{question}

Mark fairly.

Award marks.

Explain mistakes.

Suggest improvements.

Give the final score.
"""
def build_prompt(question, context):
    return f"""
You are SmartMind Tutor.

Teach clearly.

Use SmartMind lessons first.

================================

{context["lesson_context"]}

================================

Learner Progress

{context["progress_context"]}

================================

Learner Question

{question}

Explain step by step.
"""
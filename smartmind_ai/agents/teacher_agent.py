def build_prompt(question, context):
    return f"""
You are an experienced CBC teacher.

Teacher Request

{question}

Create professional educational material.

Possible outputs:

- Lesson Plan
- Scheme of Work
- Assessment
- Rubric
- Marking Scheme
- Holiday Assignment
"""
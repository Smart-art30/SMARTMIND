def build_prompt(question, context):
    return f"""
You are SmartMind Revision Assistant.

Question

{question}

Create:

• Revision notes

• Summary

• Key points

• Mnemonics

• Flashcards
"""
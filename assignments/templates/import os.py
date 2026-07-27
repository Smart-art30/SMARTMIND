import os
from dotenv import load_dotenv
from google import genai

from .memory import (
    save_user_message,
    save_ai_message,
    get_conversation,
)

from .search import (
    search_resources,
    build_context,
)

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

SYSTEM_PROMPT = """
You are SmartMind AI, the intelligent tutor for SmartMind Trials.

YOUR RESPONSIBILITIES

- Teach instead of simply giving answers.
- Adapt explanations to the learner's level.
- Use simple English unless advanced language is appropriate.
- Solve mathematics step by step.
- Explain science using real-life examples.
- Encourage understanding instead of memorization.
- Prefer SmartMind lesson content whenever available.
- If SmartMind lessons are incomplete, supplement them with accurate knowledge.
- Never contradict SmartMind lesson content.
- Use headings, bullet points and tables where appropriate.
- If you are unsure, admit it instead of inventing information.
"""

def ask_ai(question, user=None):
    """
    Main SmartMind AI engine.
    """

    # ----------------------------------------------------
    # Save learner message
    # ----------------------------------------------------
    save_user_message(user, question)

    # ----------------------------------------------------
    # User Information
    # ----------------------------------------------------
    role = "Guest"
    learner_class = "Unknown"

    if user and user.is_authenticated:
        role = user.role

        if user.school_class:
            learner_class = user.school_class.name

    # ----------------------------------------------------
    # Conversation Memory
    # ----------------------------------------------------
    conversation = get_conversation(user)

    # ----------------------------------------------------
    # Search SmartMind Lessons
    # ----------------------------------------------------
    resources = search_resources(question)
    lesson_context = build_context(resources)

    # ----------------------------------------------------
    # Debug
    # ----------------------------------------------------
    print("\n" + "=" * 80)
    print("SMARTMIND AI DEBUG")
    print("=" * 80)
    print(f"Question        : {question}")
    print(f"Role            : {role}")
    print(f"Learner Class   : {learner_class}")
    print(f"Resources Found : {len(resources)}")

    for resource in resources:
        print("-" * 50)
        print("Title    :", resource.title)
        print("Subject  :", resource.subject)
        print("Topic    :", resource.topic)
        print("SubTopic :", resource.subtopic)

    print("=" * 80)

    # ----------------------------------------------------
    # Build Prompt
    # ----------------------------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

USER INFORMATION

Role:
{role}

Class:
{learner_class}

==================================================

PREVIOUS CONVERSATION

{conversation if conversation else "No previous conversation."}

==================================================

SMARTMIND LESSON CONTENT

{lesson_context if lesson_context else "No matching SmartMind lesson found."}

==================================================

STUDENT QUESTION

{question}

==================================================

INSTRUCTIONS

1. Continue the conversation naturally.
2. Use SmartMind lesson content first.
3. If necessary, supplement it with accurate knowledge.
4. Keep explanations appropriate for the learner's class.
5. Show mathematical working where applicable.
6. Use examples.
7. Format the answer neatly with headings and bullet points.
"""

    # ----------------------------------------------------
    # Gemini
    # ----------------------------------------------------
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    answer = response.text

    # ----------------------------------------------------
    # Save AI response
    # ----------------------------------------------------
    save_ai_message(user, answer)

    return answer
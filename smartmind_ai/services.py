import os
from dotenv import load_dotenv
from google import genai
from .agent import choose_tool
from .memory import (
    save_user_message,
    save_ai_message,
    get_conversation,
)
from .rag import retrieve_context

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

SYSTEM_PROMPT = """
You are SmartMind AI, the official tutor for SmartMind Trials.

Use SmartMind lessons first.
Teach clearly.
Adapt to the learner's level.
Explain step by step.
If no lesson exists, answer using accurate knowledge.
"""

# Move constant outside function to avoid recreation
SIMPLE_REPLIES = {
    "hi": "Hello! 👋 I'm SmartMind AI. How can I help you today?",
    "hello": "Hello! 👋 What would you like to learn today?",
    "hey": "Hi! 👋 Ask me any learning question.",
    "thanks": "You're welcome! 😊",
    "thank you": "You're welcome! 😊",
    "ok": "Alright! What would you like to learn next?",
    "okay": "Alright! What would you like to learn next?",
}

TOOL_PROMPTS = {
    "tutor": """
You are acting as a SmartMind Tutor.

Teach the learner step by step.
Focus on understanding.
""",
    "quiz": """
You are acting as a SmartMind Quiz Generator.

Reuse SmartMind questions whenever possible.

If necessary, generate new CBC-style questions.
Do not reveal answers unless requested.
""",
    "teacher": """
You are acting as a Teacher Assistant.

Help teachers create:

- Lesson Plans
- Schemes of Work
- Exams
- Marking Schemes
- Rubrics
- CBC Assessments

Produce professional educational documents.
""",
    "marker": """
You are acting as an AI Examiner.

Mark learner work carefully.

Award marks fairly.

Explain mistakes.

Suggest improvements.

Give constructive feedback.
""",
    "notes": """
You are acting as a Revision Assistant.

Create:

- Revision Notes
- Summaries
- Flashcards
- Key Points
- Mnemonics

Keep them clear and easy to revise.
""",
}

NEEDS_RAG_TOOLS = frozenset(("tutor", "quiz", "notes"))



def _build_prompt(
    question,
    role,
    learner_class,
    conversation,
    intent,
    tool,
    lesson_context,
    question_context,
):

    parts = [
        SYSTEM_PROMPT,
        f"Role: {role}",
        f"Class: {learner_class or 'Unknown'}",
        f"Tool: {tool}",
        TOOL_PROMPTS.get(tool, ""),
    ]

    if conversation:
        parts.append(
            f"Previous Conversation:\n{conversation}"
        )

    if lesson_context:
        parts.append(
            f"SmartMind Lesson:\n{lesson_context}"
        )

    if question_context:
        parts.append(
            f"Question Bank:\n{question_context}"
        )

    parts.append(f"Student Question:\n{question}")

    parts.append("""
Instructions:

- Use SmartMind lessons first.
- If unavailable, answer using your own knowledge.
- Explain clearly.
- Show maths step by step.
""")

    return "\n\n".join(parts)

def ask_ai(question: str, user=None) -> str:
    """
    Main SmartMind AI Orchestrator — Optimized for performance.
    """
    # -----------------------------------
    # Fast path for simple greetings
    # -----------------------------------
    question_lower = question.lower().strip()
    reply = SIMPLE_REPLIES.get(question_lower)
    
    if reply:
        return reply
    
    # -----------------------------------
    # Save learner message (always)
    # -----------------------------------
    save_user_message(user, question)
    
    # -----------------------------------
    # User Information (cached access)
    # -----------------------------------
    role = "Guest"
    learner_class = None
    
    if user and user.is_authenticated:
        role = user.role
        if user.school_class:
            learner_class = user.school_class.name
    
    # -----------------------------------
    # Conversation Memory
    # -----------------------------------
    conversation = ""
    if user and user.is_authenticated:
        conversation = get_conversation(user, limit=1)
    
    # -----------------------------------
    # Detect Intent (fast lookup)
    # -----------------------------------
    tool, intent = choose_tool(question)
    
    # -----------------------------------
    # Retrieve SmartMind Context (RAG)
    # -----------------------------------
    # Only retrieve when needed — avoid unnecessary DB/ES queries
    words = question.split()
    should_retrieve_rag = len(words) >= 3 and tool in NEEDS_RAG_TOOLS
    
    if should_retrieve_rag:
        context = retrieve_context(
        question=question,
        user=user,
        learner_class=learner_class,
        intent=intent,
    )
        resources = context.get("resources", [])
        lesson_context = context.get("lesson_context", "")
        question_context = context.get("question_context", "")
        recommendation_context = context.get("recommendation_context", "")
        progress_context = context.get("progress_context", "")
        adaptive_context = context.get("adaptive_context", "")
    else:
        resources = []
        lesson_context = ""
        question_context = ""
        recommendation_context = ""
        progress_context = ""
        adaptive_context = ""
    
    # -----------------------------------
    # Build Prompt (extracted function)
    # -----------------------------------
    prompt = _build_prompt(
        question, role, learner_class, conversation, intent, tool,
        lesson_context, question_context, 
        
    )
    
    # -----------------------------------
    # Optional: Debug logging (production: remove or use logger)
    # -----------------------------------
    # Only log in development, not production
    # if settings.DEBUG:
    #     print(f"\n[SmartMind] Tool: {tool}, Intent: {intent}, RAG: {should_retrieve_rag}")
    
    # -----------------------------------
    # Gemini API Call
    # -----------------------------------
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        answer = response.text.strip()
    except Exception as e:
        answer = (
            "Sorry, SmartMind AI is temporarily unavailable.\n\n"
            f"Technical details:\n{str(e)}"
        )
    
    # -----------------------------------
    # Save AI Response
    # -----------------------------------
    save_ai_message(user, answer)
    
    return answer
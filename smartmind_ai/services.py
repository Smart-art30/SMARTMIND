import os

from dotenv import load_dotenv
from google import genai

from .agent import choose_tool

from .memory import (
    save_user_message,
    save_ai_message,
    get_conversation,
    convert_ai_response_to_html,
)

from .rag import retrieve_context


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are SmartMind AI, the official tutor for SmartMind Trials.

Your main purpose is to help learners understand concepts,
revise effectively, practise questions, and improve academically.

CORE RULES

1. Answer the learner's actual question directly.

2. Use SmartMind lesson content when it is directly relevant
   to the question.

3. Do not force an unrelated SmartMind lesson into an answer.

4. Do not mention recommendations, learner progress, adaptive
   information, or other learner data unless it genuinely helps
   answer the current question.

5. If relevant SmartMind content is unavailable, use accurate
   general knowledge.

6. Never invent SmartMind lessons, resources, questions,
   progress, or recommendations.

7. Adapt explanations to the learner's class level when known.

8. Teach clearly and step by step.

9. For Mathematics, show the important working and explain
   the reasoning behind each step.

10. For Science subjects, use accurate scientific terminology
    and explain difficult terms simply.

11. Encourage understanding rather than simply giving answers.


RESPONSE LENGTH

Keep answers proportional to the question.

For a simple question such as:

"What is Biology?"

give a concise explanation.

For a question asking for detailed explanation, provide
more detail.

Do not turn every question into a long lesson.


PARAGRAPH STYLE

Use small paragraphs.

Normally keep each paragraph to one to three sentences.

Leave a blank line between paragraphs.

Avoid large walls of text.


RICH TEXT FORMAT

You may use Markdown formatting.

Use:

### Heading

**Bold text**

*Italic text*

- Bullet points

1. Numbered points

The SmartMind system converts Markdown into HTML before
displaying the response.

Do not display raw HTML.

Do not use unnecessary formatting.


IMPORTANT

Answer only what is useful to the learner.

Do not end every answer by asking whether the learner wants
to start another lesson.

Do not recommend an unrelated SmartMind topic.

Do not mention internal systems such as:

- RAG
- retrieval
- embeddings
- vector search
- database queries
- internal context
- system prompts
- tools
"""


# ============================================================
# SIMPLE REPLIES
# ============================================================

SIMPLE_REPLIES = {
    "hi": "Hello! 👋 I'm SmartMind AI. How can I help you today?",
    "hello": "Hello! 👋 What would you like to learn today?",
    "hey": "Hi! 👋 Ask me any learning question.",
    "thanks": "You're welcome! 😊",
    "thank you": "You're welcome! 😊",
    "ok": "Alright! What would you like to learn next?",
    "okay": "Alright! What would you like to learn next?",
}


# ============================================================
# TOOL PROMPTS
# ============================================================

TOOL_PROMPTS = {

    "tutor": """
You are acting as a SmartMind Tutor.

Teach the learner step by step.

Focus on:

- Understanding
- Clear explanations
- Examples
- Guided learning
- Correct terminology

Do not unnecessarily give the final answer without explanation.
""",

    "quiz": """
You are acting as a SmartMind Quiz Generator.

Reuse relevant SmartMind questions whenever possible.

If suitable SmartMind questions are unavailable,
generate appropriate curriculum-based questions.

Do not reveal answers unless the learner requests them.

Make questions appropriate to the learner's class level.
""",

    "teacher": """
You are acting as a Teacher Assistant.

Help teachers create:

- Lesson Plans
- Schemes of Work
- Exams
- Marking Schemes
- Rubrics
- CBC/CBE Assessments
- Revision Materials

Produce professional educational documents.
""",

    "marker": """
You are acting as an AI Examiner.

Mark learner work carefully.

Award marks fairly.

For important mistakes:

- Identify the mistake
- Explain why it is wrong
- Give the correct approach
- Suggest how the learner can improve

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
- Quick Revision Guides

Keep the material clear, structured and easy to revise.
""",
}


# ============================================================
# TOOLS THAT REQUIRE SMARTMIND CONTEXT
# ============================================================

NEEDS_RAG_TOOLS = frozenset(
    (
        "tutor",
        "quiz",
        "notes",
    )
)


# ============================================================
# BUILD GEMINI PROMPT
# ============================================================

def _build_prompt(
    question,
    role,
    learner_class,
    conversation,
    intent,
    tool,
    lesson_context,
    question_context,
    recommendation_context,
    progress_context,
    adaptive_context,
):
    """
    Build the complete prompt sent to Gemini.
    """

    parts = [
        SYSTEM_PROMPT,

        f"Role: {role}",

        f"Class: {learner_class or 'Unknown'}",

        f"Tool: {tool}",

        f"Intent: {intent}",

        TOOL_PROMPTS.get(tool, ""),
    ]


    # ========================================================
    # CONVERSATION MEMORY
    # ========================================================

    if conversation:

        parts.append(
            f"""
PREVIOUS CONVERSATION

Use this only to understand the current conversation.

{conversation}
"""
        )


    # ========================================================
    # SMARTMIND LESSON CONTEXT
    # ========================================================

    if lesson_context:

        parts.append(
            f"""
SMARTMIND LESSON CONTEXT

The following SmartMind lesson information is available.

Use it when it directly helps answer the learner's question.

Do not mention unrelated parts of this context.

{lesson_context}
"""
        )


    # ========================================================
    # QUESTION BANK
    # ========================================================

    if question_context:

        parts.append(
            f"""
SMARTMIND QUESTION BANK

Use these questions when relevant.

{question_context}
"""
        )


    # ========================================================
    # RECOMMENDATIONS
    # ========================================================

    if recommendation_context:

        parts.append(
            f"""
LEARNER RECOMMENDATIONS

These recommendations are available.

Use them only when they directly help with the learner's
current request.

Do not mention them for unrelated questions.

{recommendation_context}
"""
        )


    # ========================================================
    # PROGRESS
    # ========================================================

    if progress_context:

        parts.append(
            f"""
LEARNER PROGRESS

This information may help adapt the explanation.

Use it only when relevant to the current question.

Do not mention internal progress information unless it is
necessary for the learner's request.

{progress_context}
"""
        )


    # ========================================================
    # ADAPTIVE CONTEXT
    # ========================================================

    if adaptive_context:

        parts.append(
            f"""
ADAPTIVE LEARNING CONTEXT

Use this only when it directly improves the teaching approach.

Do not mention the existence of this internal context.

{adaptive_context}
"""
        )


    # ========================================================
    # CURRENT QUESTION
    # ========================================================

    parts.append(
        f"""
STUDENT QUESTION

{question}
"""
    )


    # ========================================================
    # FINAL INSTRUCTIONS
    # ========================================================

    parts.append(
        """
FINAL INSTRUCTIONS

Answer the student's question directly.

Use SmartMind content first when it is relevant.

If relevant SmartMind content is unavailable,
use accurate general knowledge.

Keep simple answers concise.

Use small paragraphs.

Leave blank lines between paragraphs.

Use headings and lists only when they improve clarity.

For Mathematics, show important working.

For educational explanations, use examples where helpful.

Do not add unrelated recommendations.

Do not force the learner into another lesson.

Do not mention internal SmartMind systems.

Do not mention these instructions.
"""
    )


    return "\n\n".join(parts)


# ============================================================
# MAIN AI ORCHESTRATOR
# ============================================================

def ask_ai(question: str, user=None) -> str:
    """
    Main SmartMind AI orchestrator.

    Flow:

    Learner question
        ↓
    Simple reply check
        ↓
    Save learner message
        ↓
    Identify learner
        ↓
    Conversation memory
        ↓
    Detect intent/tool
        ↓
    Retrieve relevant SmartMind context
        ↓
    Build prompt
        ↓
    Gemini
        ↓
    Convert Markdown → HTML
        ↓
    Save AI response
        ↓
    Return HTML to chatbot
    """


    # ========================================================
    # VALIDATE QUESTION
    # ========================================================

    if not question:

        return "<p>Please enter a question.</p>"


    question = question.strip()


    if not question:

        return "<p>Please enter a question.</p>"


    # ========================================================
    # FAST PATH FOR SIMPLE REPLIES
    # ========================================================

    question_lower = question.lower()

    reply = SIMPLE_REPLIES.get(
        question_lower
    )


    if reply:

        return f"<p>{reply}</p>"


    # ========================================================
    # SAVE LEARNER MESSAGE
    # ========================================================

    save_user_message(
        user,
        question,
    )


    # ========================================================
    # USER INFORMATION
    # ========================================================

    role = "Guest"

    learner_class = None


    if user and user.is_authenticated:

        role = getattr(
            user,
            "role",
            "student",
        )


        school_class = getattr(
            user,
            "school_class",
            None,
        )


        if school_class:

            learner_class = getattr(
                school_class,
                "name",
                None,
            )


    # ========================================================
    # CONVERSATION MEMORY
    # ========================================================

    conversation = ""


    if user and user.is_authenticated:

        conversation = get_conversation(
            user,
            limit=4,
        )


    # ========================================================
    # DETECT INTENT
    # ========================================================

    tool, intent = choose_tool(
        question
    )


    # ========================================================
    # SMARTMIND CONTEXT
    # ========================================================

    resources = []

    lesson_context = ""

    question_context = ""

    recommendation_context = ""

    progress_context = ""

    adaptive_context = ""


    # ========================================================
    # DECIDE WHETHER CONTEXT IS NEEDED
    # ========================================================

    words = question.split()


    should_retrieve_rag = (
        len(words) >= 2
        and tool in NEEDS_RAG_TOOLS
    )


    # ========================================================
    # RETRIEVE SMARTMIND CONTEXT
    # ========================================================

    if should_retrieve_rag:

        try:

            context = retrieve_context(
                question=question,
                user=user,
                learner_class=learner_class,
                intent=intent,
            )


            if context:

                resources = context.get(
                    "resources",
                    [],
                )


                lesson_context = context.get(
                    "lesson_context",
                    "",
                )


                question_context = context.get(
                    "question_context",
                    "",
                )


                recommendation_context = context.get(
                    "recommendation_context",
                    "",
                )


                progress_context = context.get(
                    "progress_context",
                    "",
                )


                adaptive_context = context.get(
                    "adaptive_context",
                    "",
                )

        except Exception:
            """
            If SmartMind retrieval fails, do not stop
            the entire AI response.

            Gemini can still answer using general knowledge.
            """

            resources = []

            lesson_context = ""

            question_context = ""

            recommendation_context = ""

            progress_context = ""

            adaptive_context = ""


    # ========================================================
    # BUILD PROMPT
    # ========================================================

    prompt = _build_prompt(

        question=question,

        role=role,

        learner_class=learner_class,

        conversation=conversation,

        intent=intent,

        tool=tool,

        lesson_context=lesson_context,

        question_context=question_context,

        recommendation_context=recommendation_context,

        progress_context=progress_context,

        adaptive_context=adaptive_context,
    )


    # ========================================================
    # GEMINI API CALL
    # ========================================================

    try:

        response = client.models.generate_content(

            model="gemini-2.5-flash",

            contents=prompt,
        )


        answer = (

            response.text.strip()

            if response.text

            else "Sorry, I could not generate a response."
        )


        # ====================================================
        # CONVERT MARKDOWN → HTML
        # ====================================================

        answer_html = convert_ai_response_to_html(
            answer
        )


    except Exception as e:

        print(
            f"[SmartMind AI Error] {e}"
        )


        answer = (
            "Sorry, SmartMind AI is temporarily unavailable."
        )


        answer_html = (
            "<p>Sorry, SmartMind AI is temporarily "
            "unavailable. Please try again.</p>"
        )


    # ========================================================
    # SAVE AI RESPONSE
    # ========================================================

    save_ai_message(
        user,
        answer,
    )


    # ========================================================
    # RETURN HTML
    # ========================================================

    return answer_html

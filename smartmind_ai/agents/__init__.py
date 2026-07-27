from .tutor_agent import build_prompt as tutor_agent
from .quiz_agent import build_prompt as quiz_agent
from .teacher_agent import build_prompt as teacher_agent
from .marker_agent import build_prompt as marker_agent
from .notes_agent import build_prompt as notes_agent


def get_agent_prompt(tool, question, context):
    agents = {
        "tutor": tutor_agent,
        "quiz": quiz_agent,
        "teacher": teacher_agent,
        "marker": marker_agent,
        "notes": notes_agent,
    }

    builder = agents.get(tool, tutor_agent)
    return builder(question, context)
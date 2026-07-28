from .search import search_resources, build_context
from .adaptive import build_adaptive_context
from .quiz import build_quiz_context
from .recommendations import (
    recommend_resources,
    build_recommendation_context,
)
from .progress import build_progress_context


def retrieve_context(question, user, learner_class, intent):
    """
    Retrieve SmartMind context using a lightweight Hybrid RAG.
    """
    lesson_context = ""
    question_context = ""
    resources = []
    
    recommendation_context = ""
    progress_context = ""
    adaptive_context = ""
    
    # Quiz Mode
    if intent == "quiz":
        question_context = build_quiz_context(
            question,
            learner_class,
        )
    
    # Lesson Retrieval
    else:
        # Step 1: Keyword search
        resources = search_resources(
            question=question,
            learner_class=learner_class,
        )[:3]
        
        # Step 2: Vector search only if keyword search returns insufficient results
        if len(resources) < 3:
            # Implement your vector search here
            # vector_results = vector_search_resources(question, learner_class)
            # resources.extend(vector_results[:3 - len(resources)])
            pass
        
        # Step 3: Build lesson context
        lesson_context = build_context(resources)
    
    # Personalisation
    if user and user.is_authenticated:
        recommendation_context = build_recommendation_context(
            recommend_resources(user)
        )
        progress_context = build_progress_context(user)
        adaptive_context = build_adaptive_context(user)
    
    return {
        "resources": resources,
        "lesson_context": lesson_context,
        "question_context": question_context,
        "recommendation_context": recommendation_context,
        "progress_context": progress_context,
        "adaptive_context": adaptive_context,
    }
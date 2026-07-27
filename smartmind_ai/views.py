from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .services import ask_ai
@csrf_exempt
@require_POST
def chat(request):
    try:
        data = json.loads(request.body or "{}")
        question = data.get("message", "").strip()

        if not question:
            return JsonResponse({
                "reply": "Please enter a message."
            })

        user = request.user if request.user.is_authenticated else None

        answer = ask_ai(question=question, user=user)

        if not answer:
            answer = "Sorry, I couldn't generate a response."

        return JsonResponse({
            "reply": str(answer)
        })

    except Exception as e:
        # IMPORTANT: log real error
        print("CHAT ERROR:", str(e))

        return JsonResponse({
            "reply": "Sorry, something went wrong while processing your request."
        })
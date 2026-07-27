import os

from dotenv import load_dotenv
from google import genai

from library.models import Resource

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def create_embedding(text):

    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
    )

    return response.embeddings[0].values


def embed_resource(resource):

    text = f"""

Title

{resource.title}

Description

{resource.description}

Topic

{resource.topic}

Subtopic

{resource.subtopic}
"""

    resource.embedding = create_embedding(text)

    resource.save(update_fields=["embedding"])
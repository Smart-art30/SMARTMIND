import numpy as np

_MODEL = None


def get_model():
    global _MODEL

    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")

    return _MODEL


def build_resource_text(resource):
    """
    Convert a Resource into searchable text.
    """

    parts = []

    if resource.subject:
        parts.append(f"Subject: {resource.subject.name}")

    if resource.topic:
        parts.append(f"Topic: {resource.topic.title}")

    if resource.subtopic:
        parts.append(f"Subtopic: {resource.subtopic.title}")

    if resource.title:
        parts.append(f"Title: {resource.title}")

    if resource.description:
        parts.append(f"Description: {resource.description}")

    if resource.content:
        parts.append(f"Content: {resource.content}")

    return "\n\n".join(parts)


def create_embedding(text):
    model = get_model()

    vector = model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return np.asarray(vector, dtype="float32")


def embed_resource(resource):
    """
    Create an embedding for one Resource.
    """

    text = build_resource_text(resource)

    return create_embedding(text)
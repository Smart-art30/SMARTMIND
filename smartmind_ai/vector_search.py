import os
import pickle

import faiss
import numpy as np

from library.models import Resource

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INDEX_DIR = os.path.join(BASE_DIR, "index")

INDEX_FILE = os.path.join(INDEX_DIR, "smartmind.index")
RESOURCE_FILE = os.path.join(INDEX_DIR, "resources.pkl")

# Cosine similarity threshold
SIMILARITY_THRESHOLD = 0.45

index = None
resource_ids = []


def load_index():
    global index
    global resource_ids

    if index is not None:
        return

    index = faiss.read_index(INDEX_FILE)

    with open(RESOURCE_FILE, "rb") as f:
        resource_ids = pickle.load(f)

    # Debug: check what is stored in resources.pkl
    print("\n" + "=" * 60)
    print("VECTOR INDEX DEBUG")
    print("=" * 60)

    if resource_ids:
        print("First item :", resource_ids[0])
        print("Type       :", type(resource_ids[0]))
    else:
        print("resources.pkl is empty.")

    print("=" * 60 + "\n")


def vector_search(question, limit=5):
    """
    Semantic search using FAISS cosine similarity.
    """

    load_index()

    # Create query embedding
    vector = create_embedding(question).astype(np.float32)

    # Reshape for FAISS
    vector = vector.reshape(1, -1)

    # Normalize query vector
    faiss.normalize_L2(vector)

    # Search
    scores, ids = index.search(vector, limit)

    results = []

    print("\n========== VECTOR SEARCH ==========")

    for score, idx in zip(scores[0], ids[0]):

        if idx == -1:
            continue

        print(f"Similarity: {score:.3f}")

        if score < SIMILARITY_THRESHOLD:
            print("Rejected (below threshold)")
            continue

        try:
            resource_ref = resource_ids[idx]

            # Handle both IDs and Resource objects
            if isinstance(resource_ref, Resource):
                resource = resource_ref
            else:
                resource = Resource.objects.select_related(
                    "subject",
                    "topic",
                    "subtopic",
                ).get(id=resource_ref)

            print(f"Accepted -> {resource.title}")

            results.append(resource)

        except Resource.DoesNotExist:
            print(f"Resource not found: {resource_ref}")
            continue

    print(f"Returned {len(results)} resources")
    print("===================================\n")

    return results
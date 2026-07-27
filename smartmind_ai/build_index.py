import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from library.models import Resource

model = SentenceTransformer("all-MiniLM-L6-v2")


def get_text(resource):
    return (
        getattr(resource, "content", None)
        or getattr(resource, "description", None)
        or getattr(resource, "text", None)
        or getattr(resource, "body", None)
        or getattr(resource, "lesson", None)
        or ""
    )


def build_index():
    resources = Resource.objects.all()

    texts = []
    valid_resources = []

    for r in resources:
        text = get_text(r)

        if text and text.strip():
            texts.append(text)
            valid_resources.append(r)
        else:
            print(f"Skipping {r}")

    if not texts:
        print("No embeddings generated.")
        return

    print(f"Embedding {len(texts)} resources...")

    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, "smartmind_ai/index/smartmind.index")

    with open("smartmind_ai/index/resources.pkl", "wb") as f:
        pickle.dump([r.id for r in valid_resources], f)
        

    

    print("Index built successfully.")
import openai
import yaml
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from starlette.concurrency import run_in_threadpool
import asyncio

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

YAML_PATH = "services/create_rag/events.yaml"
CACHE_PATH = "services/create_rag/image_embeddings.npz"

# Load YAML data
def load_events(yaml_path):
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


# Embed list of texts with OpenAI (batched)
def get_embeddings(texts, model="text-embedding-3-small"):
    texts = [text.replace("\n", " ") for text in texts]
    response = openai.embeddings.create(input=texts, model=model)
    return np.array([r.embedding for r in response.data])

# Generate or load cached embeddings
def generate_or_load_embeddings(events, cache_path):
    if os.path.exists(cache_path):
        print("✅ Loading cached embeddings...")
        cache = np.load(cache_path, allow_pickle=True)
        embeddings = cache["embeddings"]
        ids = cache["ids"]
        # Validate match with current events
        if len(ids) == len(events):
            return embeddings, ids
        else:
            print("⚠️ Cache mismatch. Recomputing embeddings...")

    print("⏳ Generating new embeddings...")

    def get_year(event):
        text = event.get("year", "")
        if text != "":
            text = "Year: " + str(text) + ". "
        return text

    texts = [get_year(e) + f"{e['name']}: {e['description']}" for e in events]
    embeddings = get_embeddings(texts)
    ids = np.array([e["id"] for e in events])
    np.savez(cache_path, embeddings=embeddings, ids=ids)
    return embeddings, ids

events = load_events(YAML_PATH)
embeddings, ids = generate_or_load_embeddings(events, CACHE_PATH)

# Find closest event by embedding
def find_closest_event_id(description):
    query_vec = get_embeddings([description])[0]
    similarities = cosine_similarity([query_vec], embeddings)
    best_index = int(similarities.argmax())
    return int(ids[best_index])

async def find_closest_event_id_async(description):
    """
    Async version of find_closest_event_id that doesn't block the event loop.
    """
    return await run_in_threadpool(find_closest_event_id, description)

def find_closest_event_ids(descriptions):
    """
    Find the closest event IDs for multiple descriptions at once.
    This is much more efficient than calling find_closest_event_id multiple times.
    
    Args:
        descriptions: List of text descriptions
        
    Returns:
        List of event IDs in the same order as the input descriptions
    """
    # Get embeddings for all descriptions at once
    query_vecs = get_embeddings(descriptions)
    
    # Compute similarities with the database for all at once
    similarities = cosine_similarity(query_vecs, embeddings)
    
    # Get the best index for each query
    best_indices = similarities.argmax(axis=1)
    
    # Convert to event IDs
    event_ids = [int(ids[idx]) for idx in best_indices]
    
    return event_ids

async def find_closest_event_ids_async(descriptions):
    """
    Async version of find_closest_event_ids that doesn't block the event loop.
    """
    return await run_in_threadpool(find_closest_event_ids, descriptions)

# Main logic
if __name__ == "__main__":

    test_description = "A Christian army sets out to reclaim Jerusalem during the medieval period."
    matched_id = find_closest_event_id(test_description)
    closest_image_filepath = f"services/create_rag/rag/image_{matched_id}.png"
    print(f"🔍 Closest matching event ID: {matched_id}")

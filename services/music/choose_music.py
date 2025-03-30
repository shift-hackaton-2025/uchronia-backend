import openai
import pandas as pd
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity


from dotenv import load_dotenv

load_dotenv()


openai.api_key = os.getenv("OPENAI_API_KEY")


def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    response = openai.embeddings.create(input=[text], model=model)
    return np.array(response.data[0].embedding)


def save_embeddings(df):
    event_type_embeddings = [get_embedding(event) for event in df["Event Type"]]
    np.save("services/music/embeddings.npy", event_type_embeddings)
    print("Embeddings saved to services/music/embeddings.npy")


def choose_music(df, embeddings, prompt: str) -> str:
    prompt_embedding = get_embedding(prompt)
    similarities = cosine_similarity([prompt_embedding], embeddings)
    best_idx = similarities.argmax()
    return df.iloc[best_idx]["File"]


df = pd.read_csv("services/music/music.csv")
if not os.path.exists("services/music/embeddings.npy"):
    save_embeddings(df)
embeddings = np.load("services/music/embeddings.npy", allow_pickle=True)


if __name__ == "__main__":
    prompt = "France won the war against England and the people are celebrating in the streets."
    music_file = choose_music(df, embeddings, prompt)
    print(f"Chosen music file: {music_file}")

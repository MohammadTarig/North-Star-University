import faiss
import numpy as np
import json
from classify import classify_mode
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
from memory import ChatMemory
from sentence_transformers import CrossEncoder

# ---- Configure Gemini ----
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)

model_name = "gemini-2.0-flash"
client = genai.GenerativeModel(
    model_name
)  

embedder = SentenceTransformer("all-MiniLM-L6-v2")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# ---- General config ----
min_score = 9.0
Faqs_chunks = 4
educational_chunks = 10

# ---- Initialize memory ----
memory = ChatMemory()

# ---- Load FAISS indexes and metadata ----
INDEX_FILES = {
    "educational_materials": "educational_materials_faiss.index",
    "walkthrough": "walkthrough_faiss.index",
    "FAQs": "FAQs_faiss.index",
}

META_FILES = {
    "educational_materials": "educational_materials_metadata.json",
    "walkthrough": "walkthrough_metadata.json",
    "FAQs": "FAQs_metadata.json",
}

faiss_indexes = {}
metadata = {}

for key in INDEX_FILES:
    faiss_indexes[key] = faiss.read_index(INDEX_FILES[key])
    with open(META_FILES[key], "r", encoding="utf-8") as f:
        metadata[key] = json.load(f)


# ---- retrieve relevant chunks ----
def adaptive_select(reranked, mode, min_score=min_score, max_chunks=None):
    """
    Selects chunks based on mode and reranker scores.

    - min_score: minimum reranker score to include a chunk (0-1)
    - max_chunks: optional cap on number of chunks
    """
    # Filter by score
    filtered = [c for c in reranked if c["score"] >= min_score]

    # Fallback if nothing passes threshold
    if not filtered:
        filtered = reranked

    # Mode-based max chunks
    if mode == "FAQs mode":
        limit = max_chunks or Faqs_chunks
    elif mode == "Tutor mode":
        limit = max_chunks or educational_chunks
    elif mode == "walkthrough":
        limit = max_chunks or 7
    else:
        limit = max_chunks or 3

    return filtered[:limit]


def retrieve_chunks(user_question, folder_key, mode, top_k=15, method="local"):
    # --- Encode query ---
    if method == "local":
        question_vec = embedder.encode([user_question]).astype("float32")
    elif method == "gemini":
        resp = genai.embed_content(
            model="gemini-embedding-001", content=[user_question]
        )
        question_vec = np.array(
            [resp["embedding"] if "embedding" in resp else resp.embeddings[0]],
            dtype="float32",
        )
    else:
        raise ValueError("method must be 'local' or 'gemini'")

    if question_vec.ndim == 1:
        question_vec = np.expand_dims(question_vec, axis=0)

    # --- Broad recall from FAISS ---
    D, I = faiss_indexes[folder_key].search(question_vec, top_k)
    candidate_chunks = [metadata[folder_key][i]["text"] for i in I[0]]

    # --- Rerank candidates ---
    pairs = [[user_question, chunk] for chunk in candidate_chunks]
    scores = reranker.predict(pairs)  # assuming reranker is defined globally

    reranked = sorted(
        [
            {"text": chunk, "score": float(score)}
            for chunk, score in zip(candidate_chunks, scores)
        ],
        key=lambda x: x["score"],
        reverse=True,
    )

    # --- Adaptive filtering ---
    selected = adaptive_select(reranked, mode, min_score=0.90)
    return [c["text"] for c in selected]


# ---- generate response via Gemini ----
def generate_response(user_input, mode, context_chunks=None, memory_text=""):
    """
    Generate a response using Gemini with mode-based prompt.
    """
    context_text = "\n".join(context_chunks) if context_chunks else ""

    if mode == "Tutor mode":
        prompt = f"""
        You are a tutor helping a student with educational content.
        Use the following rules to respond:

        1. If the question is a simple factual or explanatory question (like "What is Newton's first law?" or "How to do this step"), provide a **full, clear answer** beyond the Given excerpts.
        2. If and only if the question is a mathematical, or case-study type question, follow the **Socratic Method**:
            - Start with a **light nudge** (subtle hint or guiding question)
            - If the student is still unsure, give a **medium hint** (break the problem into smaller steps)
            - Only give a **strong hint** (almost full solution) if the student remains stuck
            - Always encourage the student to think and respond; avoid giving direct answers immediately for problem-solving questions.
        3. if the student could get the answer after 2 or three hints, give him the answer of that step of the full mathematical, or case-study type question
        4. avoid giving direct answers immediately for problem-solving questions.Give it to him after 2 or 3 tries.

        Lesson excerpts (if any):
        {context_text}

        Previous conversation:
        {memory_text}

        Student question: {user_input}
        Respond according to these rules.
        """

    elif mode == "Motivation mode":
        prompt = f"""
        You are a tutor helping a student with educational content.
        Student says: '{user_input}'. Respond with encouragement, positivity and the steps to solve/answer for the topic/question
        
        # if there is no question, just the student feels down, motivate him generally based on the context.
        
        Lesson excerpts (if any):
        {context_text}

        Previous conversation:
        {memory_text}
        """
    elif mode == "FAQs mode":
        prompt = f"""
        You are a helpful assistant for students. Use the following FAQ excerpts:
        {context_text}

        Student question: {user_input}
        Provide clear instructions.
        """
    elif mode == "Casual mode":
        prompt = f"""
        Engage in friendly small talk with the student:

        student's last message: "{user_input}"
        Conversation history: "{memory_text}"
        """
    elif mode == "Gibrish mode":
        prompt = f"Replay with: Your message '{user_input}' is unclear. Can you rephrase?"
    else:
        prompt = f"""Respond to the student: 

        student's last message: "{user_input}"
        Conversation history: "{memory_text}"
        """

    # ---- Call Gemini to generate content ----
    response = client.generate_content(prompt)
    return response.text


# ---- Main chat loop ----
def chat(method="local"):
    print(
        "🎓 Welcome to TutorBot! I'm here to help you learn, practice, and stay motivated.\n"
    )
    print(
        "💡 You can ask me about lessons, request study tips, or even just chat casually.\n"
    )
    print("👉 Type 'exit' anytime to end the session.\n")

    # initialize embedder if local
    embedder = None
    if method == "local":

        embedder = SentenceTransformer("all-MiniLM-L6-v2")

    while True:
        user_input = input("Student: ")
        if user_input.lower() in ["exit", "quit"]:
            print(
                "👋 Goodbye for now! Keep up the great work, and see you next time. 📚"
            )
            memory.reset_memory()
            break

        # ---- Classify mode ----
        mode = classify_mode(user_input, "")
        print(f"[Mode detected: {mode}]")

        # ---- Retrieve chunks ----
        mode_to_folder = {
            "Tutor mode": "educational_materials",
            "FAQs mode": "FAQs",
            "walkthrough": "walkthrough",
        }

        context_chunks = None
        if mode in ["Tutor mode", "FAQs mode", "walkthrough"]:

            folder_key = mode_to_folder.get(mode)

            if method == "local":
                context_chunks = retrieve_chunks(
                    user_input, folder_key, mode, top_k=15, method=method
                )
            elif method == "gemini":
                # embed query with Gemini
                resp = genai.embed_content(
                    model="gemini-embedding-001", content=user_input
                )
                qvec = resp["embedding"] if "embedding" in resp else resp.embeddings[0]
                qvec = np.array([qvec], dtype="float32")
                D, I = faiss_indexes[folder_key].search(qvec, 3)
                context_chunks = [metadata[folder_key][i]["text"] for i in I[0]]

        # ---- Prepare memory ----
        memory_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in memory.get_all_messages()]
        )
        memory.add_message("student", user_input)

        # ---- Generate response ----
        answer = generate_response(user_input, mode, context_chunks, memory_text)
        print(f"TutorBot: {answer}\n")

        # ---- Update memory ----
        memory.add_message("TutorBot", answer)


# ---- Run ----
if __name__ == "__main__":
    chat(method="local")

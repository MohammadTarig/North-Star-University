import faiss
import numpy as np
import json
from classify import classify_mode
import google.generativeai as genai
from dotenv import load_dotenv
import os
from memory import ChatMemory

# ---- Configure Gemini ----
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)

# ---- Default model ----
model_name = "gemini-2.0-flash"
client = genai.GenerativeModel(
    model_name
)  # use client directly to call embed_content or generate_content

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
def retrieve_chunks(user_question, folder_key, top_k=3, embedder=None):
    question_vec = embedder.encode([user_question]).astype("float32")
    D, I = faiss_indexes[folder_key].search(np.array(question_vec), top_k)
    relevant_chunks = [metadata[folder_key][i]["text"] for i in I[0]]
    return relevant_chunks


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

        1. If the question is a simple factual or explanatory question (like "What is Newton's first law?" or "Where is the main campus?"), provide a **full, clear answer** using the lesson excerpts provided.
        2. If and only if the question is a mathematical, or case-study type question, follow the **Socratic Method**:
            - Start with a **light nudge** (subtle hint or guiding question)
            - If the student is still unsure, give a **medium hint** (break the problem into smaller steps)
            - Only give a **strong hint** (almost full solution) if the student remains stuck
            - Always encourage the student to think and respond; avoid giving direct answers immediately for problem-solving questions.
        3. Use the lesson excerpts or course notes to make your hints **context-aware**.
        4. Teach and get the information from the excerpts or course notes only

        Lesson excerpts (if any):
        {context_text}

        Previous conversation:
        {memory_text}

        Student question: {user_input}
        Respond according to these rules.
        """

    elif mode == "Motivation mode":
        prompt = f"Student says: '{user_input}'. Respond with encouragement, positivity, and short tips."
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
def chat(embedder):
    print("🎓 Welcome to TutorBot! I'm here to help you learn, practice, and stay motivated.\n")
    print("💡 You can ask me about lessons, request study tips, or even just chat casually.\n")
    print("👉 Type 'exit' anytime to end the session.\n")
    while True:
        user_input = input("Student: ")
        if user_input.lower() in ["exit", "quit"]:
            print(
                "👋 Goodbye for now! Keep up the great work, and see you next time. 📚"
            )

            memory.reset_memory()  # clear memory on exit
            break

        context_chunks = ""
        # ---- Classify mode ----
        mode = classify_mode(user_input, context_chunks)
        print(f"[Mode detected: {mode}]")

        # ---- Retrieve chunks if needed ----
        context_chunks = None
        if mode == "Tutor mode":
            context_chunks = retrieve_chunks(
                user_input, "educational_materials", embedder=embedder
            )
        elif mode == "FAQs mode":
            context_chunks = retrieve_chunks(user_input, "FAQs", embedder=embedder)
        elif mode == "walkthrough":
            context_chunks = retrieve_chunks(
                user_input, "walkthrough", embedder=embedder
            )

        # ---- Prepare memory text ----
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
    from sentence_transformers import SentenceTransformer

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    chat(embedder)

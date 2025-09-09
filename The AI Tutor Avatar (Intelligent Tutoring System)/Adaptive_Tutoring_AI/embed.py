import os
from docx import Document
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv
import json

# ---- Config ----
BASE_DIR = "./materials"
SUBFOLDERS = ["educational_materials", "walkthrough", "FAQs"]
CHUNK_SIZE = 500

# ---- APIKEY ----
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)

client = genai

# Set default model
model_name = "gemini-2.0-flash"

# ---- Local embeddings ----
embedder = SentenceTransformer("all-MiniLM-L6-v2")


# ---- Gemini embeddings ----
def gemini_embedding(text):
    response = client.embed_content(model="gemini-embedding-001", content=[text])
    return response.embeddings[0]


# ---- Load documents ----
def load_documents(folder_path):
    docs = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            file_path = os.path.join(root, f)
            text = ""

            # ---- TXT ----
            if f.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                    text = file.read()
            # ---- DOCX ----
            elif f.endswith(".docx"):
                doc = Document(file_path)
                text = "\n".join(
                    [p.text for p in doc.paragraphs if p.text.strip() != ""]
                )
            # ---- PDF ----
            elif f.endswith(".pdf"):
                with open(file_path, "rb") as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            else:
                continue

            # Split text into chunks
            for i in range(0, len(text), CHUNK_SIZE):
                chunk_text = text[i : i + CHUNK_SIZE]
                docs.append(
                    {
                        "text": chunk_text,
                        "filename": f,
                        "chunk_id": i // CHUNK_SIZE,
                        "path": file_path,
                    }
                )
    return docs


# ---- Embed a list of docs ----
def embed_documents(docs, method="local"):
    if method == "local":
        embeddings = [embedder.encode(doc["text"]) for doc in docs]
    elif method == "gemini":
        embeddings = [gemini_embedding(doc["text"]) for doc in docs]
    else:
        raise ValueError("method must be 'local' or 'gemini'")
    return np.array(embeddings).astype("float32")


def runEmbed(method="local"):
    for sub in SUBFOLDERS:
        folder_path = os.path.join(BASE_DIR, sub)
        print(f"📂 Processing folder: {sub}")

        docs = load_documents(folder_path)
        if not docs:
            print(f"⚠️ No documents found in {sub}, skipping...")
            continue

        # ---- Embed ----
        embeddings = embed_documents(docs, method=method)

        # ---- Store in FAISS ----
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        # ---- Save FAISS index ----
        index_file = f"{sub.replace(' ', '_')}_faiss.index"
        faiss.write_index(index, index_file)
        print(f"✅ Saved FAISS index for {sub} → {index_file}")

        # ---- Save metadata ----
        meta_file = f"{sub.replace(' ', '_')}_metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved metadata for {sub} → {meta_file}")


if __name__ == "__main__":
    runEmbed(method="local") # local or gemini

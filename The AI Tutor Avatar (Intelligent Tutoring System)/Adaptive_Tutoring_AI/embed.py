import os
from docx import Document
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv
import json
import time
import re

# ---- Config ----
BASE_DIR = "./materials"
SUBFOLDERS = ["educational_materials", "walkthrough", "FAQs"]
CHUNK_SIZE = 115
CHUNK_OVERLAP = 15
GEMINI_BATCH_SIZE = 16
GEMINI_SLEEP_ON_FAIL = 2

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


def _extract_embeddings_from_response(resp):
    """
    Normalize embed_content response from genai into a list of embeddings (lists of floats).
    Handles different possible response formats.
    """
    # object-like (some wrappers)
    if hasattr(resp, "embeddings"):
        return resp.embeddings

    # dict-like responses
    if isinstance(resp, dict):
        # direct key
        if "embeddings" in resp and isinstance(resp["embeddings"], list):
            return resp["embeddings"]
        # openai-like 'data' array with 'embedding' per item
        if "data" in resp and isinstance(resp["data"], list):
            out = []
            for item in resp["data"]:
                if isinstance(item, dict) and "embedding" in item:
                    out.append(item["embedding"])
                elif isinstance(item, dict) and "embeddings" in item:
                    # defensive: flatten
                    e = item["embeddings"]
                    if isinstance(e[0], (list, tuple)):
                        out.extend(e)
                    else:
                        out.append(e)
            if out:
                return out
        # some clients return single embedding
        if "embedding" in resp:
            return [resp["embedding"]]
    # unknown format: raise for visibility
    raise ValueError(
        f"Unrecognized embedding response format: {type(resp)} / keys: {list(resp.keys()) if isinstance(resp, dict) else 'NA'}"
    )


def gemini_embed_batch(
    texts,
    model_name="gemini-embedding-001",
    batch_size=GEMINI_BATCH_SIZE,
    max_retries=3,
):
    """
    Request embeddings from Gemini in batches. Returns a numpy array shape (len(texts), dim).
    """
    all_embs = []
    n = len(texts)
    for i in range(0, n, batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(max_retries):
            try:
                resp = client.embed_content(model=model_name, content=batch)
                batch_embs = _extract_embeddings_from_response(resp)
                # ensure length matches
                if len(batch_embs) != len(batch):
                    # defensive: try to handle single-embedding case
                    if len(batch_embs) == 1 and len(batch) > 1:
                        raise ValueError(
                            "Returned single embedding for a batch request."
                        )
                    # otherwise continue but warn
                    raise ValueError(
                        "Mismatch between returned embeddings and batch size."
                    )
                all_embs.extend(batch_embs)
                break
            except Exception as e:
                # retry/backoff
                if attempt + 1 == max_retries:
                    raise
                time.sleep(GEMINI_SLEEP_ON_FAIL * (attempt + 1))
    arr = np.array(all_embs, dtype="float32")
    return arr


def clean_text(text):
    import re

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_documents(folder_path):
    docs = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            file_path = os.path.join(root, f)
            text = ""

            if f.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                    text = file.read()
            elif f.endswith(".docx"):
                from docx import Document

                doc = Document(file_path)
                text = clean_text(
                    "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
                )
            elif f.endswith(".pdf"):
                import PyPDF2

                with open(file_path, "rb") as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += " " + clean_text(page_text)
            else:
                continue

            text = clean_text(text)
            chunk_id = 0
            for i in range(0, len(text) - CHUNK_SIZE + 1, CHUNK_SIZE - CHUNK_OVERLAP):
                chunk = text[i : i + CHUNK_SIZE]
                # avoid cutting words
                if i + CHUNK_SIZE < len(text) and text[i + CHUNK_SIZE] != " ":
                    end = text.find(" ", i + CHUNK_SIZE)
                    if end != -1:
                        chunk = text[i:end]
                docs.append(
                    {
                        "text": chunk,
                        "filename": f,
                        "chunk_id": chunk_id,
                        "path": file_path,
                    }
                )
                chunk_id += 1
    return docs


def _extract_embeddings_from_response(resp):
    """
    Normalize embed_content response from genai into a list of embeddings (lists of floats).
    Handles different possible response formats.
    """
    # object-like (some wrappers)
    if hasattr(resp, "embeddings"):
        return resp.embeddings

    # dict-like responses
    if isinstance(resp, dict):
        # direct key
        if "embeddings" in resp and isinstance(resp["embeddings"], list):
            return resp["embeddings"]
        # openai-like 'data' array with 'embedding' per item
        if "data" in resp and isinstance(resp["data"], list):
            out = []
            for item in resp["data"]:
                if isinstance(item, dict) and "embedding" in item:
                    out.append(item["embedding"])
                elif isinstance(item, dict) and "embeddings" in item:
                    # defensive: flatten
                    e = item["embeddings"]
                    if isinstance(e[0], (list, tuple)):
                        out.extend(e)
                    else:
                        out.append(e)
            if out:
                return out
        # some clients return single embedding
        if "embedding" in resp:
            return [resp["embedding"]]
    # unknown format: raise for visibility
    raise ValueError(
        f"Unrecognized embedding response format: {type(resp)} / keys: {list(resp.keys()) if isinstance(resp, dict) else 'NA'}"
    )


def gemini_embed_batch(
    texts,
    model_name="gemini-embedding-001",
    max_retries=3,
):
    """
    Request embeddings from Gemini (one by one).
    Returns a numpy array shape (len(texts), dim).
    """
    all_embs = []
    for text in texts:
        for attempt in range(max_retries):
            try:
                resp = client.embed_content(model=model_name, content=text)
                emb = _extract_embeddings_from_response(resp)
                # ensure we always append a vector, not a list of vectors
                if isinstance(emb[0], (list, np.ndarray)):
                    all_embs.append(emb[0])
                else:
                    all_embs.append(emb)
                break
            except Exception as e:
                if attempt + 1 == max_retries:
                    raise
                time.sleep(GEMINI_SLEEP_ON_FAIL * (attempt + 1))
    arr = np.array(all_embs, dtype="float32")
    return arr


# ---- Embed a list of docs ----
def embed_documents(docs, method="local"):
    if method == "local":
        embeddings = [embedder.encode(doc["text"]) for doc in docs]
    elif method == "gemini":
        texts = [doc["text"] for doc in docs]
        if len(texts) == 0:
            return np.zeros((0, 0), dtype="float32")
        embeddings = gemini_embed_batch(texts)
        # debug: print dimension
        print(f"🔍 Gemini embeddings produced shape: {embeddings.shape}")
        return embeddings.astype("float32")
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

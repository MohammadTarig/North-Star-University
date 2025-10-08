import os
import re
import json
import random
import time
from dotenv import load_dotenv
import google.generativeai as genai


# ---- Configure Gemini ----
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)

model_name = "gemini-2.0-flash"
client = genai.GenerativeModel(model_name)


def safe_generate(prompt, retries=5, delay=5):
    for attempt in range(retries):
        try:
            return client.generate_content(prompt)
        except hex.ServiceUnavailable:
            print(
                f"⚠️ Service unavailable, retrying in {delay} seconds... (Attempt {attempt+1}/{retries})"
            )
            time.sleep(delay)
    raise RuntimeError("Failed to generate content after multiple retries")

def load_concept_from_file() -> tuple[str, str]:
    """
    Load concept/topic name and combine all content levels into one text variable.
    Expected structure in JSON file:
    {
        "concepts": {
            "name": "...",
            "content": {"beginner": "...", "intermediate": "...", "advanced": "..."}
        }
    }
    Returns (concept_name, combined_content).
    """

    if not os.path.exists("dummy_concepts.json"):
        raise FileNotFoundError(f"Concept file not found: dummy_concepts.json")
    with open("dummy_concepts.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    concepts = data.get("concepts") or {}
    concept_name = (concepts.get("name") or "").strip()
    content_obj = concepts.get("content") or {}

    beginner = (content_obj.get("beginner") or "").strip()
    intermediate = (content_obj.get("intermediate") or "").strip()
    advanced = (content_obj.get("advanced") or "").strip()

    if not concept_name:
        raise ValueError("Missing 'concepts.name' in dummy_concepts.json")

    parts = []
    if beginner:
        parts.append(f"Beginner:\n{beginner}")
    if intermediate:
        parts.append(f"Intermediate:\n{intermediate}")
    if advanced:
        parts.append(f"Advanced:\n{advanced}")

    combined_content = "\n\n".join(parts).strip()
    if not combined_content:
        raise ValueError("No content found under 'concepts.content' in dummy_concepts.json")

    return concept_name, combined_content

def extract_json(text: str) -> str:
    """
    Extract the first JSON object from text (handles cases where
    Gemini adds extra explanation or markdown formatting).
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text)
    text = re.sub(r"```$", "", text)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Gemini output.")
    return match.group(0)

def questionBank():
    concept, content = load_concept_from_file()
    prompt = f"""
    You are a Quiz Generator expert. You have to generate multiple-choice questions (MCQs) for students 
    to evaluate their understanding and knowledge.

    # Task:
    1. Generate 10 questions from the Beginner content
    2. Generate 10 questions from the Intermediate content
    3. Generate 10 questions from the Advanced content

    # Topic:
    {concept}

    # Content:
    {content}

    # Output format (strict JSON):
    "assessments": {{
        "easy": [
            {{
            "question": "The question text",
            "options": ["option one", "option two", "option three", "option four"],
            "answer": "Correct option"
            }}
        ],
        "medium": [
            {{
            "question": "The question text",
            "options": ["option one", "option two", "option three", "option four"],
            "answer": "Correct option"
            }}
        ],
        "hard": [
            {{
            "question": "The question text",
            "options": ["option one", "option two", "option three", "option four"],
            "answer": "Correct option"
            }}
        ]
    }}

    # Rules:
    1. All questions must be strictly MCQs with a single correct answer.
    2. The correct answer must be clear, specific, and unambiguous.
    3. Incorrect options must be reasonable, related, and plausible, but clearly wrong.
    4. Do NOT include examples inside the question text. Questions must be concise and complete.
    5. Follow the JSON structure exactly; do not include any text outside of it.
    6. Do not provide more than one correct answer.
    7. Do not always place the correct answer in the same position.
    8 Distribute the correct answer randomly among the options placement.
    9. Make all answer options roughly the same length, so the correct answer is not obvious by size.
    """

    response = safe_generate(prompt)
    return response.text

def shuffle_mcq_options(mcq_data: dict):
    """
    Shuffle the options of each MCQ question across easy, medium, and hard levels,
    while keeping track of the correct answer.
    """
    for level in ["easy", "medium", "hard"]:
        for q in mcq_data["assessments"][level]:
            correct_answer = q["answer"]
            options = q["options"]

            # Shuffle options
            random.shuffle(options)
            q["options"] = options

            
            if correct_answer not in options:
                raise ValueError(
                    f"Correct answer '{correct_answer}' missing from options in {level} question."
                )

            q["answer"] = correct_answer  

    return mcq_data

def questionsToJson():
    result = questionBank()

    try:
        cleaned = extract_json(result)
        mcq_data = json.loads(cleaned)
    except Exception as e:
        raise ValueError("Gemini did not return valid JSON.") from e

    questions = shuffle_mcq_options(mcq_data)

    print("\n📋 Queations has been generated, The test begins: ")
    output_file = "generated_questions.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    return output_file

if __name__ == "__main__":
    questionsToJson()

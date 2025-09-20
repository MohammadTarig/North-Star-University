import os
import json
from typing import List, Dict
from haystack import Pipeline, Document, component
from haystack.components.builders import PromptBuilder
import json_repair
import google.generativeai as genai
import dotenv
import PyPDF2   


dotenv.load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)

# ---------------- Quiz Componenets ---------------- #

@component
class GeminiPdfToTextExtractor:
    @component.output_types(documents=List[Document])
    def run(self, file_path: str):
        
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        doc = Document(content=text.strip(), meta={"source": file_path})
        return {"documents": [doc]}


@component
class TextPreprocessor:
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]):
        processed_docs = []
        for doc in documents:
            text = re.sub(r"\s+", " ", doc.content).strip()
            processed_docs.append(Document(content=text, meta=doc.meta))
        return {"documents": processed_docs}


@component
class GeminiGenerator:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @component.output_types(gemini_replies=List[str])
    def run(self, prompt: str):
        client = genai.GenerativeModel(self.model)
        response = client.generate_content(prompt)
        return {"gemini_replies": [response.text]}


@component
class QuizParser:
    @component.output_types(quiz=dict)
    def run(self, replies: List[str]):
        reply = replies[0]
        first_index = min(reply.find("{"), reply.find("["))  
        last_index = max(reply.rfind("}"), reply.rfind("]")) + 1
        json_portion = reply[first_index:last_index]
        try:
            quiz = json.loads(json_portion)
        except json.JSONDecodeError:
            quiz = json_repair.loads(json_portion)
        if isinstance(quiz, list):
            quiz = quiz[0]
        return {"quiz": quiz}


quiz_generation_template = """Given the following text, create 5 multiple choice quizzes in JSON format.
Each question should have 4 different options, and only one of them should be correct.
The options should be unambiguous and follow the format: "a. option"
Return only valid JSON.

{
"topic": "a sentence explaining the topic of the text",
"questions": [
    {
    "question": "text of the question",
    "options": ["a. 1st option", "b. 2nd option", "c. 3rd option", "d. 4th option"],
    "right_option": "(a/b/c/d)" # the right option is random, it can be either a, b, c, or d.
    }
]
}

Note: the Questions get harder each time easy->hard.

text:
{% for doc in documents %}{{ doc.content }}{% endfor %}
"""

# ---------------- Quiz Generation Pipeline ---------------- #

quiz_generation_pipeline = Pipeline()
quiz_generation_pipeline.add_component("text_extractor", GeminiPdfToTextExtractor())
quiz_generation_pipeline.add_component("text_preprocessor", TextPreprocessor())
quiz_generation_pipeline.add_component(
    "prompt_builder", PromptBuilder(template=quiz_generation_template)
)
quiz_generation_pipeline.add_component(
    "gemini_generator",
    GeminiGenerator(api_key=gemini_api_key, model="gemini-2.0-flash"),
)
quiz_generation_pipeline.add_component("parser", QuizParser())

quiz_generation_pipeline.connect("text_extractor", "text_preprocessor")
quiz_generation_pipeline.connect("text_preprocessor", "prompt_builder")
quiz_generation_pipeline.connect("prompt_builder", "gemini_generator")
quiz_generation_pipeline.connect("gemini_generator", "parser")


evaluation_model = genai.GenerativeModel("gemini-2.0-flash")


def extract_json(text):
    # Try to extract a JSON block from a string
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return json_repair.loads(match.group())
    raise ValueError("No valid JSON found")

# ---------------- Quiz evaluation prompt ---------------- #

def evaluate_student_answer(
    question: str, student_answer: str, correct_answer: str
) -> dict:
    prompt = f"""
    You are an AI assistant/Tutor designed to evaluate student answers (Friendly Teacher).

    For the question below, compare the student's answer with the correct one.
    Give a score from 0 to 5, mark whether it passed, and explain briefly.
    - Give one total score from 0 to 5 (overall performance).
    - Mark passed as True or False (passing mark = 60% ()).
    - about the feedback : give the correct answer if the student got it wrong, dicuss it and cheer him/her up(be natural), if no wrong answers celabrate and congratulate him/her.

    Respond ONLY with valid JSON. Do not write any extra text or markdown.

    Output Example:
    {{
        "passed": True/False,
        "score": "X/10" (the number of correct answers given by the student/total number of questions, if he got 2 correct it should be 2/5 and so on),
        "feedback": "Your feedback"
    }}

    Question: {question}
    Student's Answer: {student_answer}
    Correct Answer: {correct_answer}
    """

    try:
        response = evaluation_model.generate_content(prompt)
        return extract_json(response.text)
    except Exception as e:
        return {
            "passed": False,
            "score": "0/5",
            "feedback": f"Error: {e}"
        }


# ---------------- Main Execution ---------------- #

if __name__ == "__main__":

    file_path = "app/materials/ArtificialIntelligence.pdf"

    try:
        # Run the quiz generation pipeline
        result = quiz_generation_pipeline.run(
            {"text_extractor": {"file_path": file_path}}
        )
        quiz_data = result["parser"]["quiz"]

        topic = quiz_data.get("topic", "Untitled Topic")
        questions = quiz_data["questions"]

        print(f"\n🧠 Topic: {topic}\n")

        answers_review = []

        
        for i, q in enumerate(questions, 1):
            print(f"\nQuestion {i}: {q['question']}")
            for opt in q["options"]:
                print(opt)

            student_input = input("\nYour answer (a/b/c/d): ").strip().lower()
            while student_input not in ["a", "b", "c", "d"]:
                student_input = (
                    input("Invalid input. Please enter a, b, c, or d: ").strip().lower()
                )

            correct_letter = q["right_option"]

            student_answer = next(
                opt for opt in q["options"] if opt.startswith(student_input + ".")
            )
            correct_answer = next(
                opt for opt in q["options"] if opt.startswith(correct_letter + ".")
            )

            answers_review.append(
                {
                    "question": q["question"],
                    "student_answer": student_answer,
                    "correct_answer": correct_answer,
                }
            )

        
        combined_questions = ""
        combined_student_answers = ""
        combined_correct_answers = ""

        for idx, ans in enumerate(answers_review, 1):
            combined_questions += f"Q{idx}: {ans['question']}\n"
            combined_student_answers += f"Q{idx}: {ans['student_answer']}\n"
            combined_correct_answers += f"Q{idx}: {ans['correct_answer']}\n"

        
        print("\n📊 Quiz Finished! Evaluating your answers...\n")
        final_eval = evaluate_student_answer(
            question=combined_questions,
            student_answer=combined_student_answers,
            correct_answer=combined_correct_answers,
        )

        
        print(f"Passed  : {final_eval.get('passed')}")
        print(f"Score   : {final_eval.get('score')}")
        print(f"Feedback: {final_eval.get('feedback')}")

    except Exception as e:
        print(f"❌ Error: {e}")

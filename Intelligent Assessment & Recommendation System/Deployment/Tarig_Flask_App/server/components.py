import re
import json
import json_repair
from PIL import Image
import pytesseract
from haystack import component, Document
from google import genai
from haystack.components.builders import PromptBuilder        


@component
class ImageToTextExtractor:
    @component.output_types(documents=list[Document])
    def run(self, image_data: bytes):
        # Use BytesIO to handle in-memory image data
        from io import BytesIO
        img = Image.open(BytesIO(image_data))  # Open from bytes
        text = pytesseract.image_to_string(img)
        doc = Document(content=text, meta={"source": "uploaded_image"})
        return {"documents": [doc]}

@component
class TextPreprocessor:
    @component.output_types(documents=list[Document])
    def run(self, documents: list[Document]):
        processed_docs = []
        for doc in documents:
            text = doc.content
            text = re.sub(r'\s+', ' ', text).strip()
            processed_docs.append(Document(content=text, meta=doc.meta))
        return {"documents": processed_docs}

@component
class GeminiGenerator:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
    
    @component.output_types(gemini_replies=list[str])
    def run(self, prompt: str):
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        return {"gemini_replies": [response.text]}

@component
class QuizParser:
    @component.output_types(quiz=dict)
    def run(self, replies: list[str]):
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
    
@component
class QuizEvaluator:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self.prompt_template = """Evaluate these quiz answers:
        {% for item in questions %}
        Question: {{ item.question }}
        Correct Answer: {{ item.right_option }}
        Student Answer: {{ item.student_answer }}
        {% endfor %}

        For each question, provide:
        - feedback (string)
        - score (0-5)
        - passed (boolean)
        Return ONLY a JSON array with these keys per question.
        """

    @component.output_types(evaluations=list)
    def run(self, questions: list):
        # Build prompt
        prompt_builder = PromptBuilder(template=self.prompt_template)
        prompt = prompt_builder.run(questions=questions)["prompt"]
        
        # Get Gemini response
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        # Parse response (same cleanup logic as before)
        try:
            json_str = response.text[response.text.find('['):response.text.rfind(']')+1]
            return {"evaluations": json.loads(json_str)}
        except Exception as e:
            raise ValueError(f"Failed to parse evaluation: {str(e)}")
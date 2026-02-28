from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from components import ImageToTextExtractor, TextPreprocessor, GeminiGenerator, QuizParser, QuizEvaluator

def create_quiz_pipeline(api_key: str):
    quiz_generation_template = """Given the following text, create 5 multiple choice quizzes in JSON format.
Each question should have 4 different options, and only one of them should be correct.
The options should be unambiguous.
Each option should begin with a letter followed by a period and a space (e.g., "a. option").
The question should also briefly mention the general topic of the text so that it can be understood in isolation.
Each question should not give hints to answer the other questions.
Include challenging questions, which require reasoning.

respond with JSON only, no markdown or descriptions.

example JSON format you should absolutely follow:
{"topic": "a sentence explaining the topic of the text",
 "questions":
  [
    {
      "question": "text of the question",
      "options": ["a. 1st option", "b. 2nd option", "c. 3rd option", "d. 4th option"],
      "right_option": "c"  # letter of the right option ("a" for the first, "b" for the second, etc.)
    }, ...
  ]
}

text:
{% for doc in documents %}{{ doc.content }}{% endfor %}
"""
    
    
    pipeline = Pipeline()
    pipeline.add_component("text_extractor", ImageToTextExtractor())
    pipeline.add_component("text_preprocessor", TextPreprocessor())
    pipeline.add_component("prompt_builder", PromptBuilder(template=quiz_generation_template))
    pipeline.add_component("gemini_generator", GeminiGenerator(api_key=api_key))
    pipeline.add_component("parser", QuizParser())
    
    pipeline.connect("text_extractor.documents", "text_preprocessor.documents")
    pipeline.connect("text_preprocessor.documents", "prompt_builder.documents")
    pipeline.connect("prompt_builder.prompt", "gemini_generator.prompt")
    pipeline.connect("gemini_generator.gemini_replies", "parser.replies")
    
    return pipeline

def create_evaluation_pipeline(api_key: str):
    pipeline = Pipeline()
    pipeline.add_component("evaluator", QuizEvaluator(api_key=api_key))
    return pipeline
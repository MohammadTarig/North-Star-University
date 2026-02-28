from flask import Flask, request, jsonify
from flask_cors import CORS
from pipelines import create_quiz_pipeline, create_evaluation_pipeline
from google import genai
import json
import os
from dotenv import load_dotenv


load_dotenv()  # Load environment variables

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

pipeline = create_quiz_pipeline(api_key=os.getenv("GEMINI_API_KEY"))

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    try:
         # Read the file data immediately before the stream closes
        file_data = file.read()
        
        # Run  pipeline
        result = pipeline.run({"text_extractor": {"image_data": file_data}}) # Pass bytes instead of stream
        quiz = result["parser"]["quiz"]

        return jsonify(quiz)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

evaluation_pipeline = create_evaluation_pipeline(api_key=os.getenv("GEMINI_API_KEY"))

# Update your evaluate-quiz endpoint
@app.route('/evaluate-quiz', methods=['POST'])
def evaluate_answer():
    try:
        quiz_data = request.get_json()
        result = evaluation_pipeline.run({"evaluator": {"questions": quiz_data["questions"]}})
        evaluations = result["evaluator"]["evaluations"]
        
        return jsonify({
            "evaluations": evaluations,
            "overall_score": sum(e['score'] for e in evaluations)/len(evaluations)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
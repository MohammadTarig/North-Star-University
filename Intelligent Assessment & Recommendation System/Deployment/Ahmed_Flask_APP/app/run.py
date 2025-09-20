from flask import Flask, render_template, request, jsonify
from logic.engin import generate_quiz_from_pdf
from logic.engin import Quiz_evaluation

import os

app = Flask(__name__)


# Homepage
@app.route("/")
def index():
    return render_template("quiz2.html")


# API to serve quiz data
@app.route("/api/start_quiz", methods=["POST"])
def start_quiz():
    data = request.get_json()
    category = data.get("category")

    
    file_path = os.path.join(os.path.dirname(__file__), "materials", f"{category}.pdf")
    try:
        quiz = generate_quiz_from_pdf(file_path)
        return jsonify({"success": True, "quiz": quiz})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/evaluate_quiz", methods=["POST"])
def evaluation():
    data = request.get_json()
    if not data or "questions" not in data:
        return jsonify({"success": False, "error": "Invalid quiz data."})

    return Quiz_evaluation(data)

# Run
if __name__ == "__main__":
    app.run(debug=True)

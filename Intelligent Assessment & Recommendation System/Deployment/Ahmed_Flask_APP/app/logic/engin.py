from .Ai_workflow import quiz_generation_pipeline
from .Ai_workflow import evaluate_student_answer


def generate_quiz_from_pdf(file_path):
    result = quiz_generation_pipeline.run({"text_extractor": {"file_path": file_path}})
    quiz_data = result["parser"]["quiz"]
    topic = quiz_data.get("topic", "Untitled Topic")
    questions = quiz_data["questions"]
    return {"topic": topic, "questions": questions}


def Quiz_evaluation(data: dict):

    answers_review = []

    for q in data["questions"]:
        student_answer = q.get("student_answer", "")
        correct_answer = q.get("right_option", "")
        answers_review.append(
            {
                "question": q["question"],
                "student_answer": student_answer,
                "correct_answer": correct_answer,
            }
        )

    # Combine into strings
    combined_questions = ""
    combined_student_answers = ""
    combined_correct_answers = ""

    for idx, ans in enumerate(answers_review, 1):
        combined_questions += f"Q{idx}: {ans['question']}\n"
        combined_student_answers += f"Q{idx}: {ans['student_answer']}\n"
        combined_correct_answers += f"Q{idx}: {ans['correct_answer']}\n"

    # Call your evaluation function
    final_eval = evaluate_student_answer(
        question=combined_questions,
        student_answer=combined_student_answers,
        correct_answer=combined_correct_answers,
    )

    return {
        "success": True,
        "result": {
            "passed": final_eval.get("passed"),
            "score": final_eval.get("score"),
            "feedback": final_eval.get("feedback"),
        },
    }

import os
import json
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity

from extensions import db
from models import Quiz, QuizQuestion, Lesson, AISummary
from middleware.auth_middleware import student_required, jwt_required_custom

quizzes_bp = Blueprint("quizzes", __name__, url_prefix="/api/quizzes")

GEMINI_MODEL = "gemini-1.5-pro"
GEMINI_URL   = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _call_gemini(prompt: str) -> str:
    """Call Gemini Pro and return the raw text response."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    payload = {
        "system_instruction": {
            "parts": [{"text": (
                "You are an educational quiz generator. "
                "Always respond with valid JSON only — no markdown, no code fences, no extra text."
            )}]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":     0.5,
            "maxOutputTokens": 1200,
            "topP":            0.9,
        }
    }

    resp = requests.post(
        f"{GEMINI_URL}?key={api_key}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _build_prompt(lesson_title: str, summary_text: str) -> str:
    return f"""Generate exactly 5 multiple-choice questions based on this lesson.

Lesson title: {lesson_title}
Study summary: {summary_text}

Rules:
- Each question must have exactly 4 options: A, B, C, D
- Only ONE option is correct
- Questions must test understanding, not just memory
- Vary difficulty: 2 easy, 2 medium, 1 hard
- Return ONLY a JSON array — no explanation, no markdown

Required JSON format (return this exact structure):
[
  {{
    "question_no": 1,
    "question_text": "...",
    "option_a": "...",
    "option_b": "...",
    "option_c": "...",
    "option_d": "...",
    "correct_option": "A"
  }},
  ...5 items total...
]"""


# POST /api/quizzes/generate/:lesson_id
# Generates a brand-new quiz using Gemini Pro — real-time, synchronous
@quizzes_bp.route("/generate/<int:lesson_id>", methods=["POST"])
@student_required
def generate_quiz(lesson_id):
    student_id = int(get_jwt_identity())
    lesson     = Lesson.query.get_or_404(lesson_id)

    # Need the AI summary as context for the quiz
    summary = AISummary.query.filter_by(lesson_id=lesson_id).first()
    if not summary:
        return jsonify({"error": "AI summary not yet available for this lesson. Please wait for it to generate first."}), 422

    # Call Gemini Pro
    try:
        raw = _call_gemini(_build_prompt(lesson.title, summary.summary_text))
    except requests.exceptions.Timeout:
        return jsonify({"error": "Gemini API timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Gemini API error: {e}")
        return jsonify({"error": "Failed to reach Gemini API. Check your API key."}), 502

    # Parse JSON response 
    try:
        # Strip markdown code fences if Gemini adds them despite instructions
        clean = raw.replace("```json", "").replace("```", "").strip()
        questions_data = json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        current_app.logger.error(f"Gemini returned invalid JSON: {raw}")
        return jsonify({"error": "AI returned an unexpected format. Please try again."}), 500

    if not isinstance(questions_data, list) or len(questions_data) != 5:
        return jsonify({"error": "AI did not return exactly 5 questions. Please try again."}), 500

    #  Save Quiz to DB 
    quiz = Quiz(
        lesson_id=lesson_id,
        student_id=student_id,
        total_questions=5,
        submitted=False,
    )
    db.session.add(quiz)
    db.session.flush()  # get quiz.id before committing

    for q in questions_data:
        correct = str(q.get("correct_option", "A")).upper()
        if correct not in ("A", "B", "C", "D"):
            correct = "A"
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_no=q["question_no"],
            question_text=q["question_text"],
            option_a=q["option_a"],
            option_b=q["option_b"],
            option_c=q["option_c"],
            option_d=q["option_d"],
            correct_option=correct,
        )
        db.session.add(question)

    db.session.commit()
    return jsonify({"quiz": quiz.to_dict(include_questions=True)}), 201


# GET /api/quizzes/:quiz_id
# Returns a quiz with all questions (answers hidden if not submitted)
@quizzes_bp.route("/<int:quiz_id>", methods=["GET"])
@student_required
def get_quiz(quiz_id):
    student_id = int(get_jwt_identity())
    quiz = Quiz.query.get_or_404(quiz_id)

    if quiz.student_id != student_id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"quiz": quiz.to_dict(include_questions=True)}), 200


#GET /api/quizzes/lesson/:lesson_id/history
# All quiz attempts by this student for a lesson (submitted only)
@quizzes_bp.route("/lesson/<int:lesson_id>/history", methods=["GET"])
@student_required
def quiz_history(lesson_id):
    student_id = int(get_jwt_identity())
    quizzes = (
        Quiz.query
        .filter_by(lesson_id=lesson_id, student_id=student_id, submitted=True)
        .order_by(Quiz.created_at.desc())
        .all()
    )
    return jsonify({"history": [q.to_dict() for q in quizzes]}), 200


#  POST /api/quizzes/:quiz_id/submit
# Submit answers, calculate score, mark quiz as done
# Body: { "answers": { "1": "A", "2": "C", ... } }
@quizzes_bp.route("/<int:quiz_id>/submit", methods=["POST"])
@student_required
def submit_quiz(quiz_id):
    student_id = int(get_jwt_identity())
    quiz = Quiz.query.get_or_404(quiz_id)

    if quiz.student_id != student_id:
        return jsonify({"error": "Access denied"}), 403

    if quiz.submitted:
        return jsonify({"error": "This quiz has already been submitted"}), 409

    data    = request.get_json(silent=True) or {}
    answers = data.get("answers", {})   # { "1": "A", "2": "B", ... }

    if not answers:
        return jsonify({"error": "No answers provided"}), 422

    score = 0
    for question in quiz.questions:
        ans = answers.get(str(question.question_no), "").upper()
        if ans in ("A", "B", "C", "D"):
            question.student_answer = ans
            question.is_correct     = (ans == question.correct_option)
            if question.is_correct:
                score += 1

    quiz.score        = score
    quiz.submitted    = True
    quiz.submitted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "quiz":    quiz.to_dict(include_questions=True),
        "message": f"Quiz submitted! You scored {score}/{quiz.total_questions}."
    }), 200


# GET /api/quizzes/stats
# Overall quiz stats for the logged-in student
@quizzes_bp.route("/stats", methods=["GET"])
@student_required
def quiz_stats():
    from sqlalchemy import func
    student_id = int(get_jwt_identity())

    total_taken = Quiz.query.filter_by(student_id=student_id, submitted=True).count()
    avg_score   = (
        db.session.query(func.avg(Quiz.score / Quiz.total_questions * 100))
        .filter_by(student_id=student_id, submitted=True)
        .scalar()
    )

    return jsonify({
        "stats": {
            "total_quizzes_taken": total_taken,
            "average_score_pct":   round(float(avg_score or 0), 1),
        }
    }), 200

from datetime import datetime
from flask import Blueprint, request, jsonify

from extensions import db
from models import AISummary, Lesson
from middleware.auth_middleware import jwt_required_custom

summaries_bp = Blueprint("summaries", __name__, url_prefix="/api/summaries")


#  GET /api/summaries/:lesson_id 
@summaries_bp.route("/<int:lesson_id>", methods=["GET"])
@jwt_required_custom
def get_summary(lesson_id):
    Lesson.query.get_or_404(lesson_id)   # 404 if lesson doesn't exist
    summary = AISummary.query.filter_by(lesson_id=lesson_id).first()
    if not summary:
        return jsonify({"error": "AI summary not yet generated for this lesson"}), 404
    return jsonify({"summary": summary.to_dict()}), 200


#  POST /api/summaries/webhook 
# Called by n8n after the AI pipeline completes.
# Payload: { "lesson_id": int, "summary_text": str }
@summaries_bp.route("/webhook", methods=["POST"])
def receive_summary():
    data         = request.get_json(silent=True) or {}
    lesson_id    = data.get("lesson_id")
    summary_text = (data.get("summary_text") or "").strip()

    if not lesson_id or not summary_text:
        return jsonify({"error": "lesson_id and summary_text are required"}), 422

    Lesson.query.get_or_404(lesson_id)

    # Upsert — update if exists, insert if not
    summary = AISummary.query.filter_by(lesson_id=lesson_id).first()
    if summary:
        summary.summary_text = summary_text
        summary.generated_at = datetime.utcnow()
    else:
        summary = AISummary(lesson_id=lesson_id, summary_text=summary_text)
        db.session.add(summary)

    db.session.commit()
    return jsonify({"message": "Summary saved", "summary": summary.to_dict()}), 200

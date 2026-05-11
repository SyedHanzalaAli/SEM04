from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func

from extensions import db
from models import Progress, Lesson
from middleware.auth_middleware import student_required

progress_bp = Blueprint("progress", __name__, url_prefix="/api/progress")

VALID_STATUSES = {"not-started", "in-progress", "completed"}


# GET /api/progress
# Returns all progress rows for the logged-in student
# JOIN: Progress ⟶ Lessons ⟶ Courses
@progress_bp.route("", methods=["GET"])
@student_required
def list_progress():
    student_id = int(get_jwt_identity())
    rows = (
        Progress.query
        .filter_by(student_id=student_id)
        .join(Progress.lesson)
        .order_by(Lesson.created_at.asc())
        .all()
    )
    return jsonify({"progress": [r.to_dict() for r in rows]}), 200


#  GET /api/progress/stats 
# Aggregate SQL: completed count, total lessons, completion %
@progress_bp.route("/stats", methods=["GET"])
@student_required
def progress_stats():
    student_id = int(get_jwt_identity())

    total_lessons = Lesson.query.count()

    completed = (
        db.session.query(func.count(Progress.id))
        .filter_by(student_id=student_id, status="completed")
        .scalar()
    )
    in_progress = (
        db.session.query(func.count(Progress.id))
        .filter_by(student_id=student_id, status="in-progress")
        .scalar()
    )

    pct = round((completed / total_lessons * 100), 1) if total_lessons else 0.0

    return jsonify({
        "stats": {
            "total_lessons":   total_lessons,
            "completed":       completed,
            "in_progress":     in_progress,
            "completion_rate": pct,
        }
    }), 200


# PUT /api/progress/:lesson_id 
# Upsert progress row — SQL UPDATE if exists, INSERT if not
@progress_bp.route("/<int:lesson_id>", methods=["PUT"])
@student_required
def update_progress(lesson_id):
    student_id = int(get_jwt_identity())
    data       = request.get_json(silent=True) or {}
    status     = (data.get("status") or "").strip()

    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of: {', '.join(VALID_STATUSES)}"}), 422

    Lesson.query.get_or_404(lesson_id)

    row = Progress.query.filter_by(student_id=student_id, lesson_id=lesson_id).first()
    if row:
        row.status     = status
        row.updated_at = datetime.utcnow()
    else:
        row = Progress(student_id=student_id, lesson_id=lesson_id, status=status)
        db.session.add(row)

    db.session.commit()
    return jsonify({"progress": row.to_dict()}), 200

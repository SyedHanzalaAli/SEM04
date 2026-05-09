import re
import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity

from extensions import db
from models import Lesson, Course
from middleware.auth_middleware import jwt_required_custom, teacher_required

lessons_bp = Blueprint("lessons", __name__, url_prefix="/api/lessons")

YOUTUBE_RE = re.compile(r"(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}")


def _fire_n8n(lesson: Lesson):
    """POST lesson info to n8n to kick off the AI summary pipeline."""
    url = current_app.config.get("N8N_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={
            "lesson_id":   lesson.id,
            "lesson_title": lesson.title,
            "youtube_url": lesson.youtube_url,
        }, timeout=5)
    except requests.RequestException as exc:
        current_app.logger.warning(f"n8n webhook failed: {exc}")


# ── GET /api/lessons?course_id= ────────────────────────────────────────────
@lessons_bp.route("", methods=["GET"])
@jwt_required_custom
def list_lessons():
    course_id = request.args.get("course_id", type=int)
    query = Lesson.query
    if course_id:
        query = query.filter_by(course_id=course_id)
    lessons = query.order_by(Lesson.created_at.desc()).all()
    return jsonify({"lessons": [l.to_dict(include_summary=True) for l in lessons]}), 200


# ── POST /api/lessons ──────────────────────────────────────────────────────
@lessons_bp.route("", methods=["POST"])
@teacher_required
def create_lesson():
    data      = request.get_json(silent=True) or {}
    title     = (data.get("title") or "").strip()
    url       = (data.get("youtube_url") or "").strip()
    course_id = data.get("course_id")

    # ── Validation ─────────────────────────────────────────
    errors = {}
    if not title:
        errors["title"] = "Lesson title is required"
    if not YOUTUBE_RE.search(url):
        errors["youtube_url"] = "A valid YouTube URL is required"
    if not course_id:
        errors["course_id"] = "course_id is required"
    if errors:
        return jsonify({"errors": errors}), 422

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    teacher_id = int(get_jwt_identity())
    if course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this course"}), 403

    lesson = Lesson(title=title, youtube_url=url, course_id=course_id)
    db.session.add(lesson)
    db.session.commit()

    # Fire-and-forget: trigger n8n AI summary pipeline
    _fire_n8n(lesson)

    return jsonify({
        "lesson":  lesson.to_dict(),
        "message": "Lesson saved. AI summary pipeline triggered."
    }), 201


# ── GET /api/lessons/:id ───────────────────────────────────────────────────
# Multi-JOIN: lesson + course + teacher name + AI summary
@lessons_bp.route("/<int:lesson_id>", methods=["GET"])
@jwt_required_custom
def get_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    data   = lesson.to_dict(include_summary=True)

    # Include teacher name via relationship chain
    if lesson.course and lesson.course.teacher:
        data["teacher_name"] = lesson.course.teacher.name
    return jsonify({"lesson": data}), 200


# ── PUT /api/lessons/:id ───────────────────────────────────────────────────
@lessons_bp.route("/<int:lesson_id>", methods=["PUT"])
@teacher_required
def update_lesson(lesson_id):
    lesson     = Lesson.query.get_or_404(lesson_id)
    teacher_id = int(get_jwt_identity())

    if lesson.course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this lesson"}), 403

    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip():
        lesson.title = data["title"].strip()
    if "youtube_url" in data:
        new_url = data["youtube_url"].strip()
        if not YOUTUBE_RE.search(new_url):
            return jsonify({"error": "Invalid YouTube URL"}), 422
        lesson.youtube_url = new_url

    db.session.commit()
    return jsonify({"lesson": lesson.to_dict()}), 200


# ── DELETE /api/lessons/:id ────────────────────────────────────────────────
@lessons_bp.route("/<int:lesson_id>", methods=["DELETE"])
@teacher_required
def delete_lesson(lesson_id):
    lesson     = Lesson.query.get_or_404(lesson_id)
    teacher_id = int(get_jwt_identity())

    if lesson.course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this lesson"}), 403

    db.session.delete(lesson)
    db.session.commit()
    return jsonify({"message": "Lesson deleted"}), 200

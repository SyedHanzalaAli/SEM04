import re
import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt

from extensions import db
from models import Lesson, Course, Enrollment, AISummary
from middleware.auth_middleware import teacher_required, jwt_required_custom

lessons_bp = Blueprint("lessons", __name__, url_prefix="/api/lessons")

YOUTUBE_RE = re.compile(r"(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}")


def _fire_n8n(lesson: Lesson):
    url = current_app.config.get("N8N_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={
            "lesson_id":    lesson.id,
            "lesson_title": lesson.title,
            "youtube_url":  lesson.youtube_url,
        }, timeout=5)
    except requests.RequestException as exc:
        current_app.logger.warning(f"n8n webhook failed: {exc}")


#GET /api/lessons?course_id=
# STRICT FILTERING:
#   - Students must be enrolled in the course to receive any lessons.
#   - Teachers only see lessons for courses they own.
@lessons_bp.route("", methods=["GET"])
@jwt_required_custom
def list_lessons():
    claims     = get_jwt()
    user_id    = int(get_jwt_identity())
    role       = claims.get("role")
    course_id  = request.args.get("course_id", type=int)

    if role == "student":
        if not course_id:
            return jsonify({"error": "course_id is required"}), 422

        #ENROLLMENT GATE
        enrolled = Enrollment.query.filter_by(
            student_id=user_id, course_id=course_id
        ).first()
        if not enrolled:
            return jsonify({
                "error": "Access denied — you are not enrolled in this course"
            }), 403
        # 

        lessons = (
            Lesson.query
            .filter_by(course_id=course_id)
            .order_by(Lesson.created_at.asc())
            .all()
        )

    elif role == "teacher":
        # Teachers only see lessons that belong to courses they own
        query = (
            Lesson.query
            .join(Course, Course.id == Lesson.course_id)
            .filter(Course.teacher_id == user_id)
        )
        if course_id:
            query = query.filter(Lesson.course_id == course_id)
        lessons = query.order_by(Lesson.created_at.asc()).all()

    else:
        lessons = []

    return jsonify({
        "lessons": [l.to_dict(include_summary=True) for l in lessons]
    }), 200


#POST /api/lessons
@lessons_bp.route("", methods=["POST"])
@teacher_required
def create_lesson():
    data      = request.get_json(silent=True) or {}
    title     = (data.get("title") or "").strip()
    url       = (data.get("youtube_url") or "").strip()
    course_id = data.get("course_id")
    teacher_id = int(get_jwt_identity())

    errors = {}
    if not title:
        errors["title"] = "Lesson title is required"
    if not YOUTUBE_RE.search(url):
        errors["youtube_url"] = "Valid YouTube URL required"
    if not course_id:
        errors["course_id"] = "course_id is required"
    if errors:
        return jsonify({"errors": errors}), 422

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    if course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this course"}), 403

    lesson = Lesson(title=title, youtube_url=url, course_id=course_id)
    db.session.add(lesson)
    db.session.commit()

    _fire_n8n(lesson)

    return jsonify({
        "lesson":  lesson.to_dict(),
        "message": "Lesson saved. AI summary pipeline triggered."
    }), 201


#GET /api/lessons/:id 
@lessons_bp.route("/<int:lesson_id>", methods=["GET"])
@jwt_required_custom
def get_lesson(lesson_id):
    claims  = get_jwt()
    user_id = int(get_jwt_identity())
    role    = claims.get("role")
    lesson  = Lesson.query.get_or_404(lesson_id)

    # Students must be enrolled in the course this lesson belongs to
    if role == "student":
        enrolled = Enrollment.query.filter_by(
            student_id=user_id, course_id=lesson.course_id
        ).first()
        if not enrolled:
            return jsonify({"error": "Not enrolled in this course"}), 403

    # Teachers must own the course
    elif role == "teacher" and lesson.course.teacher_id != user_id:
        return jsonify({"error": "You do not own this lesson"}), 403

    data = lesson.to_dict(include_summary=True)
    if lesson.course and lesson.course.teacher:
        data["teacher_name"] = lesson.course.teacher.name
    return jsonify({"lesson": data}), 200


# PUT /api/lessons/:id 
@lessons_bp.route("/<int:lesson_id>", methods=["PUT"])
@teacher_required
def update_lesson(lesson_id):
    teacher_id = int(get_jwt_identity())
    lesson     = Lesson.query.get_or_404(lesson_id)

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


# DELETE /api/lessons/:id 
@lessons_bp.route("/<int:lesson_id>", methods=["DELETE"])
@teacher_required
def delete_lesson(lesson_id):
    teacher_id = int(get_jwt_identity())
    lesson     = Lesson.query.get_or_404(lesson_id)

    if lesson.course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this lesson"}), 403

    db.session.delete(lesson)
    db.session.commit()
    return jsonify({"message": "Lesson deleted"}), 200

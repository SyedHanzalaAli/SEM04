from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from extensions import db
from models import Course, Lesson
from middleware.auth_middleware import jwt_required_custom, teacher_required

courses_bp = Blueprint("courses", __name__, url_prefix="/api/courses")


# ── GET /api/courses ───────────────────────────────────────────────────────
# Returns all courses with teacher name + lesson count (JOIN)
@courses_bp.route("", methods=["GET"])
@jwt_required_custom
def list_courses():
    courses = Course.query.join(Course.teacher).all()
    result = []
    for c in courses:
        count = Lesson.query.filter_by(course_id=c.id).count()
        result.append(c.to_dict(lesson_count=count))
    return jsonify({"courses": result}), 200


# ── POST /api/courses ──────────────────────────────────────────────────────
@courses_bp.route("", methods=["POST"])
@teacher_required
def create_course():
    data        = request.get_json(silent=True) or {}
    title       = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    teacher_id  = int(get_jwt_identity())

    if not title:
        return jsonify({"error": "Course title is required"}), 422

    course = Course(title=title, description=description, teacher_id=teacher_id)
    db.session.add(course)
    db.session.commit()
    return jsonify({"course": course.to_dict()}), 201


# ── GET /api/courses/:id ───────────────────────────────────────────────────
# Returns course details + all lessons with their summary status
@courses_bp.route("/<int:course_id>", methods=["GET"])
@jwt_required_custom
def get_course(course_id):
    course  = Course.query.get_or_404(course_id)
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    count   = len(lessons)

    data = course.to_dict(lesson_count=count)
    data["lessons"] = [l.to_dict(include_summary=True) for l in lessons]
    return jsonify({"course": data}), 200


# ── PUT /api/courses/:id ───────────────────────────────────────────────────
@courses_bp.route("/<int:course_id>", methods=["PUT"])
@teacher_required
def update_course(course_id):
    course     = Course.query.get_or_404(course_id)
    teacher_id = int(get_jwt_identity())

    if course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this course"}), 403

    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip():
        course.title = data["title"].strip()
    if "description" in data:
        course.description = data["description"].strip()

    db.session.commit()
    return jsonify({"course": course.to_dict()}), 200


# ── DELETE /api/courses/:id ────────────────────────────────────────────────
@courses_bp.route("/<int:course_id>", methods=["DELETE"])
@teacher_required
def delete_course(course_id):
    course     = Course.query.get_or_404(course_id)
    teacher_id = int(get_jwt_identity())

    if course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this course"}), 403

    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted successfully"}), 200

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from extensions import db
from models import Enrollment, Course, User
from middleware.auth_middleware import student_required, jwt_required_custom

enrollments_bp = Blueprint("enrollments", __name__, url_prefix="/api/enrollments")


# POST /api/enrollments
# Student enrolls in a course
@enrollments_bp.route("", methods=["POST"])
@student_required
def enroll():
    student_id = int(get_jwt_identity())
    data      = request.get_json(silent=True) or {}
    course_id = data.get("course_id")

    if not course_id:
        return jsonify({"error": "course_id is required"}), 422

    course = Course.query.get_or_404(course_id)

    # Guard: teacher cannot enroll in courses
    if course.teacher_id == student_id:
        return jsonify({"error": "Teachers cannot enroll in their own courses"}), 403

    # Guard: duplicate enrollment
    existing = Enrollment.query.filter_by(
        student_id=student_id, course_id=course_id
    ).first()
    if existing:
        return jsonify({"error": "Already enrolled in this course"}), 409

    enrollment = Enrollment(student_id=student_id, course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()

    return jsonify({
        "message": f"Successfully enrolled in '{course.title}'",
        "enrollment": {
            "id":         enrollment.id,
            "course_id":  course_id,
            "student_id": student_id,
        }
    }), 201


#DELETE /api/enrollments/:course_id
# Student unenrolls from a course (also clears progress for that course)
@enrollments_bp.route("/<int:course_id>", methods=["DELETE"])
@student_required
def unenroll(course_id):
    student_id = int(get_jwt_identity())

    enrollment = Enrollment.query.filter_by(
        student_id=student_id, course_id=course_id
    ).first()
    if not enrollment:
        return jsonify({"error": "You are not enrolled in this course"}), 404

    db.session.delete(enrollment)
    db.session.commit()
    return jsonify({"message": "Successfully unenrolled"}), 200


# GET /api/enrollments
# Returns a list of course_ids the current student is enrolled in
@enrollments_bp.route("", methods=["GET"])
@student_required
def list_enrollments():
    student_id  = int(get_jwt_identity())
    enrollments = Enrollment.query.filter_by(student_id=student_id).all()
    return jsonify({
        "enrolled_course_ids": [e.course_id for e in enrollments]
    }), 200

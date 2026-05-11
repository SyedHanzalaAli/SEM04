from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt
from sqlalchemy import func

from extensions import db
from models import Course, Lesson, Enrollment, User
from middleware.auth_middleware import teacher_required, student_required, jwt_required_custom

courses_bp = Blueprint("courses", __name__, url_prefix="/api/courses")

#  TEACHER ROUTES

# GET /api/courses
# Teacher: own courses with live enrollment counts (SQLAlchemy aggregate)
@courses_bp.route("", methods=["GET"])
@teacher_required
def list_teacher_courses():
    teacher_id = int(get_jwt_identity())

    # LEFT JOIN so courses with 0 enrollments still appear
    results = (
        db.session.query(
            Course,
            func.count(Enrollment.id).label("student_count"),
            func.count(Lesson.id).label("lesson_count"),
        )
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .outerjoin(Lesson,     Lesson.course_id     == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .group_by(Course.id)
        .order_by(Course.created_at.desc())
        .all()
    )

    courses = []
    for course, student_count, lesson_count in results:
        d = course.to_dict()
        d["student_count"] = student_count
        d["lesson_count"]  = lesson_count
        courses.append(d)

    return jsonify({"courses": courses}), 200


# GET /api/courses/:id/students
# Teacher: full list of enrolled students for one course
@courses_bp.route("/<int:course_id>/students", methods=["GET"])
@teacher_required
def course_students(course_id):
    teacher_id = int(get_jwt_identity())
    course     = Course.query.get_or_404(course_id)

    if course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this course"}), 403

    students = (
        db.session.query(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .filter(Enrollment.course_id == course_id)
        .order_by(User.name)
        .all()
    )

    return jsonify({
        "course":        course.title,
        "student_count": len(students),
        "students": [
            {"id": s.id, "name": s.name, "email": s.email}
            for s in students
        ],
    }), 200


# POST /api/courses
@courses_bp.route("", methods=["POST"])
@teacher_required
def create_course():
    teacher_id  = int(get_jwt_identity())
    data        = request.get_json(silent=True) or {}
    title       = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()

    if not title:
        return jsonify({"error": "Course title is required"}), 422

    course = Course(title=title, description=description, teacher_id=teacher_id)
    db.session.add(course)
    db.session.commit()
    return jsonify({"course": course.to_dict()}), 201


#PUT /api/courses/:id 
@courses_bp.route("/<int:course_id>", methods=["PUT"])
@teacher_required
def update_course(course_id):
    teacher_id = int(get_jwt_identity())
    course     = Course.query.get_or_404(course_id)

    if course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this course"}), 403

    data = request.get_json(silent=True) or {}
    if "title"       in data and data["title"].strip():
        course.title       = data["title"].strip()
    if "description" in data:
        course.description = data["description"].strip()

    db.session.commit()
    return jsonify({"course": course.to_dict()}), 200


#  DELETE /api/courses/:id
@courses_bp.route("/<int:course_id>", methods=["DELETE"])
@teacher_required
def delete_course(course_id):
    teacher_id = int(get_jwt_identity())
    course     = Course.query.get_or_404(course_id)

    if course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this course"}), 403

    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted"}), 200


#  STUDENT ROUTES

# GET /api/courses/browse 
# Student: ALL courses for discovery, with enrollment status flag
@courses_bp.route("/browse", methods=["GET"])
@student_required
def browse_courses():
    student_id = int(get_jwt_identity())

    # Aggregate: course + teacher name + total enrolled students
    results = (
        db.session.query(
            Course,
            User.name.label("teacher_name"),
            func.count(Enrollment.id).label("student_count"),
            func.count(Lesson.id).label("lesson_count"),
        )
        .join(User,     User.id          == Course.teacher_id)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .outerjoin(Lesson,     Lesson.course_id     == Course.id)
        .group_by(Course.id, User.name)
        .order_by(Course.created_at.desc())
        .all()
    )

    # Set of course IDs this student is already enrolled in
    my_ids = {
        e.course_id
        for e in Enrollment.query.filter_by(student_id=student_id).all()
    }

    courses = []
    for course, teacher_name, student_count, lesson_count in results:
        d = course.to_dict()
        d["teacher_name"]  = teacher_name
        d["student_count"] = student_count
        d["lesson_count"]  = lesson_count
        d["is_enrolled"]   = course.id in my_ids
        courses.append(d)

    return jsonify({"courses": courses}), 200


#GET /api/courses/my
# Student: ONLY courses they are enrolled in (with lesson counts)
@courses_bp.route("/my", methods=["GET"])
@student_required
def my_courses():
    student_id = int(get_jwt_identity())

    results = (
        db.session.query(
            Course,
            User.name.label("teacher_name"),
            func.count(Lesson.id).label("lesson_count"),
        )
        .join(User,       User.id          == Course.teacher_id)
        .join(Enrollment, (Enrollment.course_id  == Course.id) &
                          (Enrollment.student_id == student_id))
        .outerjoin(Lesson, Lesson.course_id == Course.id)
        .group_by(Course.id, User.name)
        .order_by(Course.title)
        .all()
    )

    courses = []
    for course, teacher_name, lesson_count in results:
        d = course.to_dict()
        d["teacher_name"] = teacher_name
        d["lesson_count"] = lesson_count
        courses.append(d)

    return jsonify({"courses": courses}), 200


#GET /api/courses/:id 
# Both roles: get course detail + lessons
# Students: only if enrolled. Teachers: only if they own it.
@courses_bp.route("/<int:course_id>", methods=["GET"])
@jwt_required_custom
def get_course(course_id):
    claims     = get_jwt()
    user_id    = int(get_jwt_identity())
    role       = claims.get("role")
    course     = Course.query.get_or_404(course_id)

    if role == "student":
        enrolled = Enrollment.query.filter_by(
            student_id=user_id, course_id=course_id
        ).first()
        if not enrolled:
            return jsonify({"error": "Enroll in this course to access its content"}), 403

    elif role == "teacher" and course.teacher_id != user_id:
        return jsonify({"error": "You do not own this course"}), 403

    data = course.to_dict()
    data["lessons"] = [l.to_dict(include_summary=True) for l in
                       sorted(course.lessons, key=lambda x: x.created_at)]
    return jsonify({"course": data}), 200

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from extensions import db
from models import LessonMaterial, Lesson, Course
from middleware.auth_middleware import teacher_required, jwt_required_custom

materials_bp = Blueprint("materials", __name__, url_prefix="/api/materials")

VALID_TYPES = {"notes", "slides", "questions", "link", "other"}


# ── GET /api/materials/lesson/:lesson_id ──────────────────────────────────
# Any authenticated user can view materials for a lesson
@materials_bp.route("/lesson/<int:lesson_id>", methods=["GET"])
@jwt_required_custom
def list_materials(lesson_id):
    Lesson.query.get_or_404(lesson_id)
    mats = (
        LessonMaterial.query
        .filter_by(lesson_id=lesson_id)
        .order_by(LessonMaterial.material_type, LessonMaterial.created_at)
        .all()
    )
    return jsonify({"materials": [m.to_dict() for m in mats]}), 200


# ── POST /api/materials ───────────────────────────────────────────────────
# Teacher posts a new material item for a lesson
@materials_bp.route("", methods=["POST"])
@teacher_required
def create_material():
    teacher_id = int(get_jwt_identity())
    data       = request.get_json(silent=True) or {}

    lesson_id     = data.get("lesson_id")
    title         = (data.get("title") or "").strip()
    material_type = (data.get("material_type") or "other").strip().lower()
    content       = (data.get("content") or "").strip()
    file_url      = (data.get("file_url") or "").strip()

    # ── Validation ─────────────────────────────────────────
    errors = {}
    if not lesson_id:
        errors["lesson_id"] = "lesson_id is required"
    if not title:
        errors["title"] = "Title is required"
    if material_type not in VALID_TYPES:
        errors["material_type"] = f"Must be one of: {', '.join(VALID_TYPES)}"
    if material_type != "link" and not content:
        errors["content"] = "Content is required for non-link materials"
    if material_type == "link" and not file_url:
        errors["file_url"] = "URL is required for link materials"
    if errors:
        return jsonify({"errors": errors}), 422

    # Ownership check — teacher must own the course this lesson belongs to
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this lesson"}), 403

    mat = LessonMaterial(
        lesson_id=lesson_id,
        teacher_id=teacher_id,
        title=title,
        material_type=material_type,
        content=content or None,
        file_url=file_url or None,
    )
    db.session.add(mat)
    db.session.commit()
    return jsonify({"material": mat.to_dict()}), 201


# ── PUT /api/materials/:id ────────────────────────────────────────────────
@materials_bp.route("/<int:mat_id>", methods=["PUT"])
@teacher_required
def update_material(mat_id):
    teacher_id = int(get_jwt_identity())
    mat        = LessonMaterial.query.get_or_404(mat_id)

    if mat.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this material"}), 403

    data = request.get_json(silent=True) or {}
    if "title"         in data and data["title"].strip():
        mat.title         = data["title"].strip()
    if "content"       in data:
        mat.content       = data["content"].strip() or None
    if "file_url"      in data:
        mat.file_url      = data["file_url"].strip() or None
    if "material_type" in data and data["material_type"] in VALID_TYPES:
        mat.material_type = data["material_type"]

    db.session.commit()
    return jsonify({"material": mat.to_dict()}), 200


# ── DELETE /api/materials/:id ─────────────────────────────────────────────
@materials_bp.route("/<int:mat_id>", methods=["DELETE"])
@teacher_required
def delete_material(mat_id):
    teacher_id = int(get_jwt_identity())
    mat        = LessonMaterial.query.get_or_404(mat_id)

    if mat.teacher_id != teacher_id:
        return jsonify({"error": "You do not own this material"}), 403

    db.session.delete(mat)
    db.session.commit()
    return jsonify({"message": "Material deleted"}), 200

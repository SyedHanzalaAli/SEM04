import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User
from middleware.auth_middleware import jwt_required_custom

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ── POST /api/auth/register ────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "")
    role     = (data.get("role") or "").strip()

    # ── Validation ─────────────────────────────────────────
    errors = {}
    if not name:
        errors["name"] = "Name is required"
    if not EMAIL_RE.match(email):
        errors["email"] = "Valid email address required"
    if len(password) < 6:
        errors["password"] = "Password must be at least 6 characters"
    if role not in ("teacher", "student"):
        errors["role"] = "Role must be 'teacher' or 'student'"
    if errors:
        return jsonify({"errors": errors}), 422

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered"}), 409

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )
    return jsonify({"token": token, "user": user.to_dict()}), 201


# ── POST /api/auth/login ───────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "")

    errors = {}
    if not EMAIL_RE.match(email):
        errors["email"] = "Valid email address required"
    if not password:
        errors["password"] = "Password is required"
    if errors:
        return jsonify({"errors": errors}), 422

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )
    return jsonify({"token": token, "user": user.to_dict()}), 200


# ── GET /api/auth/me ───────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required_custom
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify({"user": user.to_dict()}), 200

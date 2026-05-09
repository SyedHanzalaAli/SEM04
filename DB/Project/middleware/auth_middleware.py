from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def jwt_required_custom(fn):
    """Require a valid JWT — any role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper


def teacher_required(fn):
    """Require a valid JWT with role == 'teacher'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "teacher":
            return jsonify({"error": "Teacher access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


def student_required(fn):
    """Require a valid JWT with role == 'student'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "student":
            return jsonify({"error": "Student access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

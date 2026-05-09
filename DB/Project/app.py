from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import db, jwt

from routes.auth      import auth_bp
from routes.courses   import courses_bp
from routes.lessons   import lessons_bp
from routes.summaries import summaries_bp
from routes.progress  import progress_bp
from routes.quizzes   import quizzes_bp      # NEW
from routes.materials import materials_bp    # NEW


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Blueprints ─────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(lessons_bp)
    app.register_blueprint(summaries_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(quizzes_bp)      # NEW
    app.register_blueprint(materials_bp)    # NEW

    # ── JWT error handlers ─────────────────────────────────
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Authorization token missing", "detail": reason}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": "Invalid token", "detail": reason}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired — please log in again"}), 401

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)

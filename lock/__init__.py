import os
import secrets
from pathlib import Path

from flask import Flask, abort, request, session


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    # Set LOCK_SECRET_KEY to keep sessions valid across process restarts.
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("LOCK_SECRET_KEY", secrets.token_hex(32)),
        DATABASE=str(Path(app.instance_path) / "lock.sqlite"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("LOCK_HTTPS", "0") == "1",
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from . import db

    db.init_app(app)

    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_csrf_token():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return {"csrf_token": token}

    @app.before_request
    def protect_post_requests():
        # Browser forms and fetch() submissions share the same CSRF check.
        if request.method != "POST":
            return None
        expected = session.get("csrf_token")
        received = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, received):
            abort(400, description="A sessão do formulário expirou. Atualize a página.")
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; img-src 'self' data:; "
            "script-src 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    with app.app_context():
        db.init_db()
        db.seed_db()

    return app

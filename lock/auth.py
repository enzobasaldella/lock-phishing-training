import functools
import re

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db


bp = Blueprint("auth", __name__, url_prefix="/auth")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT id, name, email, role, active FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if g.user is None or not g.user["active"]:
            session.clear()
            g.user = None


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Entre na plataforma para continuar.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped_view(**kwargs):
        if g.user["role"] != "admin":
            flash("Esta área é exclusiva para administradores.", "error")
            return redirect(url_for("main.dashboard"))
        return view(**kwargs)

    return wrapped_view


@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")
        error = None

        if not 2 <= len(name) <= 100:
            error = "Informe um nome entre 2 e 100 caracteres."
        elif not EMAIL_PATTERN.match(email) or len(email) > 150:
            error = "Informe um e-mail válido."
        elif len(password) < 8:
            error = "A senha deve possuir ao menos 8 caracteres."
        elif password != confirmation:
            error = "A confirmação de senha não confere."

        if error is None:
            database = get_db()
            try:
                database.execute(
                    """
                    INSERT INTO users (name, email, password_hash, role)
                    VALUES (?, ?, ?, 'participant')
                    """,
                    (name, email, generate_password_hash(password)),
                )
                database.commit()
            except Exception as exception:
                if "UNIQUE" in str(exception):
                    error = "Já existe uma conta com este e-mail."
                else:
                    raise
            else:
                flash("Conta criada. Agora você já pode entrar.", "success")
                return redirect(url_for("auth.login"))

        flash(error, "error")

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE email = ? AND active = 1", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("E-mail ou senha inválidos.", "error")
        else:
            # Drop pre-login session data before binding the authenticated user.
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Olá, {user['name'].split()[0]}!", "success")
            target = request.args.get("next", "")
            # Accept only local paths; a crafted next URL must not redirect off-site.
            if not target.startswith("/") or target.startswith("//"):
                target = url_for("main.dashboard")
            return redirect(target)

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    session.clear()
    flash("Sessão encerrada com segurança.", "success")
    return redirect(url_for("main.index"))

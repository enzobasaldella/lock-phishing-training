from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import admin_required
from .db import get_db


bp = Blueprint("admin", __name__, url_prefix="/admin")


def log_action(action, entity, entity_id=None):
    database = get_db()
    database.execute(
        "INSERT INTO audit_logs (user_id, action, entity, entity_id) VALUES (?, ?, ?, ?)",
        (g.user["id"], action, entity, entity_id),
    )
    database.commit()


def validate_module_form():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    content = request.form.get("content", "").strip()
    published = int(request.form.get("published") == "1")
    if not 3 <= len(title) <= 120:
        return None, "O título deve possuir entre 3 e 120 caracteres."
    if not 10 <= len(description) <= 300:
        return None, "A descrição deve possuir entre 10 e 300 caracteres."
    if not 20 <= len(content) <= 5000:
        return None, "O conteúdo deve possuir entre 20 e 5.000 caracteres."
    return (title, description, content, published), None


@bp.get("")
@admin_required
def dashboard():
    database = get_db()
    totals = {
        "participants": database.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'participant' AND active = 1"
        ).fetchone()[0],
        "modules": database.execute("SELECT COUNT(*) FROM modules").fetchone()[0],
        "attempts": database.execute("SELECT COUNT(*) FROM scenario_attempts").fetchone()[0],
        "accuracy": database.execute(
            "SELECT COALESCE(ROUND(AVG(is_correct) * 100), 0) FROM scenario_attempts"
        ).fetchone()[0],
    }
    module_stats = database.execute(
        """
        SELECT m.id, m.title, m.published,
               COUNT(DISTINCT mp.user_id) AS participants,
               COALESCE(ROUND(AVG(mp.percentage)), 0) AS average_progress
        FROM modules m
        LEFT JOIN module_progress mp ON mp.module_id = m.id
        GROUP BY m.id ORDER BY m.sort_order, m.id
        """
    ).fetchall()
    return render_template("admin/dashboard.html", totals=totals, module_stats=module_stats)


@bp.get("/modules")
@admin_required
def modules():
    rows = get_db().execute(
        """
        SELECT m.*,
               (SELECT COUNT(*) FROM scenarios WHERE module_id = m.id) AS scenario_count,
               (SELECT COUNT(*) FROM questions WHERE module_id = m.id) AS question_count
        FROM modules m ORDER BY m.sort_order, m.id
        """
    ).fetchall()
    return render_template("admin/modules.html", modules=rows)


@bp.route("/modules/new", methods=("GET", "POST"))
@admin_required
def module_create():
    if request.method == "POST":
        values, error = validate_module_form()
        if error:
            flash(error, "error")
        else:
            database = get_db()
            cursor = database.execute(
                """
                INSERT INTO modules (title, description, content, published, sort_order)
                VALUES (?, ?, ?, ?, COALESCE((SELECT MAX(sort_order) + 1 FROM modules), 1))
                """,
                values,
            )
            database.commit()
            log_action("criou", "module", cursor.lastrowid)
            flash("Módulo criado.", "success")
            return redirect(url_for("admin.module_edit", module_id=cursor.lastrowid))
    return render_template("admin/module_form.html", module=None, scenarios=[], questions=[])


@bp.route("/modules/<int:module_id>/edit", methods=("GET", "POST"))
@admin_required
def module_edit(module_id):
    database = get_db()
    module = database.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if module is None:
        abort(404)

    if request.method == "POST":
        values, error = validate_module_form()
        if error:
            flash(error, "error")
        else:
            database.execute(
                """
                UPDATE modules SET title = ?, description = ?, content = ?, published = ?
                WHERE id = ?
                """,
                (*values, module_id),
            )
            database.commit()
            log_action("editou", "module", module_id)
            flash("Módulo atualizado.", "success")
            return redirect(url_for("admin.module_edit", module_id=module_id))

    scenarios = database.execute(
        "SELECT * FROM scenarios WHERE module_id = ? ORDER BY id", (module_id,)
    ).fetchall()
    questions = database.execute(
        "SELECT * FROM questions WHERE module_id = ? ORDER BY sort_order, id", (module_id,)
    ).fetchall()
    return render_template(
        "admin/module_form.html", module=module, scenarios=scenarios, questions=questions
    )


def scenario_values(module_id):
    decision_raw = request.form.get("decision_correct", "").strip()
    decision_correct = int(decision_raw) if decision_raw in {"1", "2", "3"} else None
    values = (
        module_id,
        request.form.get("title", "").strip(),
        request.form.get("kind", ""),
        request.form.get("sender", "").strip(),
        request.form.get("subject", "").strip(),
        request.form.get("message", "").strip(),
        request.form.get("correct_classification", ""),
        request.form.get("explanation", "").strip(),
        request.form.get("red_flags", "").strip(),
        request.form.get("claimed_brand", "").strip() or None,
        request.form.get("difficulty", "").strip() or None,
        request.form.get("context", "").strip() or None,
        request.form.get("cta_label", "").strip() or None,
        request.form.get("display_target", "").strip() or None,
        request.form.get("decision_prompt", "").strip() or None,
        request.form.get("decision_a", "").strip() or None,
        request.form.get("decision_b", "").strip() or None,
        request.form.get("decision_c", "").strip() or None,
        decision_correct,
        request.form.get("decision_explanation", "").strip() or None,
        request.form.get("safe_action", "").strip() or None,
        request.form.get("decision_kind", "action").strip(),
    )
    if not 3 <= len(values[1]) <= 120:
        return None, "Informe um título válido."
    if values[2] not in {"email", "sms", "message"}:
        return None, "Selecione o tipo de cenário."
    if values[6] not in {"safe", "suspicious", "phishing"}:
        return None, "Selecione a classificação correta."
    if any(not value for value in (values[3], values[4], values[5], values[7], values[8])):
        return None, "Preencha todos os campos do cenário."
    if values[10] and values[10] not in {"basico", "intermediario", "avancado"}:
        return None, "Selecione uma dificuldade válida."
    if values[13]:
        # Targets are display-only; restrict hosts even though no link is rendered.
        host = values[13].split("/", 1)[0].lower()
        approved_official = values[6] == "safe" and host in {"myaccount.google.com", "www.netflix.com"}
        if "://" in values[13] or not (host.endswith((".example", ".test")) or approved_official):
            return None, "Use um domínio .example/.test ou um dos domínios oficiais permitidos para avisos seguros; não inclua https://."
    decision_fields = values[14:20]
    if values[21] not in {"action", "evidence"}:
        return None, "Selecione um tipo de pergunta válido."
    if any(field is not None for field in decision_fields) and not all(
        field is not None for field in decision_fields
    ):
        return None, "Para adicionar uma decisão, preencha a pergunta, as três opções, a correta e a explicação."
    return values, None


@bp.route("/modules/<int:module_id>/scenarios/new", methods=("GET", "POST"))
@admin_required
def scenario_create(module_id):
    module = get_db().execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if module is None:
        abort(404)
    if request.method == "POST":
        values, error = scenario_values(module_id)
        if error:
            flash(error, "error")
        else:
            database = get_db()
            cursor = database.execute(
                """
                INSERT INTO scenarios
                    (module_id, title, kind, sender, subject, message,
                     correct_classification, explanation, red_flags, claimed_brand,
                     difficulty, context, cta_label, display_target, decision_prompt,
                     decision_a, decision_b, decision_c, decision_correct,
                     decision_explanation, safe_action, decision_kind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            database.commit()
            log_action("criou", "scenario", cursor.lastrowid)
            flash("Cenário criado.", "success")
            return redirect(url_for("admin.module_edit", module_id=module_id))
    return render_template("admin/scenario_form.html", module=module, scenario=None)


@bp.route("/scenarios/<int:scenario_id>/edit", methods=("GET", "POST"))
@admin_required
def scenario_edit(scenario_id):
    database = get_db()
    scenario = database.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
    if scenario is None:
        abort(404)
    module = database.execute("SELECT * FROM modules WHERE id = ?", (scenario["module_id"],)).fetchone()
    if request.method == "POST":
        values, error = scenario_values(scenario["module_id"])
        if error:
            flash(error, "error")
        else:
            # A new version prevents old scores from being re-graded after an edit.
            database.execute(
                """
                UPDATE scenarios SET title = ?, kind = ?, sender = ?, subject = ?,
                    message = ?, correct_classification = ?, explanation = ?, red_flags = ?,
                    claimed_brand = ?, difficulty = ?, context = ?, cta_label = ?,
                    display_target = ?, decision_prompt = ?, decision_a = ?,
                    decision_b = ?, decision_c = ?, decision_correct = ?,
                    decision_explanation = ?, safe_action = ?, decision_kind = ?,
                    content_version = content_version + 1
                WHERE id = ?
                """,
                (*values[1:], scenario_id),
            )
            database.commit()
            log_action("editou", "scenario", scenario_id)
            flash("Cenário atualizado.", "success")
            return redirect(url_for("admin.module_edit", module_id=scenario["module_id"]))
    return render_template("admin/scenario_form.html", module=module, scenario=scenario)


@bp.post("/scenarios/<int:scenario_id>/delete")
@admin_required
def scenario_delete(scenario_id):
    database = get_db()
    scenario = database.execute("SELECT module_id FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
    if scenario is None:
        abort(404)
    database.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
    database.commit()
    log_action("removeu", "scenario", scenario_id)
    flash("Cenário removido.", "success")
    return redirect(url_for("admin.module_edit", module_id=scenario["module_id"]))


def question_values(module_id):
    prompt = request.form.get("prompt", "").strip()
    explanation = request.form.get("explanation", "").strip()
    options = [request.form.get(f"option_{letter}", "").strip() for letter in "abcd"]
    try:
        correct_index = int(request.form.get("correct_option", ""))
    except ValueError:
        correct_index = -1
    if len(prompt) < 10 or len(explanation) < 10:
        return None, "Informe o enunciado e a explicação."
    if any(len(option) < 2 for option in options) or correct_index not in range(4):
        return None, "Preencha quatro alternativas e selecione a correta."
    return (module_id, prompt, explanation, options, correct_index), None


@bp.route("/modules/<int:module_id>/questions/new", methods=("GET", "POST"))
@admin_required
def question_create(module_id):
    database = get_db()
    module = database.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if module is None:
        abort(404)
    if request.method == "POST":
        values, error = question_values(module_id)
        if error:
            flash(error, "error")
        else:
            _, prompt, explanation, options, correct_index = values
            cursor = database.execute(
                """
                INSERT INTO questions (module_id, prompt, explanation, sort_order)
                VALUES (?, ?, ?, COALESCE((SELECT MAX(sort_order) + 1 FROM questions WHERE module_id = ?), 1))
                """,
                (module_id, prompt, explanation, module_id),
            )
            database.executemany(
                "INSERT INTO alternatives (question_id, text, is_correct) VALUES (?, ?, ?)",
                [(cursor.lastrowid, option, int(index == correct_index)) for index, option in enumerate(options)],
            )
            database.commit()
            log_action("criou", "question", cursor.lastrowid)
            flash("Questão criada.", "success")
            return redirect(url_for("admin.module_edit", module_id=module_id))
    return render_template("admin/question_form.html", module=module, question=None, alternatives=[])


@bp.route("/questions/<int:question_id>/edit", methods=("GET", "POST"))
@admin_required
def question_edit(question_id):
    database = get_db()
    question = database.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    if question is None:
        abort(404)
    module = database.execute("SELECT * FROM modules WHERE id = ?", (question["module_id"],)).fetchone()
    alternatives = database.execute(
        "SELECT * FROM alternatives WHERE question_id = ? ORDER BY id", (question_id,)
    ).fetchall()
    if request.method == "POST":
        values, error = question_values(question["module_id"])
        if error:
            flash(error, "error")
        else:
            _, prompt, explanation, options, correct_index = values
            database.execute(
                "UPDATE questions SET prompt = ?, explanation = ? WHERE id = ?",
                (prompt, explanation, question_id),
            )
            database.execute("DELETE FROM alternatives WHERE question_id = ?", (question_id,))
            database.executemany(
                "INSERT INTO alternatives (question_id, text, is_correct) VALUES (?, ?, ?)",
                [(question_id, option, int(index == correct_index)) for index, option in enumerate(options)],
            )
            database.commit()
            log_action("editou", "question", question_id)
            flash("Questão atualizada.", "success")
            return redirect(url_for("admin.module_edit", module_id=question["module_id"]))
    return render_template(
        "admin/question_form.html",
        module=module,
        question=question,
        alternatives=alternatives,
    )


@bp.post("/questions/<int:question_id>/delete")
@admin_required
def question_delete(question_id):
    database = get_db()
    question = database.execute("SELECT module_id FROM questions WHERE id = ?", (question_id,)).fetchone()
    if question is None:
        abort(404)
    database.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    database.commit()
    log_action("removeu", "question", question_id)
    flash("Questão removida.", "success")
    return redirect(url_for("admin.module_edit", module_id=question["module_id"]))


@bp.get("/audit")
@admin_required
def audit():
    logs = get_db().execute(
        """
        SELECT a.*, u.name AS user_name
        FROM audit_logs a LEFT JOIN users u ON u.id = a.user_id
        ORDER BY a.created_at DESC, a.id DESC LIMIT 100
        """
    ).fetchall()
    return render_template("admin/audit.html", logs=logs)

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db


bp = Blueprint("main", __name__)
CLASSIFICATION_LABELS = {
    "safe": "Seguro",
    "suspicious": "Suspeito",
    "phishing": "Phishing",
}


def update_progress(user_id, module_id):
    database = get_db()
    scenario_total = database.execute(
        "SELECT COUNT(*) FROM scenarios WHERE module_id = ?", (module_id,)
    ).fetchone()[0]
    # Repeated attempts count once per scenario; the optional quiz is one step.
    scenario_done = database.execute(
        """
        SELECT COUNT(DISTINCT scenario_id)
        FROM scenario_attempts
        WHERE user_id = ?
          AND scenario_id IN (SELECT id FROM scenarios WHERE module_id = ?)
        """,
        (user_id, module_id),
    ).fetchone()[0]
    has_quiz = database.execute(
        "SELECT EXISTS(SELECT 1 FROM questions WHERE module_id = ?)", (module_id,)
    ).fetchone()[0]
    quiz_done = database.execute(
        "SELECT EXISTS(SELECT 1 FROM quiz_attempts WHERE user_id = ? AND module_id = ?)",
        (user_id, module_id),
    ).fetchone()[0]

    total_steps = scenario_total + has_quiz
    completed_steps = scenario_done + quiz_done
    percentage = round((completed_steps / total_steps) * 100) if total_steps else 0
    completed = int(total_steps > 0 and completed_steps == total_steps)
    database.execute(
        """
        INSERT INTO module_progress (user_id, module_id, percentage, completed, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, module_id) DO UPDATE SET
            percentage = excluded.percentage,
            completed = excluded.completed,
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, module_id, percentage, completed),
    )
    database.commit()


def get_published_module(module_id):
    module = get_db().execute(
        "SELECT * FROM modules WHERE id = ? AND published = 1", (module_id,)
    ).fetchone()
    if module is None:
        abort(404)
    return module


def get_published_module_by_slug(slug):
    module = get_db().execute(
        "SELECT * FROM modules WHERE slug = ? AND published = 1", (slug,)
    ).fetchone()
    if module is None:
        abort(404)
    return module


def get_exercise_rows(user_id, module_id):
    return get_db().execute(
        """
        SELECT s.*,
               EXISTS(SELECT 1 FROM scenario_attempts sa
                      WHERE sa.scenario_id = s.id AND sa.user_id = ?) AS attempted,
               EXISTS(SELECT 1 FROM scenario_attempts sa
                      WHERE sa.scenario_id = s.id AND sa.user_id = ?
                        AND sa.content_version = s.content_version) AS current_attempted
        FROM scenarios s WHERE s.module_id = ?
        ORDER BY s.sort_order, s.id
        """,
        (user_id, user_id, module_id),
    ).fetchall()


def build_simulation_result(scenario, answer, decision_answer):
    classification_correct = answer == scenario["correct_classification"]
    has_decision = bool(scenario["decision_prompt"])
    decision_correct = (
        decision_answer == scenario["decision_correct"] if has_decision else None
    )
    # When present, the follow-up choice is required for a full score.
    correct = classification_correct and (decision_correct if has_decision else True)
    return {
        "correct": correct,
        "classification_correct": classification_correct,
        "decision_correct": decision_correct,
        "answer": CLASSIFICATION_LABELS[answer],
        "expected": CLASSIFICATION_LABELS[scenario["correct_classification"]],
        "decision_selected": scenario[f"decision_{'abc'[decision_answer - 1]}"] if has_decision else None,
        "decision_expected": scenario[f"decision_{'abc'[scenario['decision_correct'] - 1]}"] if has_decision else None,
    }


@bp.get("/")
def index():
    if g.user is not None:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@bp.get("/dashboard")
@login_required
def dashboard():
    database = get_db()
    modules = database.execute(
        """
        SELECT m.*, COALESCE(mp.percentage, 0) AS progress,
               COALESCE(mp.completed, 0) AS completed,
               (SELECT COUNT(*) FROM scenarios s WHERE s.module_id = m.id) AS scenarios_count,
               (SELECT COUNT(*) FROM questions q WHERE q.module_id = m.id) AS questions_count
        FROM modules m
        LEFT JOIN module_progress mp
          ON mp.module_id = m.id AND mp.user_id = ?
        WHERE m.published = 1
        ORDER BY m.sort_order, m.id
        """,
        (g.user["id"],),
    ).fetchall()
    guide = next((item for item in modules if item["slug"] == "cartilha-phishing"), None)
    exercise = next((item for item in modules if item["slug"] == "exercicios-phishing"), None)
    scenarios = get_exercise_rows(g.user["id"], exercise["id"]) if exercise else []
    reviewed = sum(bool(item["attempted"]) for item in scenarios)
    return render_template(
        "dashboard.html", guide=guide, exercise=exercise,
        scenarios=scenarios, reviewed=reviewed,
    )


@bp.get("/guide")
@login_required
def guide():
    return module_detail(module_id=get_published_module_by_slug("cartilha-phishing")["id"])


@bp.get("/exercises")
@login_required
def exercises():
    return module_detail(module_id=get_published_module_by_slug("exercicios-phishing")["id"])


@bp.post("/guide/complete")
@login_required
def guide_complete():
    module = get_published_module_by_slug("cartilha-phishing")
    database = get_db()
    database.execute(
        """INSERT INTO module_progress (user_id, module_id, percentage, completed)
           VALUES (?, ?, 100, 1)
           ON CONFLICT(user_id, module_id) DO UPDATE SET
               percentage = 100, completed = 1, updated_at = CURRENT_TIMESTAMP""",
        (g.user["id"], module["id"]),
    )
    database.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"completed": True})
    return redirect(url_for("main.guide"))


@bp.get("/modules/<int:module_id>")
@login_required
def module_detail(module_id):
    module = get_published_module(module_id)
    database = get_db()
    scenarios = get_exercise_rows(g.user["id"], module_id)
    question_count = database.execute(
        "SELECT COUNT(*) FROM questions WHERE module_id = ?", (module_id,)
    ).fetchone()[0]
    progress = database.execute(
        "SELECT * FROM module_progress WHERE user_id = ? AND module_id = ?",
        (g.user["id"], module_id),
    ).fetchone()
    template = {
        "cartilha-phishing": "guide.html",
        "exercicios-phishing": "exercises.html",
    }.get(module["slug"], "module_detail.html")
    return render_template(
        template,
        module=module,
        scenarios=scenarios,
        question_count=question_count,
        progress=progress,
    )


@bp.route("/simulations/<int:scenario_id>", methods=("GET", "POST"))
@login_required
def simulation(scenario_id):
    database = get_db()
    scenario = database.execute(
        """
        SELECT s.*, m.title AS module_title, m.published
        FROM scenarios s JOIN modules m ON m.id = s.module_id
        WHERE s.id = ?
        """,
        (scenario_id,),
    ).fetchone()
    if scenario is None or not scenario["published"]:
        abort(404)

    position = database.execute(
        """SELECT COUNT(*) FROM scenarios WHERE module_id = ?
           AND (sort_order < ? OR (sort_order = ? AND id <= ?))""",
        (scenario["module_id"], scenario["sort_order"], scenario["sort_order"], scenario_id),
    ).fetchone()[0]
    total = database.execute(
        "SELECT COUNT(*) FROM scenarios WHERE module_id = ?",
        (scenario["module_id"],),
    ).fetchone()[0]
    next_scenario = database.execute(
        """SELECT id FROM scenarios WHERE module_id = ?
           AND (sort_order > ? OR (sort_order = ? AND id > ?))
           ORDER BY sort_order, id LIMIT 1""",
        (scenario["module_id"], scenario["sort_order"], scenario["sort_order"], scenario_id),
    ).fetchone()
    has_quiz = database.execute(
        "SELECT EXISTS(SELECT 1 FROM questions WHERE module_id = ?)",
        (scenario["module_id"],),
    ).fetchone()[0]

    result = None
    saved_result = False
    module_completed = False
    current_progress = database.execute(
        "SELECT completed FROM module_progress WHERE user_id = ? AND module_id = ?",
        (g.user["id"], scenario["module_id"]),
    ).fetchone()
    if current_progress:
        module_completed = bool(current_progress["completed"])
    if request.method == "GET" and request.args.get("refazer") != "1":
        # Never re-grade an older attempt against a revised exercise answer key.
        latest = database.execute(
            """SELECT answer, decision_answer FROM scenario_attempts
               WHERE user_id = ? AND scenario_id = ? AND content_version = ?
               ORDER BY id DESC LIMIT 1""",
            (g.user["id"], scenario_id, scenario["content_version"]),
        ).fetchone()
        if latest:
            result = build_simulation_result(
                scenario, latest["answer"], latest["decision_answer"]
            )
            saved_result = True
    if request.method == "POST":
        answer = request.form.get("answer", "")
        decision_raw = request.form.get("decision_answer", "")
        has_decision = bool(scenario["decision_prompt"])
        valid_decision = decision_raw in {"1", "2", "3"}
        if answer not in CLASSIFICATION_LABELS:
            error = "Escolha uma classificação antes de confirmar."
        elif has_decision and not valid_decision:
            error = "Escolha também uma resposta para a segunda pergunta."
        else:
            error = None
        if error:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": error}), 400
            flash(error, "error")
        else:
            decision_answer = int(decision_raw) if has_decision else None
            result = build_simulation_result(scenario, answer, decision_answer)
            database.execute(
                """
                INSERT INTO scenario_attempts
                    (user_id, scenario_id, answer, is_correct, score,
                     decision_answer, decision_is_correct, content_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    g.user["id"], scenario_id, answer, int(result["correct"]),
                    100 if result["correct"] else 0, decision_answer,
                    int(result["decision_correct"]) if has_decision else None,
                    scenario["content_version"],
                ),
            )
            database.commit()
            update_progress(g.user["id"], scenario["module_id"])
            module_completed = bool(
                database.execute(
                    "SELECT completed FROM module_progress WHERE user_id = ? AND module_id = ?",
                    (g.user["id"], scenario["module_id"]),
                ).fetchone()[0]
            )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                # Return just the result panel so the page can update in place.
                return jsonify({
                    "html": render_template(
                        "simulation_decision.html", scenario=scenario, labels=CLASSIFICATION_LABELS,
                        result=result, next_scenario=next_scenario, has_quiz=has_quiz,
                        module_completed=module_completed,
                    ),
                    "completed": module_completed,
                })

    return render_template(
        "simulation.html",
        scenario=scenario,
        labels=CLASSIFICATION_LABELS,
        result=result,
        position=position,
        total=total,
        next_scenario=next_scenario,
        has_quiz=has_quiz,
        module_completed=module_completed,
        saved_result=saved_result,
    )


@bp.route("/modules/<int:module_id>/quiz", methods=("GET", "POST"))
@login_required
def quiz(module_id):
    module = get_published_module(module_id)
    database = get_db()
    question_rows = database.execute(
        "SELECT * FROM questions WHERE module_id = ? ORDER BY sort_order, id", (module_id,)
    ).fetchall()
    questions = []
    for question in question_rows:
        alternatives = database.execute(
            "SELECT id, text, is_correct FROM alternatives WHERE question_id = ? ORDER BY id",
            (question["id"],),
        ).fetchall()
        questions.append({"question": question, "alternatives": alternatives})

    if not questions:
        abort(404)

    result = None
    if request.method == "POST":
        answers = {}
        missing = False
        for item in questions:
            key = f"question_{item['question']['id']}"
            value = request.form.get(key, "")
            valid_ids = {str(alt["id"]) for alt in item["alternatives"]}
            if value not in valid_ids:
                missing = True
                break
            answers[item["question"]["id"]] = int(value)

        if missing:
            flash("Responda todas as questões antes de finalizar.", "error")
        else:
            correct_count = 0
            feedback = []
            for item in questions:
                question = item["question"]
                selected_id = answers[question["id"]]
                selected = next(alt for alt in item["alternatives"] if alt["id"] == selected_id)
                correct = bool(selected["is_correct"])
                correct_count += int(correct)
                feedback.append({"prompt": question["prompt"], "correct": correct, "explanation": question["explanation"]})

            database.execute(
                "INSERT INTO quiz_attempts (user_id, module_id, score, total) VALUES (?, ?, ?, ?)",
                (g.user["id"], module_id, correct_count, len(questions)),
            )
            database.commit()
            update_progress(g.user["id"], module_id)
            result = {
                "score": correct_count,
                "total": len(questions),
                "percentage": round(correct_count / len(questions) * 100),
                "feedback": feedback,
            }

    return render_template("quiz.html", module=module, questions=questions, result=result)


@bp.get("/progress")
@login_required
def progress():
    database = get_db()
    modules = database.execute(
        """
        SELECT m.id, m.title, COALESCE(mp.percentage, 0) AS percentage,
               COALESCE(mp.completed, 0) AS completed
        FROM modules m
        LEFT JOIN module_progress mp
          ON mp.module_id = m.id AND mp.user_id = ?
        WHERE m.published = 1
        ORDER BY m.sort_order, m.id
        """,
        (g.user["id"],),
    ).fetchall()
    attempts = database.execute(
        """
        SELECT sa.created_at, sa.is_correct, sa.score, s.id AS scenario_id,
               s.title, m.title AS module_title,
               (sa.content_version < s.content_version) AS older_edition
        FROM scenario_attempts sa
        JOIN scenarios s ON s.id = sa.scenario_id
        JOIN modules m ON m.id = s.module_id
        WHERE sa.user_id = ? AND m.published = 1
        ORDER BY sa.created_at DESC LIMIT 10
        """,
        (g.user["id"],),
    ).fetchall()
    return render_template(
        "progress.html", modules=modules, attempts=attempts
    )

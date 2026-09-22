import tempfile
import unittest
from pathlib import Path

from lock import create_app
from lock.db import get_db


class LockApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = str(Path(self.temporary_directory.name) / "test.sqlite")
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "DATABASE": database_path,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def login(self, email="aluno@lock.local", password="Lock@123"):
        self.client.get("/auth/login")
        return self.client.post(
            "/auth/login",
            data={"email": email, "password": password, "csrf_token": self.csrf_token()},
            follow_redirects=True,
        )

    def test_home_has_security_headers(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        page = response.get_data(as_text=True)
        self.assertIn("Conteúdo de conscientização sobre phishing", page)
        self.assertNotIn("Uma leitura. Oito exercícios.", page)
        self.assertNotIn("Prática controlada", page)

    def test_participant_can_login_and_complete_simulation(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("O que é phishing", response.get_data(as_text=True))
        self.assertIn("Exercícios de phishing", response.get_data(as_text=True))

        with self.app.app_context():
            case = get_db().execute(
                "SELECT id, decision_correct FROM scenarios WHERE case_key = 'linkedin-convite'"
            ).fetchone()
            next_case = get_db().execute(
                "SELECT id FROM scenarios WHERE case_key = 'google-acesso'"
            ).fetchone()[0]

        self.client.get(f"/simulations/{case['id']}")
        response = self.client.post(
            f"/simulations/{case['id']}",
            data={"answer": "phishing", "decision_answer": case["decision_correct"], "csrf_token": self.csrf_token()},
            follow_redirects=True,
        )
        self.assertIn("Boa análise.", response.get_data(as_text=True))
        self.assertIn(f'href="/simulations/{next_case}"', response.get_data(as_text=True))
        with self.app.app_context():
            attempt = get_db().execute(
                "SELECT is_correct, score FROM scenario_attempts WHERE user_id = 2"
            ).fetchone()
            self.assertEqual((attempt["is_correct"], attempt["score"]), (1, 100))

    def test_participant_can_complete_quiz(self):
        self.login()
        with self.app.app_context():
            get_db().execute("UPDATE modules SET published = 1 WHERE id = 1")
            get_db().commit()
        self.client.get("/modules/1/quiz")
        with self.app.app_context():
            correct = get_db().execute(
                """
                SELECT q.id AS question_id, a.id AS alternative_id
                FROM questions q JOIN alternatives a ON a.question_id = q.id
                WHERE q.module_id = 1 AND a.is_correct = 1
                """
            ).fetchall()
        form = {f"question_{row['question_id']}": row["alternative_id"] for row in correct}
        form["csrf_token"] = self.csrf_token()
        response = self.client.post("/modules/1/quiz", data=form, follow_redirects=True)
        self.assertIn("100%", response.get_data(as_text=True))

    def test_participant_cannot_access_admin(self):
        self.login()
        response = self.client.get("/admin", follow_redirects=True)
        self.assertIn("exclusiva para administradores", response.get_data(as_text=True))

    def test_admin_can_create_a_module_and_audit_is_recorded(self):
        self.login("admin@lock.local", "Admin@123")
        self.client.get("/admin/modules/new")
        response = self.client.post(
            "/admin/modules/new",
            data={
                "csrf_token": self.csrf_token(),
                "title": "Módulo de teste",
                "description": "Descrição completa para o módulo de teste.",
                "content": "Conteúdo educativo suficiente para validar o cadastro seguro.",
                "published": "1",
            },
            follow_redirects=True,
        )
        self.assertIn("Módulo criado", response.get_data(as_text=True))
        with self.app.app_context():
            log = get_db().execute(
                "SELECT action, entity FROM audit_logs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertEqual((log["action"], log["entity"]), ("criou", "module"))

    def test_seeded_pages_render_for_both_roles(self):
        self.login()
        with self.app.app_context():
            first_case = get_db().execute(
                "SELECT id FROM scenarios WHERE case_key = 'linkedin-convite'"
            ).fetchone()[0]
        for path in ("/dashboard", "/guide", "/exercises", "/progress", f"/simulations/{first_case}"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get("/modules/1").status_code, 404)

        self.client.get("/auth/login")
        with self.client.session_transaction() as session:
            session.clear()
        self.login("admin@lock.local", "Admin@123")
        admin_paths = (
            "/admin",
            "/admin/modules",
            "/admin/modules/1/edit",
            "/admin/modules/1/scenarios/new",
            "/admin/scenarios/1/edit",
            "/admin/modules/1/questions/new",
            "/admin/questions/1/edit",
            "/admin/audit",
        )
        for path in admin_paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_progress_meters_do_not_depend_on_blocked_inline_styles(self):
        self.login()
        for path in ("/dashboard", "/exercises", "/progress"):
            with self.subTest(path=path):
                page = self.client.get(path).get_data(as_text=True)
                self.assertIn('class="progress-meter"', page)
                self.assertNotIn('style="width:', page)

    def test_google_and_microsoft_have_inert_email_clients(self):
        self.login()
        with self.app.app_context():
            cases = get_db().execute(
                "SELECT id, case_key FROM scenarios WHERE case_key IN ('google-acesso', 'microsoft-acesso')"
            ).fetchall()
        for case in cases:
            with self.subTest(case=case["case_key"]):
                page = self.client.get(f"/simulations/{case['id']}").get_data(as_text=True)
                self.assertIn("client-shell", page)
                self.assertIn("Caixa de entrada", page)
                self.assertNotIn("message-banner", page)

    def test_eight_cases_are_complete_and_idempotent(self):
        with self.app.app_context():
            cases = get_db().execute(
                "SELECT case_key, difficulty, correct_classification, decision_prompt, decision_kind FROM scenarios WHERE case_key IS NOT NULL ORDER BY sort_order"
            ).fetchall()
            self.assertEqual(
                {row["case_key"] for row in cases},
                {"linkedin-convite", "google-acesso", "amazon-pagamento", "netflix-pagamento", "uber-novo-acesso", "microsoft-acesso", "rh-memorando", "office-download"},
            )
            self.assertEqual(len(cases), 8)
            self.assertEqual(
                {row["difficulty"] for row in cases},
                {"basico", "intermediario", "avancado"},
            )
            self.assertEqual(
                {row["correct_classification"] for row in cases},
                {"safe", "suspicious", "phishing"},
            )
            self.assertTrue(all(row["decision_prompt"] for row in cases))
            self.assertEqual(
                {label: sum(row["correct_classification"] == label for row in cases) for label in ("phishing", "safe", "suspicious")},
                {"phishing": 4, "safe": 2, "suspicious": 2},
            )
            self.assertEqual(sum(row["decision_kind"] == "evidence" for row in cases), 4)

        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "DATABASE": self.app.config["DATABASE"],
            }
        )
        with self.app.app_context():
            self.assertEqual(
                get_db().execute("SELECT COUNT(*) FROM scenarios WHERE case_key IS NOT NULL").fetchone()[0],
                8,
            )
            self.assertEqual(
                get_db().execute("SELECT COUNT(*) FROM modules WHERE published = 1").fetchone()[0],
                2,
            )

    def test_brand_case_requires_both_decisions_and_has_inert_target(self):
        self.login()
        with self.app.app_context():
            case = get_db().execute(
                "SELECT id, decision_correct, display_target FROM scenarios WHERE case_key = 'linkedin-convite'"
            ).fetchone()
            case_id, correct_decision, target = case

        page = self.client.get(f"/simulations/{case_id}").get_data(as_text=True)
        self.assertIn("Ver destino do botão", page)
        self.assertIn(target, page)
        self.assertNotIn(f'href="https://{target}', page)

        response = self.client.post(
            f"/simulations/{case_id}",
            data={"answer": "phishing", "csrf_token": self.csrf_token()},
            follow_redirects=True,
        )
        self.assertIn("Escolha também uma resposta para a segunda pergunta", response.get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(
                get_db().execute("SELECT COUNT(*) FROM scenario_attempts WHERE scenario_id = ?", (case_id,)).fetchone()[0],
                0,
            )

        response = self.client.post(
            f"/simulations/{case_id}",
            data={
                "answer": "phishing",
                "decision_answer": str(correct_decision),
                "csrf_token": self.csrf_token(),
            },
            follow_redirects=True,
        )
        self.assertIn("Boa análise.", response.get_data(as_text=True))
        with self.app.app_context():
            attempt = get_db().execute(
                "SELECT score, decision_is_correct FROM scenario_attempts WHERE scenario_id = ?",
                (case_id,),
            ).fetchone()
            self.assertEqual((attempt["score"], attempt["decision_is_correct"]), (100, 1))

    def test_brand_case_explains_an_incorrect_action(self):
        self.login()
        with self.app.app_context():
            case = get_db().execute(
                "SELECT id, decision_correct FROM scenarios WHERE case_key = 'amazon-pagamento'"
            ).fetchone()
            wrong_decision = "1" if case["decision_correct"] != 1 else "2"

        self.client.get(f"/simulations/{case['id']}")
        response = self.client.post(
            f"/simulations/{case['id']}",
            data={
                "answer": "phishing",
                "decision_answer": wrong_decision,
                "csrf_token": self.csrf_token(),
            },
        )
        page = response.get_data(as_text=True)
        self.assertIn("Você classificou bem. Reveja a pista.", page)
        self.assertIn("Sua pista:", page)
        self.assertIn("Pista decisiva:", page)
        with self.app.app_context():
            attempt = get_db().execute(
                "SELECT score, decision_is_correct FROM scenario_attempts WHERE scenario_id = ?",
                (case["id"],),
            ).fetchone()
            self.assertEqual((attempt["score"], attempt["decision_is_correct"]), (0, 0))

    def test_eight_cases_complete_the_exercise_module(self):
        self.login()
        with self.app.app_context():
            cases = get_db().execute(
                "SELECT id, correct_classification, decision_correct FROM scenarios WHERE case_key IS NOT NULL ORDER BY sort_order"
            ).fetchall()
            module_id = get_db().execute(
                "SELECT id FROM modules WHERE slug = 'exercicios-phishing'"
            ).fetchone()[0]

        for case in cases:
            self.assertEqual(self.client.get(f"/simulations/{case['id']}").status_code, 200)
            response = self.client.post(
                f"/simulations/{case['id']}",
                data={
                    "answer": case["correct_classification"],
                    "decision_answer": str(case["decision_correct"]),
                    "csrf_token": self.csrf_token(),
                },
            )
            self.assertIn("Boa análise.", response.get_data(as_text=True))

        module_page = self.client.get(f"/modules/{module_id}").get_data(as_text=True)
        self.assertIn("100% analisado", module_page)
        with self.app.app_context():
            progress = get_db().execute(
                "SELECT percentage, completed FROM module_progress WHERE user_id = 2 AND module_id = ?",
                (module_id,),
            ).fetchone()
            self.assertEqual((progress["percentage"], progress["completed"]), (100, 1))

    def test_revised_case_keeps_historical_attempt_without_reusing_old_feedback(self):
        self.login()
        with self.app.app_context():
            database = get_db()
            case = database.execute(
                "SELECT id, decision_correct FROM scenarios WHERE case_key = 'netflix-pagamento'"
            ).fetchone()
            database.execute(
                "UPDATE scenarios SET correct_classification = 'phishing', content_version = 1 WHERE id = ?",
                (case["id"],),
            )
            database.commit()

        response = self.client.post(
            f"/simulations/{case['id']}",
            data={"answer": "phishing", "decision_answer": str(case["decision_correct"]), "csrf_token": self.csrf_token()},
        )
        self.assertIn("Boa análise.", response.get_data(as_text=True))
        create_app({"TESTING": True, "SECRET_KEY": "test-secret-key", "DATABASE": self.app.config["DATABASE"]})
        with self.app.app_context():
            database = get_db()
            updated = database.execute(
                "SELECT correct_classification, content_version FROM scenarios WHERE id = ?", (case["id"],)
            ).fetchone()
            attempt = database.execute(
                "SELECT score, content_version FROM scenario_attempts WHERE scenario_id = ?", (case["id"],)
            ).fetchone()
            self.assertEqual((updated["correct_classification"], updated["content_version"]), ("safe", 2))
            self.assertEqual((attempt["score"], attempt["content_version"]), (100, 1))
        page = self.client.get(f"/simulations/{case['id']}").get_data(as_text=True)
        self.assertIn("Qual é a sua análise?", page)
        self.assertNotIn("SUA ÚLTIMA RESPOSTA", page)
        self.assertIn("Nova edição →", self.client.get("/exercises").get_data(as_text=True))
        self.assertIn("Edição anterior. Refazer análise", self.client.get("/progress").get_data(as_text=True))

    def test_ajax_answer_and_guide_reading_persist_after_restart(self):
        self.login()
        self.client.get("/guide")
        guide_response = self.client.post(
            "/guide/complete",
            data={"csrf_token": self.csrf_token()},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(guide_response.status_code, 200)
        self.assertTrue(guide_response.json["completed"])

        with self.app.app_context():
            case = get_db().execute(
                "SELECT id, decision_correct FROM scenarios WHERE case_key = 'google-acesso'"
            ).fetchone()
            case_id, correct_decision = case

        ajax_response = self.client.post(
            f"/simulations/{case_id}",
            data={
                "answer": "safe",
                "decision_answer": str(correct_decision),
                "csrf_token": self.csrf_token(),
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(ajax_response.status_code, 200)
        self.assertTrue(ajax_response.is_json)
        self.assertIn("Boa análise.", ajax_response.json["html"])
        self.assertIn("SUA ÚLTIMA RESPOSTA", self.client.get(f"/simulations/{case_id}").get_data(as_text=True))
        self.assertIn("Conferir resposta", self.client.get(f"/simulations/{case_id}?refazer=1").get_data(as_text=True))

        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "DATABASE": self.app.config["DATABASE"],
            }
        )
        with self.app.app_context():
            self.assertEqual(
                get_db().execute("SELECT COUNT(*) FROM scenario_attempts WHERE scenario_id = ?", (case_id,)).fetchone()[0],
                1,
            )
            self.assertEqual(
                get_db().execute("SELECT completed FROM module_progress WHERE user_id = 2 AND module_id = (SELECT id FROM modules WHERE slug = 'cartilha-phishing')").fetchone()[0],
                1,
            )

    def test_ajax_rejects_incomplete_answer_without_saving(self):
        self.login()
        with self.app.app_context():
            case_id = get_db().execute(
                "SELECT id FROM scenarios WHERE case_key = 'netflix-pagamento'"
            ).fetchone()[0]
        response = self.client.post(
            f"/simulations/{case_id}",
            data={"answer": "phishing", "csrf_token": self.csrf_token()},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Escolha também", response.json["error"])
        with self.app.app_context():
            self.assertEqual(
                get_db().execute("SELECT COUNT(*) FROM scenario_attempts WHERE scenario_id = ?", (case_id,)).fetchone()[0],
                0,
            )

    def test_branded_email_previews_are_distinct_and_inert(self):
        self.login()
        previews = (
            ("linkedin-convite", "linkedin-email", "ana-ribeiro-profile.png"),
            ("google-acesso", "google-email", "google-wordmark"),
            ("amazon-pagamento", "amazon-email", "fone-sem-fio-produto.png"),
            ("netflix-pagamento", "netflix-email", "netflix-mark"),
            ("uber-novo-acesso", "uber-email", "uber-details"),
            ("microsoft-acesso", "microsoft-alert-email", "microsoft-login-details"),
            ("office-download", "office-email", "office-apps"),
        )
        with self.app.app_context():
            case_ids = {
                row["case_key"]: row["id"]
                for row in get_db().execute("SELECT id, case_key FROM scenarios WHERE case_key IS NOT NULL")
            }

        for case_key, preview_class, visual_detail in previews:
            with self.subTest(case=case_key):
                response = self.client.get(f"/simulations/{case_ids[case_key]}")
                self.assertEqual(response.status_code, 200)
                page = response.get_data(as_text=True)
                preview = page.split(f'class="brand-email {preview_class}"', 1)[1].split("</article>", 1)[0]
                self.assertIn(visual_detail, preview)
                self.assertIn('aria-label="Botão ilustrativo, não clicável"', preview)
                self.assertNotIn("href=", preview)

        hr = self.client.get(f"/simulations/{case_ids['rh-memorando']}").get_data(as_text=True)
        self.assertIn("hr-attachment", hr)
        self.assertIn("mariana-lopes-profile.png", hr)
        self.assertIn('aria-label="Anexo ilustrativo, não clicável"', hr)

        for asset in ("ana-ribeiro-profile.png", "mariana-lopes-profile.png", "fone-sem-fio-produto.png"):
            image = self.client.get(f"/static/{asset}")
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image.mimetype, "image/png")
            image.close()

    def test_admin_can_create_and_edit_rich_scenario(self):
        self.login("admin@lock.local", "Admin@123")
        with self.app.app_context():
            module_id = get_db().execute(
                "SELECT id FROM modules WHERE slug = 'exercicios-phishing'"
            ).fetchone()[0]

        form = {
            "csrf_token": self.csrf_token(),
            "title": "Cenário de teste",
            "kind": "email",
            "sender": "Equipe <equipe@empresa.example>",
            "subject": "Assunto de teste",
            "message": "Mensagem fictícia de teste para treinamento.",
            "correct_classification": "phishing",
            "explanation": "A mensagem solicita uma ação por um canal inseguro.",
            "red_flags": "Domínio estranho; pedido inesperado",
            "claimed_brand": "Empresa fictícia",
            "difficulty": "basico",
            "context": "Você recebeu uma mensagem que não esperava.",
            "cta_label": "Conferir aviso",
            "display_target": "aviso.empresa.example/conta",
            "decision_prompt": "Qual é a melhor ação?",
            "decision_a": "Usar o botão da mensagem.",
            "decision_b": "Abrir o aplicativo oficial.",
            "decision_c": "Repassar a mensagem.",
            "decision_correct": "2",
            "decision_explanation": "O aplicativo oficial permite confirmar o aviso com segurança.",
            "safe_action": "Procure o serviço por um caminho independente.",
        }
        response = self.client.post(
            f"/admin/modules/{module_id}/scenarios/new", data=form, follow_redirects=True
        )
        self.assertIn("Cenário criado", response.get_data(as_text=True))
        with self.app.app_context():
            scenario = get_db().execute(
                "SELECT id, decision_correct, display_target FROM scenarios WHERE title = ?",
                (form["title"],),
            ).fetchone()
            self.assertEqual(scenario["decision_correct"], 2)
            self.assertEqual(scenario["display_target"], form["display_target"])
            scenario_id = scenario["id"]

        edit_page = self.client.get(f"/admin/scenarios/{scenario_id}/edit")
        self.assertIn("Cenário de teste", edit_page.get_data(as_text=True))
        form["title"] = "Cenário revisado"
        response = self.client.post(
            f"/admin/scenarios/{scenario_id}/edit", data=form, follow_redirects=True
        )
        self.assertIn("Cenário atualizado", response.get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(
                get_db().execute("SELECT content_version FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()[0],
                2,
            )

    def test_post_without_csrf_is_rejected(self):
        response = self.client.post(
            "/auth/login", data={"email": "aluno@lock.local", "password": "Lock@123"}
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

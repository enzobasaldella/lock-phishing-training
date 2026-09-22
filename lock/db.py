import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash


EXERCISE_DESCRIPTION = (
    "Analise mensagens de compras, contas digitais e trabalho para reconhecer sinais de phishing."
)
EXERCISE_CONTENT = (
    "Leia a mensagem como se tivesse acabado de chegar. Observe o remetente, "
    "o pedido e o destino indicado. Depois, classifique a mensagem e responda "
    "à pergunta sobre a pista principal ou a melhor atitude. Alguns avisos são "
    "legítimos; outros exigem confirmação. A explicação mostra o que pesou em cada caso."
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db():
    database = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        database.executescript(schema_file.read().decode("utf-8"))
    migrate_db(database)
    database.commit()


def migrate_db(database):
    """Add exercise fields without replacing an existing local database."""
    additions = {
        "modules": {"slug": "TEXT"},
        "scenarios": {
            "case_key": "TEXT",
            "claimed_brand": "TEXT",
            "difficulty": "TEXT",
            "context": "TEXT",
            "cta_label": "TEXT",
            "display_target": "TEXT",
            "decision_prompt": "TEXT",
            "decision_a": "TEXT",
            "decision_b": "TEXT",
            "decision_c": "TEXT",
            "decision_correct": "INTEGER",
            "decision_explanation": "TEXT",
            "decision_kind": "TEXT NOT NULL DEFAULT 'action'",
            "content_version": "INTEGER NOT NULL DEFAULT 1",
            "safe_action": "TEXT",
            "sort_order": "INTEGER NOT NULL DEFAULT 1000",
        },
        "scenario_attempts": {
            "decision_answer": "INTEGER",
            "decision_is_correct": "INTEGER",
            "content_version": "INTEGER NOT NULL DEFAULT 1",
        },
    }
    for table, columns in additions.items():
        existing = {row["name"] for row in database.execute(f"PRAGMA table_info({table})")}
        for name, sql_type in columns.items():
            if name not in existing:
                database.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
    database.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_slug ON modules(slug)")
    database.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_scenarios_case_key ON scenarios(case_key)")


def revise_seed_case(database, case, previous_values):
    """Upgrade only untouched seed fields; retain attempts from older editions."""
    changed = False
    for field, previous in previous_values.items():
        column = "correct_classification" if field == "classification" else field
        updated = case[field]
        if previous == updated:
            continue
        cursor = database.execute(
            f"UPDATE scenarios SET {column} = ? WHERE case_key = ? AND content_version = 1 AND {column} IS ?",
            (updated, case["case_key"], previous),
        )
        changed = changed or cursor.rowcount > 0
    if changed:
        database.execute(
            "UPDATE scenarios SET content_version = content_version + 1 WHERE case_key = ?",
            (case["case_key"],),
        )


def seed_db():
    database = get_db()
    if database.execute("SELECT COUNT(*) FROM modules").fetchone()[0] > 0:
        refine_demo_content(database)
        seed_brand_cases(database)
        seed_extra_cases(database)
        organize_learning_content(database)
        return

    database.executemany(
        """
        INSERT INTO users (name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                "Administrador Lock",
                "admin@lock.local",
                generate_password_hash("Admin@123"),
                "admin",
            ),
            (
                "Aluno Demonstração",
                "aluno@lock.local",
                generate_password_hash("Lock@123"),
                "participant",
            ),
        ],
    )

    modules = [
        (
            "Fundamentos do phishing",
            "Entenda como uma mensagem comum pode ser usada para provocar uma decisão apressada.",
            "Phishing não depende apenas de erros de português ou de uma aparência amadora. Uma mensagem pode citar uma compra recente, usar o nome de um serviço conhecido e parecer perfeitamente organizada. O objetivo é fazer você agir antes de conferir.\n\nPergunte-se: a mensagem pede senha, pagamento, instalação ou alguma decisão urgente? Eu esperava receber esse aviso? Consigo confirmar a informação por um caminho que eu já conhecia antes da mensagem?\n\nSe houver dúvida, interrompa a ação. A urgência de quem enviou não precisa virar a sua urgência.",
            1,
            1,
        ),
        (
            "Links, remetentes e anexos",
            "Leia além do nome exibido: confira para onde botões, arquivos e pedidos realmente levam.",
            "Um nome familiar no campo do remetente é só uma pista, não uma garantia. Verifique o endereço completo e, principalmente, o destino de botões e links. Um domínio que contém o nome da marca pode pertencer a outra pessoa.\n\nAnexos inesperados também merecem pausa, sobretudo quando a mensagem pressiona você a abrir, ativar conteúdo ou instalar algo. Mesmo um aviso com visual convincente pode esconder um caminho inseguro.\n\nQuando quiser conferir, abra o aplicativo oficial ou digite você mesmo um endereço já conhecido. Não use o link da própria mensagem para provar que ela é verdadeira.",
            1,
            2,
        ),
        (
            "Como agir com segurança",
            "Tenha um plano simples para confirmar avisos suspeitos e reagir se já tiver clicado.",
            "Primeiro, não continue pela mensagem. Para confirmar uma cobrança, abra o aplicativo do serviço. Para confirmar uma solicitação de trabalho, use um contato interno que você já conhece. Se houver canal de reporte na sua organização, encaminhe a suspeita por ele.\n\nSe você já digitou uma senha em uma página duvidosa, troque-a pelo site ou aplicativo oficial e encerre sessões abertas. Ative a verificação em duas etapas, quando disponível. Se houve pagamento, instalação de arquivo ou exposição de dados, procure imediatamente o suporte responsável.\n\nPedir ajuda cedo costuma limitar o problema. O objetivo não é encontrar culpados, mas recuperar o controle.",
            1,
            3,
        ),
    ]
    database.executemany(
        """
        INSERT INTO modules (title, description, content, published, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        modules,
    )

    scenarios = [
        (
            1,
            "Sua conta será bloqueada",
            "email",
            "atendimento@seguranca-conta.example",
            "Ação imediata necessária",
            "Detectamos um problema. Confirme sua senha nos próximos 15 minutos para evitar o bloqueio.",
            "phishing",
            "A mensagem cria urgência e pede uma senha. Serviços legítimos não solicitam sua senha por e-mail.",
            "Urgência artificial; pedido de senha; domínio desconhecido.",
        ),
        (
            1,
            "Aviso interno de manutenção",
            "message",
            "Equipe de TI",
            "Manutenção programada",
            "O sistema ficará indisponível amanhã, das 20h às 21h. Nenhuma ação é necessária.",
            "safe",
            "A mensagem é apenas informativa: não pressiona, não pede dados e não oferece link ou anexo.",
            "Ausência de pedido sensível; informação verificável pelos canais internos.",
        ),
        (
            2,
            "Entrega aguardando pagamento",
            "sms",
            "Entrega Rápida",
            "Taxa pendente",
            "Seu pacote foi retido. Pague agora em entrega-rapida-pagamento.example para liberar.",
            "phishing",
            "O endereço demonstrativo tenta parecer oficial e a cobrança inesperada induz a uma ação rápida.",
            "Cobrança inesperada; pressão; endereço semelhante a uma marca.",
        ),
        (
            2,
            "Documento compartilhado inesperado",
            "email",
            "contato.desconhecido@exemplo.test",
            "Você recebeu um documento",
            "Confira o orçamento no arquivo Orcamento.zip anexado.",
            "suspicious",
            "Um anexo compactado e inesperado exige confirmação por outro canal antes de ser aberto.",
            "Remetente desconhecido; anexo inesperado; arquivo compactado.",
        ),
        (
            3,
            "Pedido urgente do gestor",
            "message",
            "Novo número",
            "Transferência confidencial",
            "Troquei de número. Faça uma transferência urgente e não ligue porque estou em reunião.",
            "phishing",
            "A solicitação combina autoridade, urgência, sigilo e impedimento de confirmação.",
            "Novo contato; transferência; urgência; pedido de sigilo.",
        ),
    ]
    database.executemany(
        """
        INSERT INTO scenarios
            (module_id, title, kind, sender, subject, message, correct_classification,
             explanation, red_flags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        scenarios,
    )

    questions = [
        (
            1,
            "Qual atitude é mais segura diante de um pedido inesperado de senha?",
            "Senhas não devem ser compartilhadas por mensagem. Confirme pelo canal oficial.",
            1,
            [
                ("Responder rapidamente para evitar bloqueio", 0),
                ("Confirmar pelo canal oficial sem usar o link recebido", 1),
                ("Encaminhar a mensagem a colegas", 0),
                ("Informar apenas parte da senha", 0),
            ],
        ),
        (
            1,
            "Qual recurso emocional aparece com frequência em phishing?",
            "Urgência e medo reduzem o tempo que a vítima dedica à verificação.",
            2,
            [
                ("Calma e ausência de prazo", 0),
                ("Urgência e medo", 1),
                ("Explicação técnica completa", 0),
                ("Confirmação presencial", 0),
            ],
        ),
        (
            2,
            "Como verificar um link recebido por mensagem?",
            "A opção mais segura é evitar o link e usar um endereço ou aplicativo já conhecido.",
            1,
            [
                ("Abrir e conferir depois", 0),
                ("Digitar o endereço oficial conhecido ou usar o aplicativo", 1),
                ("Confiar quando houver um cadeado", 0),
                ("Repassar para outra pessoa testar", 0),
            ],
        ),
        (
            3,
            "O que fazer ao receber um pedido urgente de transferência de um novo número?",
            "A identidade deve ser confirmada por um canal independente antes de qualquer ação.",
            1,
            [
                ("Transferir um valor pequeno primeiro", 0),
                ("Confirmar com a pessoa por um contato já conhecido", 1),
                ("Pedir uma foto do documento no mesmo chat", 0),
                ("Responder com seus dados para confirmar identidade", 0),
            ],
        ),
    ]
    for module_id, prompt, explanation, sort_order, alternatives in questions:
        cursor = database.execute(
            """
            INSERT INTO questions (module_id, prompt, explanation, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (module_id, prompt, explanation, sort_order),
        )
        database.executemany(
            """
            INSERT INTO alternatives (question_id, text, is_correct)
            VALUES (?, ?, ?)
            """,
            [(cursor.lastrowid, text, is_correct) for text, is_correct in alternatives],
        )

    database.commit()
    refine_demo_content(database)
    seed_brand_cases(database)
    seed_extra_cases(database)
    organize_learning_content(database)


def refine_demo_content(database):
    """Refresh untouched sample lessons while preserving user-edited modules."""
    revisions = [
        (
            "Fundamentos do phishing",
            "Aprenda o que é phishing e por que mensagens urgentes merecem atenção.",
            "Phishing é uma tentativa de manipular pessoas para que revelem dados ou executem ações inseguras. Golpistas costumam explorar urgência, medo, autoridade e recompensas. Antes de agir, pare, verifique o remetente por outro canal e desconfie de pedidos inesperados.",
            "Entenda como uma mensagem comum pode ser usada para provocar uma decisão apressada.",
            "Phishing não depende apenas de erros de português ou de uma aparência amadora. Uma mensagem pode citar uma compra recente, usar o nome de um serviço conhecido e parecer perfeitamente organizada. O objetivo é fazer você agir antes de conferir.\n\nPergunte-se: a mensagem pede senha, pagamento, instalação ou alguma decisão urgente? Eu esperava receber esse aviso? Consigo confirmar a informação por um caminho que eu já conhecia antes da mensagem?\n\nSe houver dúvida, interrompa a ação. A urgência de quem enviou não precisa virar a sua urgência.",
        ),
        (
            "Links, remetentes e anexos",
            "Pratique a conferência dos principais sinais de uma mensagem suspeita.",
            "O nome exibido não prova quem enviou a mensagem. Confira o endereço completo, observe domínios parecidos e não abra anexos inesperados. Em vez de usar o link recebido, acesse o serviço digitando o endereço conhecido no navegador ou usando o aplicativo oficial.",
            "Leia além do nome exibido: confira para onde botões, arquivos e pedidos realmente levam.",
            "Um nome familiar no campo do remetente é só uma pista, não uma garantia. Verifique o endereço completo e, principalmente, o destino de botões e links. Um domínio que contém o nome da marca pode pertencer a outra pessoa.\n\nAnexos inesperados também merecem pausa, sobretudo quando a mensagem pressiona você a abrir, ativar conteúdo ou instalar algo. Mesmo um aviso com visual convincente pode esconder um caminho inseguro.\n\nQuando quiser conferir, abra o aplicativo oficial ou digite você mesmo um endereço já conhecido. Não use o link da própria mensagem para provar que ela é verdadeira.",
        ),
        (
            "Como agir com segurança",
            "Saiba interromper o golpe, confirmar solicitações e comunicar incidentes.",
            "Quando uma mensagem gerar dúvida, não responda nem use os contatos fornecidos nela. Confirme a solicitação por um canal oficial independente. Se você clicou ou informou dados, altere a senha, encerre sessões, ative autenticação em dois fatores e procure o responsável pelo serviço.",
            "Tenha um plano simples para confirmar avisos suspeitos e reagir se já tiver clicado.",
            "Primeiro, não continue pela mensagem. Para confirmar uma cobrança, abra o aplicativo do serviço. Para confirmar uma solicitação de trabalho, use um contato interno que você já conhece. Se houver canal de reporte na sua organização, encaminhe a suspeita por ele.\n\nSe você já digitou uma senha em uma página duvidosa, troque-a pelo site ou aplicativo oficial e encerre sessões abertas. Ative a verificação em duas etapas, quando disponível. Se houve pagamento, instalação de arquivo ou exposição de dados, procure imediatamente o suporte responsável.\n\nPedir ajuda cedo costuma limitar o problema. O objetivo não é encontrar culpados, mas recuperar o controle.",
        ),
    ]
    for title, old_description, old_content, new_description, new_content in revisions:
        database.execute(
            """
            UPDATE modules SET description = ?, content = ?
            WHERE title = ? AND description = ? AND content = ?
            """,
            (new_description, new_content, title, old_description, old_content),
        )
    database.commit()


def seed_brand_cases(database):
    """Insert original, inert phishing cases once; keep later admin edits."""
    module_slug = "exercicios-phishing"
    module = database.execute(
        "SELECT id, slug FROM modules WHERE slug IN (?, 'caixa-de-entrada') ORDER BY CASE WHEN slug = ? THEN 0 ELSE 1 END LIMIT 1",
        (module_slug, module_slug),
    ).fetchone()
    if module is None:
        cursor = database.execute(
            """
            INSERT INTO modules (slug, title, description, content, published, sort_order)
            VALUES (?, ?, ?, ?, 1, 0)
            """,
            (
                module_slug,
                "Exercícios de phishing",
                EXERCISE_DESCRIPTION,
                EXERCISE_CONTENT,
            ),
        )
        module_id = cursor.lastrowid
    else:
        module_id = module["id"]
        if module["slug"] == "caixa-de-entrada":
            database.execute(
                "UPDATE modules SET slug = ? WHERE id = ?", (module_slug, module_id)
            )

    cases = [
        {
            "case_key": "linkedin-convite",
            "title": "Um convite fora da rede",
            "difficulty": "basico",
            "claimed_brand": "LinkedIn",
            "context": "Você recebeu um convite de uma pessoa que não conhece. O assunto parece rotineiro, mas o botão pede que você confirme seu acesso.",
            "sender": "Convites LinkedIn <convites@linkedin-alertas.example>",
            "subject": "Ana Ribeiro quer se conectar com você",
            "message": "Você e Ana Ribeiro têm 6 conexões em comum. Para ver o perfil completo e responder ao convite, confirme seu acesso.",
            "cta_label": "Ver perfil",
            "display_target": "linkedin-convites.example/acesso",
            "explanation": "O convite é um pretexto para levar você a uma página de acesso que não pertence ao serviço mencionado. Contatos em comum e foto de perfil não comprovam a origem da mensagem.",
            "red_flags": "Domínio do remetente diferente do serviço; botão leva a outro domínio; pedido de confirmação de acesso para uma ação simples",
            "decision_prompt": "Qual detalhe pesa mais na identificação do golpe?",
            "decision_a": "A foto de Ana e as conexões em comum.",
            "decision_b": "O destino do botão usa outro domínio e exige acesso para ver um convite.",
            "decision_c": "O texto não contém erros de português.",
            "decision_correct": 2,
            "decision_explanation": "Fotos e conexões em comum podem ser copiadas. O endereço do botão e a exigência de login são as evidências mais fortes.",
            "decision_kind": "evidence",
            "safe_action": "Abra o aplicativo oficial e confira a área de convites. Se o convite não estiver lá, reporte a mensagem.",
        },
        {
            "case_key": "amazon-pagamento",
            "title": "O pagamento de uma compra",
            "difficulty": "intermediario",
            "claimed_brand": "Amazon",
            "context": "Você comprou um fone recentemente. A foto, o item e o número do pedido parecem familiares; agora confira também o endereço do botão.",
            "sender": "Central de pedidos <pedidos@central-amazon.example>",
            "subject": "Problema com o pagamento do pedido #BR-843126",
            "message": "Olá,\n\nNão foi possível concluir o pagamento do pedido #BR-843126. A operadora pode recusar uma cobrança quando os dados do cartão estão desatualizados.\n\nPara evitar o cancelamento, atualize a forma de pagamento em até 5 dias. Não responda a este e-mail com dados do cartão.",
            "cta_label": "Revisar pagamento",
            "display_target": "pagamentos-amazon.example/pedido/BR-843126",
            "explanation": "A frase sobre segurança torna o texto convincente, mas o botão aponta para um domínio que apenas contém o nome da marca. O número de pedido, sozinho, não confirma que a cobrança existe.",
            "red_flags": "Destino do botão fora do serviço mencionado; número e foto do produto não autenticam o e-mail; prazo curto aumenta a pressão",
            "decision_prompt": "Apesar dos detalhes do pedido, qual evidência é decisiva?",
            "decision_a": "A foto do produto, que confirma a origem do e-mail.",
            "decision_b": "O prazo de cinco dias, que prova a cobrança.",
            "decision_c": "O botão leva a um domínio diferente do serviço citado.",
            "decision_correct": 3,
            "decision_explanation": "Uma mensagem pode trazer item e número convincentes, mas esses dados não tornam confiável um destino externo.",
            "decision_kind": "evidence",
            "safe_action": "Confira a situação do pedido no aplicativo ou site oficial, sem usar o botão do e-mail.",
        },
        {
            "case_key": "uber-novo-acesso",
            "title": "Acesso desconhecido à conta",
            "difficulty": "intermediario",
            "claimed_brand": "Uber",
            "context": "Chega um aviso de acesso por um aparelho que você não reconhece. O nome do remetente parece correto, mas isso não valida o botão.",
            "sender": "Segurança Uber <seguranca@uber.com>",
            "subject": "Novo acesso detectado na sua conta",
            "message": "Se não reconhece este acesso, proteja sua conta pelo botão abaixo. Se foi você, nenhuma ação é necessária.",
            "cta_label": "Proteger minha conta",
            "display_target": "conta-uber-verificacao.example/seguranca",
            "explanation": "Mesmo quando o endereço do remetente parece correto, ele não basta como prova. O destino do botão é um domínio diferente do serviço citado. O alerta de acesso é usado para provocar uma reação rápida.",
            "red_flags": "Destino do botão fora do serviço; alerta que provoca urgência; remetente exibido não é prova suficiente",
            "decision_prompt": "O acesso pode ser real. Qual atitude protege sua conta sem confiar na mensagem?",
            "decision_a": "Abrir o aplicativo oficial por conta própria e revisar a segurança da conta.",
            "decision_b": "Usar o botão do e-mail porque o remetente parece correto.",
            "decision_c": "Ignorar o aviso até receber uma segunda mensagem.",
            "decision_correct": 1,
            "decision_explanation": "Um alerta real merece atenção, mas a verificação deve começar pelo aplicativo oficial, não pelo link recebido.",
            "safe_action": "Acesse o aplicativo oficial. Revise sessões e senha; se necessário, procure o suporte por um canal conhecido.",
        },
        {
            "case_key": "office-download",
            "title": "Uma licença de software inesperada",
            "difficulty": "avancado",
            "claimed_brand": "Microsoft 365",
            "context": "Você usa ferramentas de escritório no trabalho. A mensagem diz que sua organização liberou recursos premium e pede instalação imediata.",
            "sender": "Equipe de licenças <licencas@intranet-office.example>",
            "subject": "Sua licença premium está pronta para ativação",
            "message": "Um administrador da sua organização liberou recursos premium para os aplicativos de escritório e armazenamento em nuvem.\n\nSua nova licença inclui Word, Excel, PowerPoint, Teams e 1 TB de espaço na nuvem.\n\nPara começar, entre com sua conta corporativa e senha atual e baixe os aplicativos. A licença anterior expira hoje.",
            "cta_label": "Ativar e baixar",
            "display_target": "m365-atualizacao.example/instalador",
            "explanation": "A oferta combina autoridade interna, prazo e instalação de arquivo. Pedir a senha atual em uma página aberta por e-mail e baixar um instalador não verificado cria risco de roubo de credenciais e software malicioso.",
            "red_flags": "Upgrade não solicitado; pedido de senha atual; instalação por link externo; prazo para pressionar",
            "decision_prompt": "Como confirmar a oferta sem expor a conta ou o computador?",
            "decision_a": "Baixar o instalador e só informar a senha se a página parecer profissional.",
            "decision_b": "Consultar a equipe de TI por um canal já conhecido antes de acessar ou instalar qualquer coisa.",
            "decision_c": "Pedir a um colega que teste o instalador primeiro.",
            "decision_correct": 2,
            "decision_explanation": "A equipe de TI pode confirmar licenças e orientar a instalação pelos canais oficiais. Não use o link recebido para verificar a própria mensagem.",
            "safe_action": "Confirme com a equipe de TI pelo canal interno conhecido. Não informe senha nem baixe o arquivo da mensagem.",
        },
    ]
    for case in cases:
        database.execute(
            """
            INSERT OR IGNORE INTO scenarios
                (case_key, module_id, title, kind, sender, subject, message,
                 correct_classification, explanation, red_flags, claimed_brand,
                 difficulty, context, cta_label, display_target, decision_prompt,
                 decision_a, decision_b, decision_c, decision_correct,
                 decision_explanation, safe_action, decision_kind)
            VALUES (?, ?, ?, 'email', ?, ?, ?, 'phishing', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case["case_key"], module_id, case["title"], case["sender"],
                case["subject"], case["message"], case["explanation"],
                case["red_flags"], case["claimed_brand"], case["difficulty"],
                case["context"], case["cta_label"], case["display_target"],
                case["decision_prompt"], case["decision_a"], case["decision_b"],
                case["decision_c"], case["decision_correct"],
                case["decision_explanation"], case["safe_action"], case.get("decision_kind", "action"),
            ),
        )
    copy_revisions = [
        (
            "linkedin-convite",
            "Olá!\n\nAna Ribeiro enviou um convite para fazer parte da sua rede profissional. Vocês têm contatos em comum.\n\nPara visualizar o perfil completo e responder ao convite, confirme seu acesso no botão abaixo.\n\nEquipe de notificações",
            cases[0]["message"],
        ),
        (
            "amazon-pagamento",
            "Olá,\n\nNão conseguimos concluir a cobrança do pedido #BR-843126. Para evitar o cancelamento, revise a forma de pagamento nas próximas 24 horas.\n\nPor segurança, não envie dados do cartão em resposta a este e-mail. Use o botão abaixo para atualizar as informações do pedido.\n\nAtendimento de pedidos",
            cases[1]["message"],
        ),
        (
            "uber-novo-acesso",
            "Olá,\n\nIdentificamos um acesso à sua conta às 11h47, em outro dispositivo. Se foi você, nenhuma ação é necessária.\n\nCaso não reconheça o acesso, proteja sua conta imediatamente pelo botão abaixo.\n\nEquipe de segurança",
            cases[2]["message"],
        ),
        (
            "office-download",
            "Olá,\n\nA equipe de tecnologia liberou sua licença premium para os aplicativos de escritório e armazenamento em nuvem.\n\nPara concluir a ativação, entre com sua conta corporativa e senha atual. Depois, baixe o instalador pelo botão abaixo. O acesso antigo será desativado ao fim do dia.\n\nCentral de licenças",
            cases[3]["message"],
        ),
    ]
    for case_key, previous, updated in copy_revisions:
        database.execute(
            "UPDATE scenarios SET message = ? WHERE case_key = ? AND message = ?",
            (updated, case_key, previous),
        )
    revise_seed_case(database, cases[0], {
        "decision_prompt": "Você quer conferir o convite. Qual é o próximo passo mais seguro?",
        "decision_a": "Abrir o botão da mensagem e digitar a senha para confirmar.",
        "decision_b": "Abrir o aplicativo oficial por conta própria e conferir os convites por lá.",
        "decision_c": "Responder à mensagem pedindo que Ana envie outro link.",
        "decision_explanation": "Acesse o aplicativo diretamente. Assim você consulta o convite sem depender do endereço enviado na mensagem.",
        "decision_kind": "action",
    })
    revise_seed_case(database, cases[1], {
        "context": "Você fez compras recentemente, então um aviso de pagamento pode parecer plausível. A mensagem não identifica claramente o produto.",
        "red_flags": "Cobrança com prazo curto; pedido sem descrição do produto; destino do botão fora do serviço mencionado",
        "decision_prompt": "Antes de atualizar qualquer pagamento, o que você faria?",
        "decision_a": "Usar o botão, já que o e-mail diz para não responder com dados do cartão.",
        "decision_b": "Informar apenas os quatro últimos dígitos do cartão para testar a mensagem.",
        "decision_c": "Abrir o aplicativo ou site oficial por um caminho conhecido e consultar meus pedidos.",
        "decision_explanation": "Consulte seus pedidos por um caminho que você já conhece. Uma mensagem pode parecer cuidadosa e ainda levar a uma página falsa.",
        "decision_kind": "action",
    })
    database.execute(
        "UPDATE scenarios SET cta_label = 'Ver perfil' WHERE case_key = 'linkedin-convite' AND cta_label = 'Ver convite'"
    )
    database.commit()


def seed_extra_cases(database):
    """Add four more scenarios without replacing attempts or edited exercises."""
    module_id = database.execute(
        "SELECT id FROM modules WHERE slug = 'exercicios-phishing'"
    ).fetchone()[0]
    cases = [
        {
            "case_key": "google-acesso",
            "title": "Alerta de acesso à Conta Google",
            "difficulty": "basico",
            "claimed_brand": "Google",
            "context": "Você entrou na sua conta em um Mac mais cedo. Agora chega um aviso sobre esse acesso. Observe o remetente, o pedido e o destino exibido.",
            "sender": "Google <no-reply@accounts.google.com>",
            "subject": "Novo acesso em um Mac",
            "message": "Detectamos um novo acesso à sua Conta Google em um Mac. Se foi você, nenhuma ação é necessária. Caso não reconheça a atividade, revise a segurança da conta.",
            "classification": "safe",
            "explanation": "Neste cenário, o remetente e o destino exibido pertencem ao domínio do serviço. O aviso não pede senha, código ou pagamento. Ainda assim, abrir a Conta Google por conta própria é a forma mais prudente de conferir a atividade.",
            "red_flags": "Remetente e destino coerentes; não solicita senha ou pagamento; atividade também pode ser consultada pela conta",
            "cta_label": "Ver atividade",
            "display_target": "myaccount.google.com/notifications",
            "decision_prompt": "Você quer conferir o novo acesso. O que faz?",
            "decision_a": "Abro a Conta Google por um endereço já conhecido e consulto a atividade de segurança.",
            "decision_b": "Respondo ao e-mail com meu código de verificação.",
            "decision_c": "Ignoro qualquer alerta de acesso, mesmo sem reconhecer o dispositivo.",
            "decision_correct": 1,
            "decision_explanation": "Mesmo quando um aviso parece legítimo, acessar a conta diretamente evita depender do botão da mensagem.",
            "safe_action": "Abra sua Conta Google pelo aplicativo ou por um endereço salvo e revise a atividade recente.",
            "sort_order": 20,
        },
        {
            "case_key": "netflix-pagamento",
            "title": "Cobrança recusada da Netflix",
            "difficulty": "intermediario",
            "claimed_brand": "Netflix",
            "context": "Você já viu no aplicativo que a cobrança deste mês falhou. O e-mail apenas avisa sobre uma nova tentativa; avalie se há um pedido de dados ou um desvio de endereço.",
            "sender": "Netflix <no-reply@netflix.com>",
            "subject": "Não foi possível processar seu pagamento",
            "message": "Olá,\n\nNão conseguimos processar a mensalidade deste mês. Faremos outra tentativa com a forma de pagamento já cadastrada.\n\nVocê pode acompanhar a situação da assinatura na sua conta. Não envie dados do cartão por resposta a este e-mail.",
            "classification": "safe",
            "explanation": "Neste exercício, a falha já foi vista no aplicativo, o endereço exibido pertence ao serviço e o aviso não solicita senha, código nem dados do cartão. Isso sustenta a classificação de mensagem legítima no cenário; na vida real, confirme pela conta aberta por você.",
            "red_flags": "Cobrança previamente vista no aplicativo; destino coerente com o serviço; nenhum dado sensível solicitado",
            "cta_label": "Ver assinatura",
            "display_target": "www.netflix.com/account",
            "decision_prompt": "Como você acompanha a cobrança sem depender do e-mail?",
            "decision_a": "Respondo com os dados do cartão para adiantar a cobrança.",
            "decision_b": "Abro a Netflix por conta própria e consulto a assinatura.",
            "decision_c": "Ignoro a cobrança porque mensagens legítimas nunca chegam por e-mail.",
            "decision_correct": 2,
            "decision_explanation": "Mesmo uma mensagem legítima pode ser conferida sem clicar: consulte a assinatura no serviço aberto por você.",
            "safe_action": "Entre na Netflix por um caminho conhecido e confira a seção de pagamento da conta.",
            "sort_order": 40,
        },
        {
            "case_key": "microsoft-acesso",
            "title": "Entrada incomum na conta Microsoft",
            "difficulty": "avancado",
            "claimed_brand": "Microsoft",
            "context": "Um alerta apresenta local, IP e dispositivo específicos. Nesta visualização, não é possível inspecionar o destino do botão. Há motivos para verificar, mas ainda falta prova para cravar golpe.",
            "sender": "Equipe da conta Microsoft <no-reply@microsoft.com>",
            "subject": "Atividade de entrada incomum",
            "message": "Se essa atividade não foi sua, informe o acesso pelo botão abaixo. Caso contrário, você poderá reconhecer acessos semelhantes no futuro.",
            "classification": "suspicious",
            "explanation": "O aviso pode corresponder a um acesso real, mas detalhes técnicos e remetente exibido não autenticam o e-mail. Como o destino do botão não está disponível nesta visualização, não há evidência para classificá-lo como golpe confirmado nem como seguro.",
            "red_flags": "Destino do botão indisponível; remetente exibido não comprova origem; acesso inesperado precisa de verificação independente",
            "cta_label": "Informar atividade",
            "display_target": None,
            "decision_prompt": "Por que a classificação ainda é inconclusiva?",
            "decision_a": "Porque uma mensagem com endereço IP é sempre falsa.",
            "decision_b": "Porque o remetente exibido garante que a conta foi invadida.",
            "decision_c": "Porque não vemos o destino do botão, e os detalhes técnicos não provam a origem.",
            "decision_correct": 3,
            "decision_explanation": "Informações específicas podem aparecer tanto em avisos reais quanto em golpes. Sem conferir o destino e a atividade na conta, a conclusão fica em aberto.",
            "decision_kind": "evidence",
            "safe_action": "Acesse a área de segurança da conta Microsoft por um caminho conhecido e revise as sessões.",
            "sort_order": 60,
        },
        {
            "case_key": "rh-memorando",
            "title": "Memorando de férias e salários",
            "difficulty": "avancado",
            "claimed_brand": "Equipe de RH",
            "context": "Uma colega do RH compartilha um memorando sobre férias e reajustes. Você não esperava o arquivo e não sabe se a equipe fez o envio.",
            "sender": "Mariana Lopes <mariana.lopes@empresa.example>",
            "subject": "Memorando atualizado sobre férias e remuneração",
            "message": "Olá, equipe,\n\nRevisem o memorando em anexo sobre as aprovações de férias e os próximos reajustes. Os nomes destacados em amarelo precisam confirmar os dados até o fim do mês.\n\nDepois de abrir o arquivo, respondam a este e-mail para confirmar que as informações estão corretas.\n\nMariana Lopes\nRecursos Humanos",
            "classification": "suspicious",
            "explanation": "O remetente parece interno, mas um arquivo HTML inesperado pode abrir uma página de captura de dados. Sem confirmação por outro canal, não dá para tratar a mensagem como segura.",
            "red_flags": "Anexo HTML inesperado; assunto sensível que desperta curiosidade; pedido de confirmação após abrir o arquivo",
            "cta_label": "memorando-ferias-salarios.html",
            "display_target": None,
            "decision_prompt": "Qual detalhe pede uma verificação antes de abrir?",
            "decision_a": "A assinatura da colega, que prova a origem.",
            "decision_b": "O anexo HTML inesperado sobre um tema sensível.",
            "decision_c": "O prazo até o fim do mês, que torna o arquivo seguro.",
            "decision_correct": 2,
            "decision_explanation": "Um anexo HTML pode abrir uma página ou executar conteúdo inesperado. A assinatura e o tema não substituem a confirmação pelo canal interno conhecido.",
            "decision_kind": "evidence",
            "safe_action": "Procure o RH pelo canal interno conhecido e reporte a mensagem se a equipe não confirmar o envio.",
            "sort_order": 70,
        },
    ]
    for case in cases:
        database.execute(
            """
            INSERT OR IGNORE INTO scenarios
                (case_key, module_id, title, kind, sender, subject, message,
                 correct_classification, explanation, red_flags, claimed_brand,
                 difficulty, context, cta_label, display_target, decision_prompt,
                 decision_a, decision_b, decision_c, decision_correct,
                 decision_explanation, safe_action, sort_order, decision_kind)
            VALUES (?, ?, ?, 'email', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case["case_key"], module_id, case["title"], case["sender"],
                case["subject"], case["message"], case["classification"],
                case["explanation"], case["red_flags"], case["claimed_brand"],
                case["difficulty"], case["context"], case["cta_label"],
                case["display_target"], case["decision_prompt"], case["decision_a"],
                case["decision_b"], case["decision_c"], case["decision_correct"],
                case["decision_explanation"], case["safe_action"], case["sort_order"], case.get("decision_kind", "action"),
            ),
        )
    revise_seed_case(database, cases[1], {
        "context": "Um e-mail diz que sua mensalidade não foi cobrada e solicita validade e código de segurança do cartão. O visual parece familiar.",
        "message": "Olá,\n\nTentamos cobrar o cartão cadastrado, mas a autorização foi recusada. Faremos uma nova tentativa em 24 a 48 horas.\n\nAtualize a validade e o código de segurança do cartão para continuar usando sua conta.",
        "classification": "phishing",
        "explanation": "O texto e o remetente exibido parecem plausíveis, mas o botão leva a um domínio que apenas contém o nome Netflix. A mensagem ainda pede dados sensíveis do cartão.",
        "red_flags": "Destino do botão fora do serviço; pedido de código de segurança do cartão; ameaça de interrupção da conta",
        "cta_label": "Atualizar dados",
        "display_target": "conta-netflix-pagamentos.example/cartao",
        "decision_prompt": "Como você confirma se existe um problema na cobrança?",
        "decision_a": "Digito a validade e o código de segurança na página do botão.",
        "decision_b": "Abro o aplicativo ou site oficial da Netflix por conta própria e verifico a cobrança.",
        "decision_c": "Respondo ao e-mail com uma foto do cartão.",
        "decision_explanation": "A cobrança deve ser verificada pelo serviço oficial, sem fornecer dados pelo caminho indicado no e-mail.",
    })
    revise_seed_case(database, cases[2], {
        "context": "Um alerta apresenta local, IP e dispositivo específicos. A precisão dos detalhes pode dar credibilidade à mensagem, mas o destino do botão ainda precisa ser conferido.",
        "classification": "phishing",
        "explanation": "Os dados técnicos e o remetente exibido não comprovam autenticidade. O botão de relato aponta para um domínio alheio à Microsoft, onde a conta poderia ser capturada.",
        "red_flags": "Botão com destino fora do serviço; endereço de remetente pode ser falsificado; detalhes técnicos usados para criar confiança",
        "display_target": "microsoft-seguranca.example/relatar",
        "decision_prompt": "O alerta pode indicar um acesso real. Qual é o caminho seguro?",
        "decision_a": "Uso o botão para informar a atividade antes que a conta seja bloqueada.",
        "decision_b": "Encaminho o e-mail a colegas para ver se receberam o mesmo aviso.",
        "decision_c": "Entro na conta Microsoft pelo aplicativo ou site oficial e reviso os acessos recentes.",
        "decision_explanation": "Confirme acessos pela área de segurança da conta aberta independentemente do e-mail.",
        "decision_kind": "action",
    })
    revise_seed_case(database, cases[3], {
        "decision_prompt": "Você não esperava esse memorando. O que faz antes de abrir o anexo?",
        "decision_a": "Abro o arquivo para descobrir se meu nome está destacado.",
        "decision_b": "Confirmo com o RH por um contato interno já conhecido e só então verifico o documento.",
        "decision_c": "Encaminho o arquivo aos colegas para saber se abre normalmente.",
        "decision_explanation": "Confirme a origem do documento por um canal independente antes de abrir anexos inesperados.",
        "decision_kind": "action",
    })
    database.commit()


def organize_learning_content(database):
    """Expose a short guide and one exercise library; retain historical rows."""
    guide = database.execute(
        "SELECT id FROM modules WHERE slug = 'cartilha-phishing'"
    ).fetchone()
    if guide is None:
        database.execute(
            """UPDATE modules SET published = 0
               WHERE slug IS NULL AND title IN
                 ('Fundamentos do phishing', 'Links, remetentes e anexos', 'Como agir com segurança')"""
        )
        database.execute(
            """INSERT INTO modules (slug, title, description, content, published, sort_order)
               VALUES (?, ?, ?, ?, 1, 0)""",
            (
                "cartilha-phishing",
                "O que é phishing",
                "Uma cartilha curta para reconhecer tentativas de engano antes de clicar.",
                "Phishing é uma tentativa de convencer você a revelar informações ou executar uma ação insegura. Pode chegar por e-mail, SMS, aplicativo de mensagens ou rede social. A aparência profissional e o nome de uma marca conhecida não provam que a mensagem é verdadeira.\n\nAntes de agir, observe três pontos: quem parece ter enviado, o que a mensagem pede e para onde ela tenta levar você. Pedidos de senha, código de verificação, dados do cartão, instalação de arquivo ou pagamento urgente merecem uma pausa.\n\nO nome exibido no remetente pode ser falsificado. Um domínio parecido com o de uma empresa também pode pertencer a outra pessoa. Se houver um botão, inspecione o destino; se houver anexo inesperado, confirme a origem antes de abrir.\n\nPara verificar, entre no aplicativo oficial por conta própria ou use um contato que você já conhecia antes da mensagem. Não use o próprio link recebido para provar que ele é confiável.\n\nSe você já informou uma senha, troque-a pelo serviço oficial e encerre sessões abertas. Se forneceu dados bancários, realizou um pagamento ou instalou um arquivo, procure imediatamente o suporte responsável. Reportar cedo ajuda a limitar o problema.",
            ),
        )
    exercise = database.execute(
        "SELECT id FROM modules WHERE slug = 'exercicios-phishing'"
    ).fetchone()
    if exercise:
        database.execute(
            """UPDATE modules SET
                   title = CASE WHEN title = 'Caixa de entrada: quatro decisões'
                                THEN 'Exercícios de phishing' ELSE title END
               WHERE id = ?""",
            (exercise["id"],),
        )
        # Refresh only stock copy, leaving administrator edits untouched.
        database.execute(
            """UPDATE modules SET description = ? WHERE id = ? AND description IN (?, ?)""",
            (
                EXERCISE_DESCRIPTION,
                exercise["id"],
                "Convites, compras, acessos e downloads: pratique antes de confiar.",
                "Oito mensagens para analisar: compras, contas, trabalho e redes sociais.",
            ),
        )
        database.execute(
            """UPDATE modules SET content = ? WHERE id = ? AND content IN (?, ?, ?)""",
            (
                EXERCISE_CONTENT,
                exercise["id"],
                "Nesta trilha, você vai analisar quatro mensagens inspiradas em situações comuns do cotidiano digital. Leia o contexto, observe o remetente e inspecione o destino do botão antes de responder. Nenhum botão da mensagem funciona de verdade. Sua tarefa é classificar o risco e escolher a ação mais segura. Errar faz parte do treino: o feedback mostra onde estavam as pistas.",
                "Leia cada mensagem como se ela tivesse acabado de chegar. Observe quem enviou, o que pede e para onde a ação levaria. Depois, classifique o risco e escolha uma resposta segura. Há mensagens fraudulentas, uma mensagem legítima e uma situação que pede verificação. Os botões e anexos são ilustrativos; nenhuma ação sai do Lock.",
                "Leia cada mensagem como se ela tivesse acabado de chegar. Observe quem enviou, o que pede e para onde a ação levaria. Depois, classifique o risco e identifique a pista decisiva ou a atitude segura. Há mensagens fraudulentas, legítimas e situações que pedem verificação. Os botões e anexos são ilustrativos; nenhuma ação sai do Lock.",
            ),
        )
        if guide is None:
            database.execute(
                "UPDATE modules SET published = 1, sort_order = 1 WHERE id = ?",
                (exercise["id"],),
            )
    case_updates = (
        ("linkedin-convite", "Um convite fora da rede", "Convite do LinkedIn", 10),
        ("amazon-pagamento", "O pagamento de uma compra", "Cobrança da Amazon", 30),
        ("uber-novo-acesso", "Acesso desconhecido à conta", "Alerta de acesso da Uber", 50),
        ("office-download", "Uma licença de software inesperada", "Oferta de Office", 80),
    )
    for case_key, old_title, new_title, position in case_updates:
        database.execute(
            "UPDATE scenarios SET title = ? WHERE case_key = ? AND title = ?",
            (new_title, case_key, old_title),
        )
        database.execute(
            "UPDATE scenarios SET sort_order = ? WHERE case_key = ? AND sort_order = 1000",
            (position, case_key),
        )
    database.commit()


@click.command("init-db")
@with_appcontext
def init_db_command():
    init_db()
    seed_db()
    click.echo("Banco de dados do Lock inicializado.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

# Lock

Plataforma web, em português brasileiro, com conteúdo de conscientização e
exercícios práticos sobre phishing.

O Lock transforma orientações de segurança em prática: o participante lê uma
cartilha curta, analisa mensagens fictícias, classifica o risco, identifica a
pista decisiva ou escolhe como agir e recebe uma explicação imediata. Suas
respostas e seu progresso ficam salvos para revisão.

> [!NOTE]
> Este é um protótipo de ensino. Ele não envia campanhas, não coleta credenciais
> de terceiros e não se conecta a empresas ou bancos. As marcas nos e-mails
> simulados aparecem apenas no contexto didático, sem afiliação com elas.

## O que o Lock oferece

- **O que é phishing:** cartilha sobre sinais de risco e verificação segura.
- **Exercícios de phishing:** mensagens de diferentes contextos e níveis, com
  explicação após cada resposta e opção de refazer.
- **Meu progresso:** conclusão da cartilha, percentual dos exercícios e
  respostas anteriores.
- **Administração:** gestão de conteúdo, indicadores agregados e auditoria.

O acervo inicial aborda LinkedIn, Google, Amazon, Netflix, Uber, Microsoft,
mensagens de RH e Office. Combina golpes, mensagens legítimas e casos que
precisam de confirmação. Novos exercícios podem ser cadastrados na área de
administração.
Os retratos representam personagens fictícios; a foto de produto é ilustrativa.
Todos os botões e anexos dos exemplos são **inertes**.

## Como executar

Pré-requisitos: **Python 3.11 ou superior** e um navegador atual. No terminal,
dentro da pasta do projeto:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Abra <http://127.0.0.1:5000>. O banco de dados é criado em
`instance/lock.sqlite` na primeira execução. Para encerrar o servidor, use
`Ctrl+C`. Nas execuções seguintes, o progresso salvo é mantido.

### Acesso para demonstração

| Perfil        | E-mail             | Senha       |
|---------------|--------------------|-------------|
| Participante  | `aluno@lock.local` | `Lock@123`  |
| Administrador | `admin@lock.local` | `Admin@123` |

> [!WARNING]
> Essas contas são exclusivamente locais. Não exponha este servidor à internet
> nem use as senhas demonstrativas em produção. Fora de uma demonstração
> descartável, defina um `LOCK_SECRET_KEY` longo, aleatório e persistente; em
> produção também são necessários HTTPS, servidor apropriado, gestão de contas,
> backup e revisão de segurança.

### Percurso rápido para testar

1. Entre como participante e abra a cartilha **O que é phishing**.
2. Abra **Exercícios de phishing** e selecione uma mensagem.
3. Inspecione o destino ilustrativo do botão, quando houver; classifique a
   mensagem e responda à pergunta sobre a pista ou a atitude. O feedback
   aparece sem recarregar a página.
4. Atualize a página para confirmar que a resposta foi salva. Use **Refazer**
   para tentar novamente e consulte **Meu progresso**.
5. Saia, entre como administrador e explore conteúdos, indicadores e auditoria.

## Testes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

A suíte cobre autenticação, autorização, proteção CSRF, conteúdos, respostas,
persistência, progresso e administração. Os 18 testes passaram na validação
local. Isso não substitui um teste de intrusão ou uma avaliação com usuários
reais.

## Documentação

As etapas abaixo descrevem o projeto sem identificar aluno, professor, cidade
ou vínculo profissional:

- [Etapa 01 — Pesquisa e escopo](documentacao/etapa-01-pesquisa.md)
- [Etapa 02 — Requisitos e modelagem](documentacao/etapa-02-requisitos-e-diagramas.md)
- [Etapa 03 — Desenvolvimento e testes](documentacao/etapa-03-desenvolvimento.md)
- [Etapa 04 — Relato de experiência](documentacao/etapa-04-relato-experiencia.md)

Os [diagramas](documentacao/diagramas/) estão disponíveis como fontes PlantUML
e imagens.

> [!IMPORTANT]
> O PDF e o DOCX da entrega acadêmica contêm dados de identificação. Eles ficam
> em `documentacao/entrega/`, pasta excluída pelo `.gitignore`, e devem ser
> enviados apenas pelo canal de entrega da instituição. Um envio manual de
> arquivos ao GitHub não aplica as regras do `.gitignore`.

### Regenerar o relatório

Após editar uma etapa, instale as dependências documentais e informe os dados
da capa localmente. Substitua os exemplos entre aspas pelos dados corretos:

```bash
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python tools/gerar_relatorio.py \
  --aluno "NOME DO ALUNO" \
  --professor "NOME DO PROFESSOR" \
  --cidade "CIDADE - UF" \
  --instituicao "INSTITUIÇÃO"
```

O gerador deixa apenas o PDF e o DOCX em `documentacao/entrega/` quando ambos
são produzidos. O PDF requer Google Chrome ou Chromium; o DOCX requer
LibreOffice. `--ano` e `--curso` também podem ser informados, se necessário.
Se existir um complemento em `apoio-privado/contexto-relatorio.md`, ele será
incluído apenas no relatório gerado localmente.

## Estrutura essencial

```text
lock/          aplicação Flask, páginas, estilos e esquema do banco
tests/         testes automatizados
documentacao/  etapas e diagramas; entrega acadêmica local ignorada
tools/         gerador do relatório
run.py         inicialização do servidor local
```

`instance/` é criada automaticamente para o banco local. Ela e
`apoio-privado/` não devem ser compartilhadas. O vídeo de usabilidade é uma
entrega separada, conforme as orientações do AVA.

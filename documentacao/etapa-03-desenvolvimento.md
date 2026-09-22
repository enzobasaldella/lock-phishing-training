# Etapa 03 — Desenvolvimento e validação do software

Implementação local do protótipo, seus controles de segurança e sua validação.

> [!WARNING]
> O Lock não está preparado para implantação pública. As mensagens e os leitores
> de e-mail são ilustrativos; não há envio de campanhas nem links ativos.

## Resumo da etapa

Foi implementada uma aplicação web responsiva em Python/Flask, com persistência
SQLite, dois perfis de acesso, cartilha, oito exercícios, feedback assíncrono,
progresso, administração e auditoria. A validação inclui dezoito testes
automatizados e inspeção visual em larguras de computador e celular.

## 1. Introdução

Após a pesquisa e a modelagem, foi desenvolvida uma versão funcional do Lock.
O software transforma os requisitos definidos na Etapa 02 em uma aplicação web
responsiva que pode ser executada localmente. A experiência principal apresenta
uma cartilha e oito exercícios de análise de mensagens; respostas e progresso
são registrados. O sistema também mantém recursos de quiz e administração.

O objetivo da implementação é demonstrar, de forma integrada, conhecimentos de
programação, banco de dados, engenharia de software e segurança da informação.
O protótipo não executa ataques nem envia mensagens externas. Todo treinamento
acontece dentro do ambiente controlado do sistema.

## 2. Tecnologias utilizadas

| Tecnologia | Aplicação no projeto |
|---|---|
| Python 3 | Linguagem usada para regras, validações e acesso aos dados. |
| Flask | Framework web responsável por rotas, sessões, formulários e páginas. |
| SQLite | Banco de dados relacional armazenado em arquivo local. |
| HTML semântico | Estrutura das telas e dos formulários. |
| CSS responsivo | Identidade visual e adaptação para computador e celular. |
| JavaScript | Envio das respostas e exibição do feedback sem recarregar a página. |
| Jinja | Renderização segura dos dados nas páginas HTML. |
| unittest | Automação dos testes de fluxos e controles de segurança. |

Essas tecnologias foram escolhidas por serem suficientes para um protótipo
completo, possuírem ampla documentação e permitirem uma demonstração local sem
serviços externos.

## 3. Arquitetura da aplicação

O projeto foi dividido em componentes com responsabilidades específicas:

```text
lock/
├── __init__.py          criação da aplicação e configuração de controles básicos
├── auth.py              cadastro, login, logout e autorização
├── main.py              módulos, simulações, quizzes e progresso
├── admin.py             conteúdo, indicadores e auditoria
├── db.py                conexão, inicialização e dados demonstrativos
├── schema.sql           tabelas, restrições e relacionamentos
├── templates/           páginas HTML
└── static/              estilos, interações, ícone e imagens fictícias dos e-mails
```

As rotas foram separadas por área funcional. A camada de apresentação recebe
apenas os dados necessários, enquanto as operações de banco utilizam consultas
parametrizadas. O SQLite mantém usuários, módulos, cenários, perguntas,
alternativas, tentativas, progresso e logs administrativos.

## 4. Funcionalidades implementadas

### 4.1 Participante

- criação de conta com validação de nome, e-mail e senha;
- autenticação e encerramento seguro da sessão;
- cartilha **O que é phishing**, com marcação de leitura concluída;
- biblioteca **Exercícios de phishing**, organizada em três níveis;
- oito corpos de e-mail com composição visual própria, adaptados ao português
  brasileiro e ao contexto dos serviços representados;
- classificação dos cenários como seguro, suspeito ou phishing;
- identificação de uma pista decisiva ou escolha de uma atitude segura, conforme o exercício;
- inspeção de destino demonstrativo do botão, sem link ativo;
- correção imediata sem recarregamento, com explicação, indícios observados e orientação prática;
- persistência da última resposta da edição atual, histórico de versões anteriores e opção de refazer;
- pontuação binária por exercício (100 quando as duas decisões estão corretas,
  0 caso contrário), progresso e histórico de tentativas.

### 4.2 Administrador

- painel com quantidade de participantes, módulos e tentativas;
- indicador agregado de taxa de acerto;
- criação, edição, publicação e despublicação de módulos;
- criação, edição e remoção de cenários;
- criação, edição e remoção de questões e alternativas;
- consulta ao log de ações administrativas.

### 4.3 Conteúdo demonstrativo

O banco publica duas áreas: **O que é phishing** e **Exercícios de phishing**.
A biblioteca tem oito mensagens: LinkedIn, Google, Amazon, Netflix, Uber,
Microsoft, RH e Office. Os nomes e
elementos visuais das marcas servem apenas para contextualizar situações comuns
de engenharia social, sem afiliação com as empresas. Os corpos de e-mail foram
montados em HTML/CSS e incluem retratos de personagens fictícios e uma imagem
ilustrativa de produto. Os alertas do Google e da Microsoft aparecem em leitores
de e-mail ilustrativos, inspirados no Gmail e no Outlook. Não há páginas reais
das empresas. Os botões são elementos visuais inertes; os destinos suspeitos
usam domínios reservados, como `.example`
e `.test`. Os exercícios legítimos do Google e da Netflix exibem destinos
oficiais apenas como texto, nunca como links clicáveis.

Os níveis básico, intermediário e avançado graduam a sutileza dos sinais. Em
cada exercício, o participante lê o contexto, examina uma mensagem simulada,
pode inspecionar o destino do botão quando disponível, classifica a mensagem e
responde sobre a pista decisiva ou a atitude mais segura. O feedback mostra
separadamente a leitura do risco e a segunda resposta, apresenta as pistas e
recomenda uma atitude aplicável fora do treinamento. No computador, as respostas
ficam ao lado da mensagem; no celular, abrem em um painel próprio.

| Ordem | Exercício | Nível | Classificação esperada |
|---:|---|---|---|
| 1 | Convite do LinkedIn | Básico | Phishing |
| 2 | Alerta de acesso à Conta Google | Básico | Seguro |
| 3 | Cobrança da Amazon | Intermediário | Phishing |
| 4 | Cobrança recusada da Netflix | Intermediário | Seguro |
| 5 | Alerta de acesso da Uber | Intermediário | Phishing |
| 6 | Entrada incomum na conta Microsoft | Avançado | Suspeito |
| 7 | Memorando de férias e salários | Avançado | Suspeito |
| 8 | Oferta de Office | Avançado | Phishing |

O gabarito combina quatro mensagens de phishing, duas seguras e duas
inconclusivas. A pergunta complementar alterna entre quatro análises de pistas
e quatro escolhas de atitude, para evitar respostas mecânicas. O caso da
Microsoft não apresenta o destino do botão: o aluno deve reconhecer a falta de
evidência, sem concluir que todo alerta técnico é golpe.

## 5. Banco de dados

O modelo relacional foi implementado com as tabelas abaixo:

| Tabela | Finalidade |
|---|---|
| `users` | Armazena conta, hash da senha, perfil e situação do usuário. |
| `modules` | Armazena os conteúdos e seu estado de publicação. |
| `scenarios` | Armazena mensagens fictícias, resposta esperada e explicação. |
| `questions` e `alternatives` | Formam os quizzes de múltipla escolha. |
| `scenario_attempts` | Registra classificação, decisão prática e resultado de cada simulação. |
| `quiz_attempts` | Registra pontuação e total de questões de cada quiz. |
| `module_progress` | Consolida o percentual concluído pelo participante. |
| `audit_logs` | Registra alterações administrativas relevantes. |

Chaves estrangeiras preservam os relacionamentos, restrições `CHECK` limitam
valores válidos e índices apoiam as consultas mais frequentes. Na inicialização,
uma migração aditiva inclui campos de exercícios em bancos anteriores e a
semeadura evita duplicar os oito cenários. A edição do conteúdo é versionada:
tentativas anteriores continuam registradas, mas não exibem feedback recalculado
com o novo gabarito; o participante pode refazer o exercício. Conteúdos
demonstrativos antigos ficam despublicados, sem apagar usuários ou tentativas.

## 6. Medidas de segurança aplicadas

| Controle | Implementação |
|---|---|
| Proteção de senhas | Armazenamento com hash e sal pelo Werkzeug; nenhuma senha é salva em texto puro. |
| Controle de acesso | Decoradores impedem participantes de acessar funções administrativas. |
| Proteção CSRF | Todos os formulários `POST` exigem um token associado à sessão. |
| Injeção SQL | Consultas recebem parâmetros separados dos comandos SQL. |
| XSS | O mecanismo de templates escapa automaticamente dados exibidos em HTML. |
| Sessão | Cookies usam `HttpOnly` e `SameSite=Lax`; o login renova a sessão e o logout limpa os dados de sessão. `Secure` pode ser habilitado com `LOCK_HTTPS=1` sob HTTPS. |
| Cabeçalhos HTTP | CSP, bloqueio de enquadramento, `nosniff`, política de referência e restrição de permissões. |
| Validação | Campos e valores permitidos são verificados também no servidor. |
| Minimização | O cadastro solicita somente nome, e-mail e senha. |
| Auditoria | Alterações administrativas ficam vinculadas a usuário, entidade e data. |
| Simulação segura | Nenhum cenário possui link ativo ou solicita credencial verdadeira. |

### 6.1 Análise qualitativa de riscos

A análise abaixo identifica pontos de falha relevantes para o protótipo e
relaciona cada risco a uma medida implementada ou a uma limitação assumida. Não
representa um teste de intrusão nem uma medição estatística de probabilidade.

| Risco analisado | Possível consequência | Tratamento no Lock / limite residual |
|---|---|---|
| Ação impulsiva diante de mensagem convincente | Exposição de senha, cartão ou instalação de arquivo fora da plataforma. | Cartilha e exercícios ensinam a verificar remetente, pedido e destino por canal independente; eficácia com usuários reais ainda não foi medida. |
| Acesso indevido às funções administrativas | Alteração ou remoção de conteúdo. | Verificação de autenticação e perfil em todas as rotas administrativas; uma implantação real também exigiria gestão robusta de contas. |
| Injeção de comandos SQL por formulários | Leitura ou alteração não autorizada do banco. | Consultas parametrizadas e validação de campos; não foi executada auditoria especializada. |
| Código malicioso em conteúdo exibido | Execução de scripts no navegador de participantes. | Escape automático do Jinja e política CSP; conteúdo administrativo deve continuar sendo revisado. |
| Envio de formulário forjado | Ações em nome de um usuário autenticado. | Token CSRF validado nos formulários `POST`. |
| Exposição de sessão ou dados em rede pública | Acesso não autorizado a contas e progresso. | Demonstração restrita a `127.0.0.1`; HTTPS, cookie `Secure` e segredo persistente são necessários antes de qualquer publicação. |
| Tentativas repetidas de adivinhar senha | Comprometimento de conta demonstrativa. | Hash de senha reduz o dano de vazamento do banco, mas não existe limitação de tentativas: o risco permanece para uso público. |

Assim, o projeto trata riscos nas camadas de **interface**, **aplicação** e
**banco de dados**, além de explicitar o limite da camada de **rede** no modo
local. Esses controles são parte da aprendizagem de desenvolvimento seguro,
mas não tornam o protótipo pronto para produção.

Em uma publicação real com domínio público, também seria necessário usar HTTPS,
um servidor WSGI de produção, segredo persistente protegido, cópias de segurança,
monitoramento, limitação de tentativas de login, política de privacidade,
recuperação de senha e revisão independente de segurança. O servidor embutido do
Flask e as credenciais de demonstração **não devem** ser usados em produção.

## 7. Testes e validação

Foram criados testes automatizados para verificar:

1. carregamento da página inicial e presença de cabeçalhos de segurança;
2. autenticação e realização correta de uma simulação;
3. execução e correção de um quiz;
4. bloqueio da administração para participante;
5. criação de módulo pelo administrador e registro em auditoria;
6. rejeição de requisição sem token CSRF;
7. carregamento das páginas de participante e de administração com os dados de demonstração;
8. criação idempotente dos oito exercícios, com três níveis e três classificações;
9. exigência das duas decisões nos casos novos e validação do destino inerte;
10. criação e edição de um cenário completo pelo administrador;
11. explicação da alternativa correta após uma decisão insegura;
12. conclusão do módulo após os oito exercícios;
13. renderização distinta dos e-mails e ausência de links ativos dentro deles;
14. salvamento da leitura e da resposta assíncrona após reiniciar a aplicação;
15. rejeição de resposta assíncrona incompleta sem gerar tentativa;
16. indicadores de progresso compatíveis com a política de segurança da página;
17. renderização dos clientes de e-mail ilustrativos sem links ativos;
18. preservação de tentativa anterior quando um exercício recebe novo gabarito.

Na validação local de 21 de setembro de 2026, os dezoito testes foram
concluídos com sucesso. As páginas principais também foram verificadas no
navegador em larguras de 1.280 e 390 pixels, sem rolagem horizontal. O envio
assíncrono e a permanência da última resposta após recarregar foram verificados
em um banco de teste. Essa verificação funcional não equivale a teste de
usabilidade com participantes reais, teste de intrusão ou garantia de ausência
de falhas.

## 8. Execução e demonstração

No terminal aberto na pasta do projeto, são utilizados os comandos:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Depois, a plataforma fica disponível em `http://127.0.0.1:5000`.
Na primeira execução, o arquivo SQLite e os dados demonstrativos são criados
automaticamente. Para manter as sessões válidas entre reinícios, configure
`LOCK_SECRET_KEY` com um valor estável em um ambiente que não seja apenas uma
demonstração descartável. Não inclua esse segredo nem o banco local no relatório.

Para facilitar a apresentação, existem duas contas demonstrativas:

| Perfil | E-mail | Senha |
|---|---|---|
| Participante | `aluno@lock.local` | `Lock@123` |
| Administrador | `admin@lock.local` | `Admin@123` |

Os testes podem ser repetidos com:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## 9. Limites e resultado da etapa

A Etapa 03 resultou em uma plataforma web funcional e coerente com os modelos
da Etapa 02. O participante consegue percorrer o ciclo de aprendizagem, prática,
feedback e acompanhamento. O administrador consegue manter o conteúdo e
consultar indicadores sem depender de serviços externos. A implementação também
materializa controles de segurança que podem ser explicados durante a
apresentação, atendendo ao tema central do Projeto Interdisciplinar IV. Permanecem
fora do escopo implantação pública, avaliação pedagógica com usuários reais,
análise formal de vulnerabilidades da aplicação e integração com infraestrutura
de uma organização.

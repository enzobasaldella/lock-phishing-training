# Etapa 01 — Pesquisa e definição do projeto

Protótipo de plataforma web para treinamento e conscientização contra phishing.

> [!NOTE]
> O Lock não utiliza dados nem sistemas internos de organizações. Os serviços
> conhecidos aparecem apenas em mensagens fictícias de treinamento, sem
> afiliação ou endosso das empresas citadas.

## Resumo da etapa

A pesquisa delimitou o público, o problema e o escopo do Lock. O projeto propõe
transformar orientações contra phishing em decisões praticadas no navegador,
com explicação imediata e sem envio de mensagens a terceiros.

## 1. Objetivo e método

Esta etapa atende à pesquisa do nicho, à definição do escopo do aplicativo e à
análise de soluções existentes solicitadas no manual do PI IV. Foi realizada uma
pesquisa documental qualitativa, sem entrevistas, questionários ou coleta de
dados de empresas. Foram consultados materiais de orientação do CERT.br e da
CISA e páginas públicas das plataformas Wizer e KnowBe4 [R1–R4]. Essas fontes
foram usadas para identificar necessidades e funções comuns, não para afirmar
participação de mercado ou eficácia quantitativa do protótipo.

## 2. Nicho de mercado e problema

O nicho escolhido é o de **treinamento e conscientização contra phishing**,
oferecido como serviço digital. Phishing utiliza mensagens ou páginas enganosas
para induzir uma pessoa a revelar informações, abrir arquivos ou executar uma
ação que normalmente não realizaria. O risco não se limita a mensagens com erros
evidentes: aparência profissional, nome de marca e dados aparentemente precisos
podem aumentar a credibilidade do golpe [R1, R2].

O público inicial são pessoas e pequenas equipes que dependem de e-mail e
serviços digitais, mas precisam de orientação objetiva, em português, para
verificar solicitações inesperadas. O problema educacional é a distância entre
*saber que golpes existem* e *reconhecer o que fazer ao receber uma mensagem*
sob pressão. A solução proposta permite ensaiar essa decisão sem enviar
campanhas externas nem expor dados reais.

### Público-alvo e necessidades

| Público | Necessidade atendida |
|---|---|
| Participante sem formação técnica | Ler exemplos próximos do cotidiano, decidir e compreender as pistas sem jargão. |
| Responsável pelo treinamento | Publicar conteúdo, acompanhar indicadores agregados e identificar temas que merecem reforço. |
| Pessoa que estuda individualmente | Praticar no navegador, revisar respostas e repetir exercícios no próprio ritmo. |

As personas a seguir são fictícias e servem à análise de requisitos:

- **Marina, 31 anos, assistente administrativa:** usa e-mail e serviços de
  compras diariamente. Precisa comparar remetente, pedido e destino de um botão
  antes de agir, com explicação curta após cada resposta.
- **Rafael, 38 anos, responsável por uma pequena equipe:** precisa disponibilizar
  conteúdos e observar resultados gerais, sem acessar desnecessariamente dados
  pessoais das respostas de cada participante.

## 3. Soluções existentes e oportunidade

| Referência | Característica observada na fonte pública | Decisão para o Lock |
|---|---|---|
| Wizer [R3] | Oferece treinamento de conscientização, vídeos e simulações de phishing. | Priorizar exercícios curtos, feedback e linguagem acessível; não copiar materiais ou interface. |
| KnowBe4 [R4] | Apresenta treinamento de conscientização e acompanhamento do risco humano. | Incluir visão administrativa agregada, em escala adequada ao protótipo. |
| CERT.br e CISA [R1, R2] | Orientam a observar sinais, confirmar por canais conhecidos e comunicar suspeitas. | Fundamentar a cartilha e as recomendações dadas após os exercícios. |

O Lock não pretende substituir uma plataforma corporativa de campanhas. Seu
diferencial no recorte acadêmico é a **prática integralmente dentro do sistema**:
mensagens fictícias em português, botões inertes, classificação do risco,
identificação de uma pista ou escolha de uma atitude, com explicação das duas
respostas. Como tudo acontece no Lock, a atividade não se confunde com uma
mensagem recebida fora do treinamento.

## 4. Escopo definido

### Objetivo geral

Desenvolver uma plataforma web responsiva que ajude participantes a reconhecer
mensagens de phishing e a escolher caminhos seguros de verificação.

### Funcionalidades da versão demonstrável

| Área | Entrega prevista |
|---|---|
| Acesso | Cadastro, login, logout e separação entre participante e administrador. |
| Aprendizagem | Cartilha **O que é phishing** e módulo **Exercícios de phishing**. |
| Prática | Oito mensagens de e-mail simuladas, em três níveis, com classificação e análise da pista decisiva ou da atitude segura. |
| Feedback | Explicação dos sinais, atitude recomendada e opção de refazer. |
| Acompanhamento | Última resposta, histórico de tentativas e percentual de conclusão. |
| Administração | Gestão de módulos, cenários e questões opcionais; indicadores agregados e auditoria. |

O sistema também aceita cenários de SMS e mensageria cadastrados pelo
administrador, mas **a coleção principal publicada contém oito e-mails**. O
suporte a quizzes existe para módulos adicionais; não é uma etapa obrigatória
do percurso principal da demonstração.

### Fora do escopo

Não há disparo de e-mail ou SMS, campanhas externas, captura de credenciais,
integração com serviços reais, páginas de login de terceiros, pagamento ou
aplicativo nativo. Os elementos visuais de marcas aparecem apenas nas mensagens
demonstrativas, identificadas como simulações; nenhum botão do exercício abre
um destino externo. O protótipo não foi submetido
a um teste formal de eficácia pedagógica nem a uma auditoria profissional de
segurança.

## 5. Viabilidade e critérios de sucesso

A escolha de uma aplicação web evita instalação no celular e permite apresentar
o mesmo fluxo em computador e navegador móvel. Python, Flask e SQLite permitem
implementar autenticação, persistência e administração sem infraestrutura
externa. A versão é considerada demonstrável quando o participante consegue
entrar, ler a cartilha, responder os oito exercícios, receber feedback, sair e
voltar para revisar o progresso; o administrador deve conseguir manter conteúdo
e consultar indicadores. A Etapa 03 documenta como esses critérios foram
verificados.

O tratamento de dados foi limitado a informações necessárias ao cadastro e ao
progresso. Para uso público real ainda seriam necessários infraestrutura de
produção, política de privacidade, gestão de contas e revisão de segurança.

## 6. Resultado da Etapa 01

O nicho e o escopo foram definidos de forma compatível com o exemplo de
**simulação de engenharia social e conscientização** citado no manual do PI IV.
A pesquisa orientou os requisitos da Etapa 02 e a implementação da Etapa 03,
mantendo uma separação clara entre um protótipo acadêmico e uma solução pronta
para uso corporativo.

## Referências

- **[R1]** CERT.br. *Golpes: não se deixe enganar — Cartilha de Segurança para
  Internet*. Disponível em:
  <https://cartilha.cert.br/fasciculos/golpes/fasciculo-golpes.pdf>.
  Acesso em: 21 set. 2026.
- **[R2]** CISA. *Secure Our World: phishing tip sheet*. Disponível em:
  <https://www.cisa.gov/sites/default/files/2024-09/Secure-Our-World-Phishing-Tip-Sheet.pdf>.
  Acesso em: 21 set. 2026.
- **[R3]** WIZER. *Security awareness training and phishing simulation*.
  Disponível em: <https://www.wizer-training.com/>.
  Acesso em: 21 set. 2026.
- **[R4]** KNOWBE4. *Security awareness training*. Disponível em:
  <https://www.knowbe4.com/products/security-awareness-training>.
  Acesso em: 21 set. 2026.

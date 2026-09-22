# Etapa 04 — Relato de experiência

Relato da construção de um protótipo de treinamento contra phishing.

> [!NOTE]
> O relato descreve o desenvolvimento do protótipo. Não houve avaliação com
> participantes reais nem implantação em uma organização.

## Resumo da etapa

Esta etapa reúne as decisões de desenvolvimento, as dificuldades encontradas,
os aprendizados relacionados ao curso e os limites da versão demonstrável.

## 1. Percurso de elaboração

A elaboração do Lock começou pela delimitação de um problema de Segurança da
Informação que pudesse ser demonstrado sem expor pessoas ou sistemas reais.
O tema escolhido foi a conscientização contra phishing, porque reconhecer uma
mensagem enganosa exige mais do que memorizar sinais isolados: é preciso
avaliar o contexto e decidir como conferir a informação. A pesquisa inicial
ajudou a transformar esse problema em um escopo viável para o Projeto
Interdisciplinar IV: uma plataforma web com cartilha, exercícios simulados,
feedback e acompanhamento do progresso.

Na etapa de modelagem, os requisitos e os diagramas organizaram o percurso do
participante e as responsabilidades do sistema. A distinção entre participante
e administrador, o registro das tentativas e a relação entre módulos e
cenários deixaram de ser apenas ideias de interface e passaram a orientar as
rotas e as tabelas do banco de dados. Esse encadeamento entre pesquisa,
modelagem e implementação foi importante para manter o protótipo coerente com
o objetivo educacional definido no início.

## 2. Decisões e dificuldades encontradas

Uma das principais decisões foi realizar toda a prática dentro do próprio
Lock. Os e-mails dos exercícios são representações didáticas; seus botões e
anexos não executam ações e não há envio de campanhas a terceiros. Essa opção
permitiu demonstrar tentativas de engenharia social sem reproduzir um ataque
real. Também tornou necessário deixar claro, em cada exercício, quais
elementos eram apenas ilustrativos e quais informações o participante deveria
observar.

A revisão do acervo revelou um problema pedagógico: se quase todas as
mensagens são golpes e a resposta prática é sempre abrir o aplicativo
oficial, o aluno pode acertar por repetição, sem analisar o caso. O conjunto
foi reorganizado para conter quatro exemplos de phishing, dois avisos
legítimos no contexto apresentado e duas situações inconclusivas. Em metade
dos exercícios, a segunda pergunta solicita a pista decisiva; nos demais,
solicita a atitude mais segura. O caso da conta Microsoft, por exemplo, não
exibe o destino do botão. Por isso, a conclusão adequada é reconhecer a
necessidade de verificação, e não afirmar que o aviso é legítimo ou fraudulento
sem evidência suficiente.

Outra dificuldade foi conciliar uma resposta imediata na interface com o
registro confiável das tentativas. O envio assíncrono evita que a página
recarregue após a resposta, enquanto a validação e o armazenamento continuam
no servidor. Quando o conteúdo de um exercício muda, a versão anterior da
tentativa permanece no histórico, mas seu feedback não é reinterpretado com o
novo gabarito. Essa solução preserva o percurso realizado e permite responder
novamente à edição atual.

## 3. Aprendizados relacionados ao curso

O projeto aproximou conceitos de programação, banco de dados, engenharia de
software e segurança da informação. A modelagem de requisitos e os diagramas
ajudaram a separar funcionalidades essenciais de recursos adicionais. O modelo
relacional permitiu associar contas, módulos, cenários, tentativas e progresso,
mantendo a identificação de cada registro e evitando perda de dados durante
as revisões do conteúdo.

Na implementação, os conceitos de desenvolvimento seguro apareceram em
medidas concretas: senhas armazenadas por hash, verificação de perfil para a
área administrativa, consultas parametrizadas, proteção contra requisições
forjadas e validação dos dados recebidos pelo servidor. Essas medidas não
tornam o protótipo invulnerável, mas mostram que a segurança precisa fazer
parte das decisões de projeto, e não ser acrescentada somente depois da
interface pronta.

O conteúdo dos exercícios também reforçou um aprendizado sobre engenharia
social. Uma foto, um nome conhecido, um número de pedido ou detalhes técnicos
podem tornar uma mensagem convincente sem comprovar sua origem. Ao mesmo
tempo, tratar toda mensagem como golpe impede uma avaliação cuidadosa. A
classificação entre segura, suspeita e phishing foi usada para exercitar esse
juízo, sempre acompanhada de uma forma independente de conferir a informação.

## 4. Avaliação do resultado e limites

O resultado é um protótipo web executável, com oito exercícios, cartilha,
controle de acesso, persistência e administração de conteúdo. Os testes
automatizados verificam fluxos de uso e controles básicos, inclusive a
preservação do histórico após revisões dos exercícios. O projeto atende ao
recorte de simulação de engenharia social e conscientização indicado entre os
exemplos do manual do PI IV.

A avaliação também mostrou limites importantes. Não foi conduzido um estudo
com participantes reais para medir aprendizagem ou usabilidade, nem uma
auditoria de segurança ou implantação pública. Para uso fora da demonstração
local, seriam necessários testes com usuários, revisão técnica independente,
infraestrutura com HTTPS, política de contas e análise das exigências legais
e organizacionais aplicáveis. Assim, o Lock deve ser apresentado como prova de
conceito acadêmica, não como uma plataforma corporativa já validada.

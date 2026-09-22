"""Monta o relatório único do PI IV a partir das quatro etapas documentadas.

Instalação: .venv/bin/python -m pip install -r requirements-docs.txt
Uso: .venv/bin/python tools/gerar_relatorio.py --aluno NOME --professor NOME
     --cidade LOCAL --instituicao NOME
"""

from __future__ import annotations

import argparse
import html
import io
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

try:
    import markdown
except ImportError as error:
    raise SystemExit(
        "Instale a dependência documental: .venv/bin/python -m pip install -r requirements-docs.txt"
    ) from error


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "documentacao"
OUTPUT = DOCS / "entrega"
PRIVATE_CONTEXT = ROOT / "apoio-privado" / "contexto-relatorio.md"
STAGES = (
    ("Etapa 01 — Pesquisa e definição do projeto", "etapa-01-pesquisa.md"),
    ("Etapa 02 — Requisitos e modelagem", "etapa-02-requisitos-e-diagramas.md"),
    ("Etapa 03 — Desenvolvimento e validação", "etapa-03-desenvolvimento.md"),
)
CONTENTS = (
    ("Resumo e introdução", "Projeto Interdisciplinar IV — Lock"),
    ("Etapa 01 — Pesquisa e definição do projeto", "Etapa 01 — Pesquisa e definição do projeto"),
    ("Etapa 02 — Requisitos e modelagem", "Etapa 02 — Requisitos e modelagem"),
    ("Etapa 03 — Desenvolvimento e validação do software", "Etapa 03 — Desenvolvimento e validação"),
    ("Etapa 04 — Relato de experiência", "Etapa 04 — Relato de experiência"),
    ("Considerações finais", "Considerações finais"),
)


def stage_body(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^## 1\.", source)
    if match is None:
        raise ValueError(f"Primeira seção numerada não encontrada em {path}")
    body = source[match.start() :]
    # PNG é mais compatível com a importação do HTML pelo LibreOffice.
    body = body.replace("diagramas/modelo-conceitual.svg", "../diagramas/modelo-conceitual.png")
    body = body.replace("diagramas/casos-de-uso.svg", "../diagramas/casos-de-uso.png")
    body = body.replace("diagramas/classes.svg", "../diagramas/classes.png")
    body = body.replace("diagramas/sequencia-simulacao.svg", "../diagramas/sequencia-simulacao.png")
    body = re.sub(r"\(diagramas/([^)]+\.puml)\)", r"(../diagramas/\1)", body)
    body = re.sub(
        r"Arquivo-fonte: \[([^]]+)\]\(\.\./diagramas/[^)]+\)\.",
        "",
        body,
    )
    return body


def build_markdown(experience: str, private_context: str = "") -> str:
    introduction = """# Projeto Interdisciplinar IV — Lock

## Resumo

O Lock é um protótipo acadêmico de serviço web para conscientização contra
phishing. O projeto reúne pesquisa de nicho, requisitos e modelagem, uma
cartilha, oito exercícios simulados, autenticação, persistência, painel
administrativo e testes automatizados. Todo o treinamento acontece dentro do
sistema, sem envio de mensagens a terceiros. Este relatório reúne as quatro
etapas previstas no manual do Projeto Interdisciplinar IV.

**Palavras-chave:** phishing; engenharia social; conscientização; segurança da
informação; aplicação web.

## Introdução geral

O trabalho toma como referência o exemplo de simulação de engenharia social e
medidas de conscientização apresentado no manual do Projeto Interdisciplinar IV.
O problema abordado é a dificuldade de avaliar mensagens aparentemente
legítimas antes de clicar, informar dados ou abrir anexos. A solução proposta é
um ambiente controlado de aprendizagem, no qual cada decisão gera uma
explicação e fica registrada para revisão. O protótipo não é afiliado às marcas
citadas nos exercícios nem utiliza sistemas ou dados internos de instituições.

## Organização do relatório

1. Etapa 01 — pesquisa do nicho, análise de referências e escopo.
2. Etapa 02 — requisitos, regras de negócio, casos de uso e diagramas.
3. Etapa 03 — implementação, controles, testes e demonstração.
4. Etapa 04 — relato da experiência e dos aprendizados.

"""
    sections = [introduction]
    for title, filename in STAGES:
        sections.append(f"# {title}\n\n{stage_body(DOCS / filename)}")
    experience_parts = [part for part in (private_context.strip(), experience.strip()) if part]
    sections.append("# Etapa 04 — Relato de experiência\n\n" + "\n\n".join(experience_parts))
    sections.append(
        "# Considerações finais\n\n"
        "O objetivo deste projeto foi transformar orientações de prevenção ao "
        "phishing em uma experiência de aprendizagem prática e segura. A pesquisa "
        "delimitou o nicho e o escopo; a modelagem descreveu requisitos, casos de "
        "uso, entidades e interações; e o desenvolvimento reuniu esses elementos "
        "em uma aplicação web funcional. Assim, o trabalho relaciona conceitos "
        "de Segurança da Informação, programação, banco de dados e engenharia "
        "de software em uma única solução demonstrável.\n\n"
        "No recorte implementado, o Lock oferece cartilha, oito exercícios de "
        "análise de mensagens, feedback imediato, registro de tentativas, "
        "progresso individual e administração de conteúdo. A combinação de "
        "mensagens fraudulentas, legítimas e inconclusivas procura reduzir "
        "respostas automáticas e favorecer a justificativa de cada decisão. "
        "Os testes automatizados confirmam os fluxos principais e controles "
        "básicos da aplicação local, inclusive a preservação do histórico após "
        "a revisão de um exercício.\n\n"
        "O resultado demonstra a viabilidade técnica da proposta como prova "
        "de conceito acadêmica. Ainda não há evidência de eficácia pedagógica "
        "com usuários reais, nem auditoria profissional de segurança ou "
        "infraestrutura para uso público. Essas limitações orientam uma "
        "continuidade possível: avaliação com participantes, revisão técnica "
        "independente e preparação de controles operacionais antes de qualquer "
        "aplicação fora do ambiente de demonstração.\n"
    )
    return "\n\n".join(sections)


STYLE = """
@page {
  size: A4;
  margin: 2.25cm 2.15cm 2.3cm;
  @bottom-right { content: counter(page); color: #65787b; font: 9pt Arial, sans-serif; }
}
* { box-sizing: border-box; }
body { color: #24343a; background: white; font: 11pt/1.5 Georgia, 'Liberation Serif', serif; }
.cover, .title-page, .contents { break-after: page; min-height: 24cm; }
.cover { display: flex; flex-direction: column; justify-content: space-between; text-align: center; padding: 1.2cm 0 .5cm; }
.cover .institution { color: #17565b; font: 700 11pt/1.4 Arial, sans-serif; letter-spacing: .08em; text-transform: uppercase; }
.cover .project { margin: 1.7cm auto 0; color: #183a41; font: 700 34pt/1.08 Georgia, serif; letter-spacing: -.03em; }
.cover .subtitle { max-width: 13cm; margin: .5cm auto 0; font: 14pt/1.35 Arial, sans-serif; }
.cover .author { font: 700 12pt Arial, sans-serif; }
.cover .place { font: 11pt Arial, sans-serif; }
.accent { width: 3.2cm; height: 4px; margin: .7cm auto; background: #d89a48; }
.title-page { padding-top: 1.4cm; }
.title-page h1 { margin-top: 1.6cm; font: 700 25pt/1.15 Georgia, serif; }
.title-page .statement { max-width: 10cm; margin: 3cm 0 0 auto; font: 11pt/1.5 Georgia, serif; text-align: justify; }
.title-page .place { margin-top: 5cm; text-align: center; }
.contents { padding-top: 1.3cm; }
.contents h1 { border-bottom: 2px solid #d89a48; padding-bottom: .25cm; }
.contents-table { margin: .75cm 0 0; font: 11pt Georgia, 'Liberation Serif', serif; }
.contents-table td { padding: .16cm 0; border: 0; border-bottom: 1px dotted #9aabae; }
.contents-table .page-number { width: 1cm; text-align: right; font: 10pt Arial, sans-serif; }
main h1 { break-before: page; margin: 0 0 .8cm; padding-bottom: .22cm; border-bottom: 3px solid #d89a48; color: #183a41; font: 700 22pt/1.2 Georgia, serif; }
main h1:first-child { break-before: auto; }
main h2 { break-after: avoid; margin: .7cm 0 .25cm; color: #17565b; font: 700 15pt/1.25 Georgia, serif; }
main h2[id="3-diagrama-de-casos-de-uso"],
main h2[id="6-diagrama-de-sequencia"] { break-before: page; }
main h3 { break-after: avoid; margin: .5cm 0 .18cm; color: #294950; font: 700 12pt/1.25 Arial, sans-serif; }
p { margin: 0 0 .38cm; text-align: justify; orphans: 3; widows: 3; }
ul, ol { margin-top: .1cm; padding-left: .65cm; }
li { margin-bottom: .12cm; }
table { width: 100%; margin: .35cm 0 .5cm; border-collapse: collapse; font: 9.2pt/1.35 Arial, sans-serif; }
th, td { padding: .18cm .2cm; border: 1px solid #cbd8d8; text-align: left; vertical-align: top; }
th { color: #173d43; background: #e8f0ef; }
tr { break-inside: avoid; }
blockquote { margin: .35cm 0; padding: .2cm .3cm; border-left: 4px solid #d89a48; background: #f7f5ef; }
blockquote p { margin: 0; }
code { padding: 0 .06cm; color: #174d52; background: #f0f5f4; font: 9pt 'Liberation Mono', monospace; }
pre { padding: .3cm; overflow-wrap: anywhere; background: #f0f5f4; font: 8pt/1.4 'Liberation Mono', monospace; }
pre code { padding: 0; background: none; }
img { display: block; max-width: 100%; max-height: 17cm; width: auto; height: auto; margin: .4cm auto; object-fit: contain; }
a { color: #17565b; text-decoration: underline; overflow-wrap: anywhere; }
strong { color: #1b353a; }
@media screen { body { max-width: 21cm; margin: 1cm auto; box-shadow: 0 0 25px #c8d0cf; padding: .6cm; } }
"""


def build_html(body: str, args: argparse.Namespace, page_numbers: dict[str, int] | None = None) -> str:
    rendered = markdown.markdown(body, extensions=("tables", "fenced_code", "toc", "attr_list"))
    student = html.escape(args.aluno)
    teacher = html.escape(args.professor)
    city = html.escape(args.cidade)
    year = html.escape(args.ano)
    course = html.escape(args.curso)
    institution = html.escape(args.instituicao)
    page_numbers = page_numbers or {}
    contents = "".join(
        f'<tr><td>{html.escape(label)}</td><td class="page-number">{page_numbers.get(heading, "")}</td></tr>'
        for label, heading in CONTENTS
    )
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Lock — Relatório PI IV</title>
<style>{STYLE}</style></head><body>
<section class="cover"><div class="institution">{institution}<br>Curso de {course}</div>
<div><div class="project">LOCK</div><div class="accent"></div>
<div class="subtitle">Projeto Interdisciplinar 4<br>Desenvolvimento de aplicativo para e-commerce ou serviços<br>Treinamento e conscientização contra phishing</div></div>
<div><div class="author">{student}</div><div class="place">{city} · {year}</div></div></section>
<section class="title-page"><p>{student}</p><h1>Lock — plataforma web de conscientização contra phishing</h1>
<p class="statement">Projeto Interdisciplinar 4 apresentado à {institution} como exigência parcial da disciplina Projeto Interdisciplinar 4, do curso de {course}, sob a orientação do Prof. {teacher}.</p>
<p class="place">{city}<br>{year}</p></section>
<section class="contents"><h1>Sumário</h1><table class="contents-table">{contents}</table>
<p>Os diagramas da Etapa 02 são apresentados no corpo do relatório e mantidos em arquivos-fonte editáveis no projeto.</p></section>
<main>{rendered}</main></body></html>"""


def find_pdf_page_numbers(pdf_path: Path) -> dict[str, int]:
    extractor = shutil.which("pdftotext")
    if extractor is None:
        return {}
    result = subprocess.run(
        [extractor, "-layout", str(pdf_path), "-"],
        check=True, timeout=30, capture_output=True, text=True,
    )
    pages = result.stdout.split("\f")
    return {
        heading: next(
            (number for number, page in enumerate(pages, start=1)
             if number > 3 and heading in page),
            0,
        )
        for _, heading in CONTENTS
    }


def embed_docx_images(source: Path, destination: Path) -> None:
    """Inclui os diagramas no DOCX; o LibreOffice os exporta como links locais."""
    rel_name = "word/_rels/document.xml.rels"
    types_name = "[Content_Types].xml"
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    types_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    ET.register_namespace("", rel_ns)
    with ZipFile(source) as archive:
        relationships = ET.fromstring(archive.read(rel_name))
        content_types = ET.fromstring(archive.read(types_name))
        images: dict[str, bytes] = {}
        image_ids: list[str] = []
        for index, relation in enumerate(relationships, start=1):
            if not relation.attrib.get("Type", "").endswith("/image"):
                continue
            if relation.attrib.get("TargetMode") != "External":
                continue
            url = urllib.parse.urlparse(relation.attrib["Target"])
            image_path = Path(urllib.parse.unquote(url.path)).resolve()
            if url.scheme != "file" or DOCS / "diagramas" not in image_path.parents:
                raise ValueError(f"Imagem externa inesperada no DOCX: {image_path}")
            member = f"word/media/diagrama-{index}.png"
            images[member] = image_path.read_bytes()
            image_ids.append(relation.attrib["Id"])
            relation.set("Target", f"media/diagrama-{index}.png")
            relation.attrib.pop("TargetMode", None)
        if not any(item.attrib.get("Extension") == "png" for item in content_types):
            ET.SubElement(
                content_types, f"{{{types_ns}}}Default",
                {"Extension": "png", "ContentType": "image/png"},
            )
        rel_xml = ET.tostring(relationships, encoding="utf-8", xml_declaration=True)
        ET.register_namespace("", types_ns)
        types_xml = ET.tostring(content_types, encoding="utf-8", xml_declaration=True)
        document_xml = archive.read("word/document.xml")
        for image_id in image_ids:
            document_xml = document_xml.replace(
                f'r:link="{image_id}"'.encode(), f'r:embed="{image_id}"'.encode()
            )
        modified = {
            rel_name: rel_xml,
            types_name: types_xml,
            "word/document.xml": document_xml,
        }
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as output:
            for item in archive.infolist():
                output.writestr(item, modified.get(item.filename, archive.read(item.filename)))
            for member, data in images.items():
                output.writestr(member, data)
    destination.write_bytes(buffer.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aluno", required=True)
    parser.add_argument("--professor", required=True)
    parser.add_argument("--cidade", required=True)
    parser.add_argument("--instituicao", required=True)
    parser.add_argument("--ano", default="2026")
    parser.add_argument("--curso", default="Análise e Desenvolvimento de Sistemas")
    parser.add_argument("--experiencia-arquivo", type=Path, default=DOCS / "etapa-04-relato-experiencia.md")
    args = parser.parse_args()

    if not args.experiencia_arquivo.is_file():
        parser.error("Arquivo da Etapa 04 não encontrado.")
    experience = stage_body(args.experiencia_arquivo).strip()
    if not experience or any(
        not value.strip()
        for value in (args.aluno, args.professor, args.cidade, args.instituicao)
    ):
        parser.error("Informe os dados acadêmicos e o conteúdo da Etapa 04.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    private_context = PRIVATE_CONTEXT.read_text(encoding="utf-8") if PRIVATE_CONTEXT.is_file() else ""
    body = build_markdown(experience, private_context)
    stem = "PI-IV-Lock-relatorio-final"
    markdown_path = OUTPUT / f"{stem}.md"
    html_path = OUTPUT / f"{stem}.html"
    pdf_path = OUTPUT / f"{stem}.pdf"
    docx_path = OUTPUT / f"{stem}.docx"
    markdown_path.write_text(body, encoding="utf-8")
    page_numbers: dict[str, int] = {}
    html_path.write_text(build_html(body, args, page_numbers), encoding="utf-8")

    generated_pdf = False
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome:
        with tempfile.TemporaryDirectory(prefix="lock-relatorio-") as profile:
            for _ in range(4):
                subprocess.run(
                    [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                     "--no-pdf-header-footer", f"--user-data-dir={profile}",
                     f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                    check=True, timeout=90, capture_output=True,
                )
                actual_pages = find_pdf_page_numbers(pdf_path)
                if any(number == 0 for number in actual_pages.values()):
                    raise RuntimeError("Não foi possível localizar todas as seções no PDF.")
                if actual_pages == page_numbers:
                    break
                page_numbers = actual_pages
                html_path.write_text(build_html(body, args, page_numbers), encoding="utf-8")
            else:
                raise RuntimeError("A paginação do sumário não estabilizou.")
        generated_pdf = True
    else:
        print("Chrome não encontrado; HTML gerado, mas PDF não foi criado.")
    generated_docx = False
    libreoffice = shutil.which("libreoffice")
    if libreoffice:
        with tempfile.TemporaryDirectory(prefix="lock-relatorio-docx-") as temp_dir:
            temp_path = Path(temp_dir)
            profile_uri = (temp_path / "profile").as_uri()
            subprocess.run(
                [libreoffice, f"-env:UserInstallation={profile_uri}", "--headless",
                 "--convert-to", "docx:Office Open XML Text", "--outdir", str(temp_path),
                 str(html_path)],
                check=True, timeout=90, capture_output=True,
            )
            converted = temp_path / docx_path.name
            if not converted.exists():
                raise RuntimeError("O LibreOffice não gerou o DOCX esperado.")
            embed_docx_images(converted, docx_path)
        generated_docx = True
    else:
        print("LibreOffice não encontrado; DOCX editável não foi criado.")
    if generated_pdf and generated_docx:
        markdown_path.unlink()
        html_path.unlink()
    else:
        print(f"Intermediários para conferência: {markdown_path}, {html_path}")
    if generated_pdf:
        print(f"PDF de entrega: {pdf_path}")
    if generated_docx:
        print(f"DOCX editável: {docx_path}")


if __name__ == "__main__":
    main()

"""Generate the single PDF and its Markdown source from the current repository.

Documentation-only dependency: ReportLab 4.1.0.
Run: uv run --with reportlab==4.1.0 python scripts/build_developer_handbook.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/handbook"
REPO = "https://github.com/viweb25/vi-websync-ai.git"
SKIP = {
    ".git",
    ".agents",
    ".codex",
    ".aws",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    ".local",
}
SPECIAL = json.loads((OUT / "file_descriptions.json").read_text())


def files():
    """List maintained files only, without reading local secret values."""
    found = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if any(part in SKIP for part in rel.parts) or not p.is_file():
            continue
        if p.name.startswith(".env") and p.name != ".env.example":
            continue
        if p.suffix in {".pyc", ".log", ".db", ".sqlite", ".onnx", ".pt", ".pth", ".enc"}:
            continue
        found.append(rel.as_posix())
    return sorted(
        set(found)
        | {
            "docs/handbook/VI_WebSync_Developer_Handbook.pdf",
            "docs/handbook/VI_WebSync_Developer_Handbook.md",
        }
    )


def describe(path):
    if path in SPECIAL:
        return SPECIAL[path]
    if path.startswith("docs/archive/"):
        return (
            "Historical starter reference, preserved during cleanup. "
            "Not active configuration or instructions; do not run its old commands."
        )
    p = ROOT / path
    if p.name == "__init__.py":
        return (
            "Python package marker and short module description; "
            "enables imports for this service or shared package."
        )
    if p.suffix == ".md":
        lines = p.read_text().splitlines()
        title = next((line.lstrip("# ") for line in lines if line.startswith("#")), "Documentation")
        if p.name == "README.md":
            content = " ".join(
                line.strip() for line in lines if line.strip() and not line.startswith("#")
            )
            return content[:650]
        return (
            title + ". Maintained reference for the team; read it for the detailed policy or plan."
        )
    if p.suffix == ".py":
        tree = ast.parse(p.read_text())
        names = [
            n.name
            for n in tree.body
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        return (
            "Python module. Top-level definitions: "
            + (", ".join(names) or "package initialization")
            + "."
        )
    return "Project source/configuration file; inspect alongside its parent folder guide."


def markdown():
    groups = {}
    for path in files():
        group = "Root configuration" if "/" not in path else path.split("/")[0]
        if path.startswith("docs/archive/"):
            group = "Archived starter — historical only"
        groups.setdefault(group, []).append(path)
    parts = []
    for group, paths in groups.items():
        parts.append(f"### {group}\n")
        for path in paths:
            parts.append(f"- `{path}` — {describe(path)}\n")
    template = (OUT / "handbook.template.md").read_text()
    return template.replace("{{REPOSITORY_URL}}", REPO).replace("{{INVENTORY}}", "\n".join(parts))


def render_pdf(source, path):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageBreak,
        PageTemplate,
        Paragraph,
        Preformatted,
        Spacer,
    )
    from reportlab.platypus.tableofcontents import TableOfContents

    font_dir = Path("/usr/share/fonts/truetype/dejavu")
    if font_dir.exists():
        for name, filename in [
            ("Handbook", "DejaVuSans.ttf"),
            ("HandbookBold", "DejaVuSans-Bold.ttf"),
            ("HandbookMono", "DejaVuSansMono.ttf"),
        ]:
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
        pdfmetrics.registerFontFamily("Handbook", normal="Handbook", bold="HandbookBold")
        normal, bold, mono = "Handbook", "HandbookBold", "HandbookMono"
    else:
        normal, bold, mono = "Helvetica", "Helvetica-Bold", "Courier"
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Body",
            fontName=normal,
            fontSize=9,
            leading=14,
            spaceAfter=8,
            textColor=colors.HexColor("#23343d"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Item", parent=styles["Body"], leftIndent=10, firstLineIndent=-7, spaceAfter=7
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1",
            fontName=bold,
            fontSize=29,
            leading=35,
            textColor=colors.HexColor("#123d46"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2",
            fontName=bold,
            fontSize=16,
            leading=21,
            spaceBefore=14,
            spaceAfter=10,
            keepWithNext=True,
            textColor=colors.HexColor("#123d46"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3",
            fontName=bold,
            fontSize=12,
            leading=17,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HandbookCode",
            fontName=mono,
            fontSize=7.1,
            leading=10.5,
            backColor=colors.HexColor("#edf2f4"),
            borderPadding=8,
            spaceBefore=5,
            spaceAfter=12,
            alignment=TA_LEFT,
        )
    )

    class Handbook(BaseDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and flowable.style.name == "H2":
                title = flowable.getPlainText()
                key = "section-" + title.split(".")[0]
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(title, key, 0)
                self.notify("TOCEntry", (0, title, self.page, key))

    def page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#c9d6dc"))
        canvas.line(20 * mm, 18 * mm, 190 * mm, 18 * mm)
        canvas.setFont(normal, 8)
        canvas.setFillColor(colors.HexColor("#607580"))
        canvas.drawString(
            20 * mm, 12 * mm, "VI WebSync  |  Developer Handbook  |  13 November 2026"
        )
        canvas.drawRightString(190 * mm, 12 * mm, str(doc.page))
        canvas.restoreState()

    doc = Handbook(
        str(path),
        pagesize=(210 * mm, 297 * mm),
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=19 * mm,
        bottomMargin=24 * mm,
        title="VI WebSync Developer Handbook",
        author="VI WebSync / Siva",
    )
    doc.addPageTemplates(
        PageTemplate(
            id="handbook",
            frames=[
                Frame(
                    doc.leftMargin,
                    doc.bottomMargin,
                    doc.width,
                    doc.height,
                    leftPadding=0,
                    rightPadding=0,
                    topPadding=0,
                    bottomPadding=0,
                )
            ],
            onPage=page,
        )
    )
    story = []
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(name="Contents", fontName=normal, fontSize=10, leading=18, spaceBefore=3)
    ]

    def markup(text):
        text = escape(text)
        return re.sub(r"`([^`]+)`", lambda m: f'<font name="{mono}" size="8">{m[1]}</font>', text)

    block, code, in_code = [], [], False

    def flush():
        if block:
            story.append(Paragraph(markup(" ".join(block)), styles["Body"]))
            block.clear()

    inserted_toc = False
    for line in source.splitlines():
        if line.startswith("```"):
            flush()
            if in_code:
                story.append(
                    Preformatted("\n".join(code), styles["HandbookCode"], maxLineLength=103)
                )
                code = []
            in_code = not in_code
        elif in_code:
            code.append(line)
        elif line.startswith("## "):
            flush()
            if not inserted_toc:
                story.append(Spacer(1, 12 * mm))
                story.append(Paragraph("Contents", styles["H3"]))
                story.append(toc)
                story.append(PageBreak())
                inserted_toc = True
            story.append(Paragraph(markup(line[3:]), styles["H2"]))
        elif line.startswith("### "):
            flush()
            story.append(Paragraph(markup(line[4:]), styles["H3"]))
        elif line.startswith("# "):
            flush()
            story.append(Spacer(1, 12 * mm))
            story.append(Paragraph(markup(line[2:]), styles["H1"]))
        elif line.startswith("- "):
            flush()
            story.append(Paragraph("• " + markup(line[2:]), styles["Item"]))
        elif not line.strip():
            flush()
        else:
            block.append(line)
    flush()
    doc.multiBuild(story)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = markdown()
    (OUT / "VI_WebSync_Developer_Handbook.md").write_text(source)
    render_pdf(source, OUT / "VI_WebSync_Developer_Handbook.pdf")
    print(f"Handbook generated: {len(files())} maintained files documented.")


if __name__ == "__main__":
    main()

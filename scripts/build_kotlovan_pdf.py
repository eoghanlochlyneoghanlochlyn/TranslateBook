from pathlib import Path
import re

from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from arabic_reshaper import reshape
from bidi.algorithm import get_display

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "translations" / "kotlovan-fa.txt"
OUT = ROOT / "pdf" / "kotlovan-fa.pdf"
FONT = ROOT / "fonts" / "NotoNaskhArabic-Regular.ttf"

OUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont("NotoNaskh", str(FONT)))


def rtl(text: str) -> str:
    """Shape Arabic/Persian glyphs and apply bidi ordering for ReportLab."""
    return get_display(reshape(text))


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


raw = SRC.read_text(encoding="utf-8")
raw = raw.replace("\r\n", "\n").replace("\r", "\n")

# The TXT contains source-page markers for translation tracking.
# They are intentionally omitted from the book layout.
raw = re.sub(r"\n\s*\[صفحه(?:ٔ|‌ٔ)?\s*\d+\]\s*\n", "\n\n", raw)
raw = re.sub(r"^\s*\[صفحات\s*۱\s*تا\s*۵\]\s*\n", "", raw)
raw = re.sub(r"^\s*\[صفحات\s*\d+\s*تا\s*\d+\]\s*\n", "", raw, flags=re.M)

blocks = re.split(r"\n\s*\n+", raw)
blocks = [b.strip() for b in blocks if b.strip()]

title = "گودال پی"
author = "آندری پلاتونوف"
subtitle = "ترجمهٔ فارسی"

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A5,
    rightMargin=19 * mm,
    leftMargin=19 * mm,
    topMargin=19 * mm,
    bottomMargin=18 * mm,
    title=title,
    author=author,
    subject="ترجمهٔ فارسی رمان گودال پی",
)

title_style = ParagraphStyle(
    "TitleFA",
    fontName="NotoNaskh",
    fontSize=23,
    leading=31,
    alignment=TA_CENTER,
    spaceAfter=10 * mm,
)

author_style = ParagraphStyle(
    "AuthorFA",
    fontName="NotoNaskh",
    fontSize=15,
    leading=23,
    alignment=TA_CENTER,
    spaceAfter=4 * mm,
)

subtitle_style = ParagraphStyle(
    "SubtitleFA",
    fontName="NotoNaskh",
    fontSize=12,
    leading=20,
    alignment=TA_CENTER,
    spaceAfter=12 * mm,
)

body_style = ParagraphStyle(
    "BodyFA",
    fontName="NotoNaskh",
    fontSize=11.7,
    leading=21,
    alignment=TA_RIGHT,
    firstLineIndent=7 * mm,
    spaceBefore=0,
    spaceAfter=4.5 * mm,
    splitLongWords=False,
)

dialog_style = ParagraphStyle(
    "DialogFA",
    fontName="NotoNaskh",
    fontSize=11.7,
    leading=21,
    alignment=TA_RIGHT,
    firstLineIndent=0,
    leftIndent=0,
    rightIndent=0,
    spaceBefore=1.5 * mm,
    spaceAfter=3 * mm,
    splitLongWords=False,
)

break_style = ParagraphStyle(
    "BreakFA",
    fontName="NotoNaskh",
    fontSize=13,
    leading=20,
    alignment=TA_CENTER,
    spaceBefore=3 * mm,
    spaceAfter=3 * mm,
)

story = [
    Spacer(1, 35 * mm),
    Paragraph(rtl(esc(title)), title_style),
    Paragraph(rtl(esc(author)), author_style),
    Paragraph(rtl(esc(subtitle)), subtitle_style),
    PageBreak(),
]


def is_dialogue_block(block: str) -> bool:
    """Detect a paragraph whose first visible character is a dialogue dash."""
    return bool(re.match(r"^[\s]*[ـ—–-](?:\s|$)", block))


def clean_dialogue(text: str) -> str:
    # Normalize common dash variants used as Persian dialogue markers.
    # Keep the marker itself; bidi shaping is applied to the complete line.
    text = text.strip()
    text = re.sub(r"^[ـ–-]\s*", "— ", text)
    return text


for block in blocks:
    if block.strip() in {"***", "— — —"}:
        story.append(Paragraph(rtl("⋆ ⋆ ⋆"), break_style))
        continue

    if is_dialogue_block(block):
        # Dialogue paragraphs are intentionally kept separate from prose:
        # no first-line indent, slightly tighter vertical spacing, and the
        # dialogue marker remains part of the RTL line.
        text = re.sub(r"\s*\n\s*", " ", block).strip()
        text = clean_dialogue(text)
        story.append(Paragraph(rtl(esc(text)), dialog_style))
        continue

    # Prose paragraphs keep their source paragraph boundaries and indentation.
    text = re.sub(r"\s*\n\s*", " ", block).strip()
    story.append(Paragraph(rtl(esc(text)), body_style))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("NotoNaskh", 9)
    canvas.drawCentredString(A5[0] / 2, 9 * mm, str(doc.page))
    canvas.restoreState()


doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Built {OUT}")

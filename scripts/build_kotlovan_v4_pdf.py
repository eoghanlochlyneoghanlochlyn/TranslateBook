#!/usr/bin/env python3
from pathlib import Path
import re
from bidi.algorithm import get_display
from arabic_reshaper import reshape
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "translations/kotlovan-fa-v4-edited.txt"
OUT = ROOT / "pdf/kotlovan-fa-v4-edited.pdf"

def font(candidates):
    for p in candidates:
        if Path(p).exists():
            return p
    raise FileNotFoundError("Persian font not found")

pdfmetrics.registerFont(TTFont("Persian", font([
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf"
])))
pdfmetrics.registerFont(TTFont("PersianBold", font([
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Bold.ttf"
])))

def rtl(s):
    return get_display(reshape(s))

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

raw = SRC.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").strip()

# Accept both Persian and ASCII digits in page markers and normalize them
# only for validation/removal. The edited text may contain either form.
def marker_num(value):
    return int(value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))

marker_matches = re.findall(r"^\[صفحهٔ\s*([0-9۰-۹]+)\]\s*$", raw, re.M)
markers = [marker_num(x) for x in marker_matches]
expected = list(range(1, 72))
if markers != expected:
    raise SystemExit(f"Expected page markers 1..71, got {marker_matches}")

raw = re.sub(r"^\[صفحهٔ\s*[0-9۰-۹]+\]\s*$", "", raw, flags=re.M)
raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A5,
    rightMargin=17 * mm,
    leftMargin=17 * mm,
    topMargin=18 * mm,
    bottomMargin=17 * mm,
    title="گودال پی — آندری پلاتونوف",
    author="ترجمهٔ فارسی — ویرایش ادبی",
)

title = ParagraphStyle(
    "Title", fontName="PersianBold", fontSize=21, leading=29,
    alignment=TA_CENTER, spaceAfter=7 * mm
)
author = ParagraphStyle(
    "Author", fontName="Persian", fontSize=13.5, leading=21,
    alignment=TA_CENTER, spaceAfter=4 * mm
)
body = ParagraphStyle(
    "Body", fontName="Persian", fontSize=11.2, leading=21.2,
    alignment=TA_RIGHT, firstLineIndent=7 * mm,
    spaceAfter=5.2 * mm, splitLongWords=False, wordWrap="RTL"
)
dialog = ParagraphStyle(
    "Dialog", fontName="Persian", fontSize=11.2, leading=21.2,
    alignment=TA_RIGHT, firstLineIndent=0,
    spaceBefore=1.5 * mm, spaceAfter=4.5 * mm,
    splitLongWords=False, wordWrap="RTL"
)

story = [
    Spacer(1, 34 * mm),
    Paragraph(rtl(esc("گودال پی")), title),
    Paragraph(rtl(esc("آندری پلاتونوف")), author),
    Paragraph(rtl(esc("ترجمهٔ فارسی — ویرایش ادبی")), author),
    PageBreak(),
]

for block in blocks:
    if block in {"***", "— — —"}:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(rtl("⋆ ⋆ ⋆"), body))
        story.append(Spacer(1, 3 * mm))
        continue

    # Newlines inside a paragraph are layout artifacts, not prose breaks.
    block = re.sub(r"\s*\n\s*", " ", block).strip()

    # A dialogue marker always starts a new paragraph, even when it was
    # accidentally placed after narrator text on the same source line.
    parts = re.split(r"\s+(?=—\s+)", block)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"^[–-]\s*", "— ", part)
        style = dialog if part.startswith("— ") else body
        story.append(Paragraph(rtl(esc(part)), style))

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Persian", 8.5)
    canvas.drawCentredString(A5[0] / 2, 10 * mm, str(doc.page))
    canvas.restoreState()

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Created {OUT}")
from pathlib import Path
import re

from bidi.algorithm import get_display
import arabic_reshaper
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
)

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "translations"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
OUTPUT = DIST / "kotlovan-fa-v2.pdf"

# Noto Sans Arabic has broad Persian coverage and renders cleanly in ReportLab.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
]
FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
]

def first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return p
    raise FileNotFoundError("Persian Unicode font was not found.")

font_regular = first_existing(FONT_CANDIDATES)
font_bold = first_existing(FONT_BOLD_CANDIDATES)

pdfmetrics.registerFont(TTFont("Persian", font_regular))
pdfmetrics.registerFont(TTFont("PersianBold", font_bold))

def rtl(text: str) -> str:
    if not text.strip():
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def para_text(text: str) -> str:
    # Escape only characters meaningful to ReportLab XML.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return rtl(text)

def page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Persian", 8.5)
    canvas.drawCentredString(A5[0] / 2, 10 * mm, str(doc.page))
    canvas.restoreState()

files = sorted(
    TRANSLATIONS.glob("kotlovan-fa-v2-pages-*.txt"),
    key=lambda p: int(re.search(r"pages-(\d+)", p.name).group(1))
)

if not files:
    raise SystemExit("No translation page files found.")

# The source files contain page markers such as [صفحهٔ ۱۲].
# We retain them as subtle section markers while removing duplicate headers.
body = []
seen_intro = False

for path in files:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    for line in lines:
        s = line.strip()

        if not s:
            body.append(Spacer(1, 3.2 * mm))
            continue

        if s in {
            "گودال پی",
            "آندری پلاتونوف",
            "ترجمهٔ فارسی ــ بازترجمهٔ ادبی، نسخهٔ ۲",
        }:
            if seen_intro:
                continue
            if s == "گودال پی":
                body.append(Paragraph(para_text(s), ParagraphStyle(
                    "BookTitle", fontName="PersianBold", fontSize=24,
                    leading=32, alignment=TA_CENTER, spaceAfter=5*mm
                )))
            elif s == "آندری پلاتونوف":
                body.append(Paragraph(para_text(s), ParagraphStyle(
                    "Author", fontName="Persian", fontSize=15,
                    leading=22, alignment=TA_CENTER, spaceAfter=2*mm
                )))
            else:
                body.append(Paragraph(para_text(s), ParagraphStyle(
                    "Edition", fontName="Persian", fontSize=9.5,
                    leading=15, alignment=TA_CENTER, spaceAfter=15*mm
                )))
            seen_intro = True
            continue

        m = re.fullmatch(r"\[صفحهٔ\s*(\d+)\]", s)
        if m:
            # Page markers are not printed; physical PDF pagination is independent.
            continue

        # Preserve dialogue turns and paragraph boundaries exactly.
        style = ParagraphStyle(
            "Body",
            fontName="Persian",
            fontSize=11.2,
            leading=20,
            alignment=TA_RIGHT,
            rightIndent=0,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=2.2 * mm,
            splitLongWords=False,
        )
        body.append(Paragraph(para_text(s), style))

doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=A5,
    rightMargin=18 * mm,
    leftMargin=18 * mm,
    topMargin=20 * mm,
    bottomMargin=17 * mm,
    title="گودال پی — آندری پلاتونوف",
    author="ترجمهٔ فارسی، بازترجمهٔ ادبی نسخهٔ ۲",
    subject="ترجمهٔ کامل فارسی رمان گودال پی",
)

doc.build(body, onFirstPage=page_number, onLaterPages=page_number)
print(f"Created {OUTPUT}")

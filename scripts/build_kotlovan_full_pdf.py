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
SRC = ROOT / "translations/kotlovan-fa-v3-edited.txt"
OUT = ROOT / "pdf/kotlovan-fa-v3-edited.pdf"

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

raw = SRC.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
if len(re.findall(r"^\[صفحهٔ\s*\d+\]\s*$", raw, re.M)) != 71:
    raise SystemExit("Expected exactly 71 page markers in edited source.")

raw = re.sub(r"^\[صفحهٔ\s*\d+\]\s*$", "\n\n", raw, flags=re.M)
raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
blocks = [b.strip() for b in re.split(r"\n\s*\n+", raw) if b.strip()]

doc = SimpleDocTemplate(str(OUT), pagesize=A5, rightMargin=18*mm, leftMargin=18*mm,
                        topMargin=20*mm, bottomMargin=17*mm,
                        title="گودال پی — آندری پلاتونوف",
                        author="ترجمهٔ فارسی، ویرایش ادبی")

title = ParagraphStyle("Title", fontName="PersianBold", fontSize=22, leading=30,
                       alignment=TA_CENTER, spaceAfter=7*mm)
author = ParagraphStyle("Author", fontName="Persian", fontSize=14, leading=22,
                        alignment=TA_CENTER, spaceAfter=5*mm)
body = ParagraphStyle("Body", fontName="Persian", fontSize=11.4, leading=20.5,
                      alignment=TA_RIGHT, firstLineIndent=7*mm,
                      spaceAfter=4.2*mm, splitLongWords=False)
dialog = ParagraphStyle("Dialog", fontName="Persian", fontSize=11.4, leading=20.5,
                        alignment=TA_RIGHT, firstLineIndent=0,
                        spaceBefore=1.2*mm, spaceAfter=3.2*mm,
                        splitLongWords=False)

story = [Spacer(1, 35*mm), Paragraph(rtl(esc("گودال پی")), title),
         Paragraph(rtl(esc("آندری پلاتونوف")), author),
         Paragraph(rtl(esc("ترجمهٔ فارسی — ویرایش ادبی")), author), PageBreak()]

for block in blocks:
    if block in {"***", "— — —"}:
        story.append(Paragraph(rtl("⋆ ⋆ ⋆"), body))
        continue
    if re.match(r"^[—–-]\s+", block):
        text = re.sub(r"\s*\n\s*", " ", block).strip()
        text = re.sub(r"^[–-]\s*", "— ", text)
        story.append(Paragraph(rtl(esc(text)), dialog))
    else:
        text = re.sub(r"\s*\n\s*", " ", block).strip()
        story.append(Paragraph(rtl(esc(text)), body))

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Persian", 8.5)
    canvas.drawCentredString(A5[0]/2, 10*mm, str(doc.page))
    canvas.restoreState()

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Created {OUT}")

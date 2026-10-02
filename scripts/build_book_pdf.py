from pathlib import Path
import re

from bidi.algorithm import get_display
import arabic_reshaper
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "translations"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
OUTPUT = DIST / "kotlovan-fa-v2.pdf"

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
    for path in paths:
        if Path(path).exists():
            return path
    raise FileNotFoundError("Persian Unicode font was not found.")


pdfmetrics.registerFont(TTFont("Persian", first_existing(FONT_CANDIDATES)))
pdfmetrics.registerFont(TTFont("PersianBold", first_existing(FONT_BOLD_CANDIDATES)))


def rtl(text: str) -> str:
    if not text.strip():
        return ""
    return get_display(arabic_reshaper.reshape(text))


def para_text(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return rtl(text)


def page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Persian", 8.5)
    canvas.drawCentredString(A5[0] / 2, 10 * mm, str(doc.page))
    canvas.restoreState()


BODY_STYLE = ParagraphStyle(
    "Body",
    fontName="Persian",
    fontSize=11.2,
    leading=20,
    alignment=TA_RIGHT,
    spaceAfter=2.2 * mm,
    splitLongWords=False,
)


def add_text(body, raw):
    for line in raw.splitlines():
        s = line.strip()

        if not s:
            body.append(Spacer(1, 3.2 * mm))
            continue

        if s in {
            "گودال پی",
            "آندری پلاتونوف",
            "ترجمهٔ فارسی ــ بازترجمهٔ ادبی، نسخهٔ آزمایشی",
            "ترجمهٔ فارسی ــ بازترجمهٔ ادبی، نسخهٔ ۲",
        }:
            continue

        if re.fullmatch(r"\[صفحهٔ\s*\d+\]", s):
            continue

        body.append(Paragraph(para_text(s), BODY_STYLE))


body = []

# Source pages 1–10 are stored in the complete translation file.
complete_file = TRANSLATIONS / "kotlovan-fa-v2.txt"
if not complete_file.exists():
    raise SystemExit(f"Missing required source file: {complete_file}")

raw_complete = complete_file.read_text(encoding="utf-8")
marker_re = re.compile(r"^\[صفحهٔ\s*(\d+)\]\s*$", re.MULTILINE)
markers = list(marker_re.finditer(raw_complete))

if not markers:
    raise SystemExit("No source page markers found in kotlovan-fa-v2.txt.")

page_numbers = [int(m.group(1)) for m in markers]
if 1 not in page_numbers:
    raise SystemExit("Source page 1 marker is missing from kotlovan-fa-v2.txt.")

# The complete file currently contains pages 1–10. Do not assume page 11
# exists in this file; later pages are stored in the batch files below.
add_text(body, raw_complete)

# Pages 11 onward are stored in the existing page-batch files.
files = sorted(
    TRANSLATIONS.glob("kotlovan-fa-v2-pages-*.txt"),
    key=lambda p: int(re.search(r"pages-(\d+)", p.name).group(1)),
)

for path in files:
    add_text(body, path)

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

#!/usr/bin/env python3
import json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "translations"
OUTPUT = TRANSLATIONS / "kotlovan-fa-v4-edited.txt"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
API_KEY = os.getenv("GEMINI_API_KEY")

FIRST_SOURCE = TRANSLATIONS / "kotlovan-fa-v3-edited.txt"
EXTRA_SOURCES = [
    TRANSLATIONS / f"kotlovan-fa-v2-pages-{a}-{b}.txt"
    for a, b in [(11,15),(16,20),(21,25),(26,30),(31,35),(36,40),
                 (41,45),(46,50),(51,55),(56,60),(61,65),(66,71)]
]

PROMPT = """تو ویراستار ادبی حرفه‌ای زبان فارسی هستی. متن زیر نسخهٔ قبلیِ ویرایش‌شدهٔ ترجمهٔ رمان «گودال پی» اثر آندری پلاتونوف است.

فقط بازبینی نهایی و ویرایش ادبی انجام بده؛ دوباره ترجمه نکن و محتوای تازه نساز.
هیچ جمله، رویداد، شخصیت، نام، عدد، جزئیات یا ابهام معنایی را حذف یا اضافه نکن.
جمله‌های ناقص، سنگین، ترجمه‌وار یا نامأنوس را به فارسی طبیعی و ادبی بازنویسی کن، بدون تغییر معنا.
لحن سرد، فلسفی، تلخ و طنز تلخ پلاتونوف را حفظ کن.
هر واحد روایی مستقل یک پاراگراف باشد.
هر دیالوگ یک گوینده در یک پاراگراف مستقل باشد و با «— » شروع شود.
دیالوگ و متن راوی هرگز در یک پاراگراف ادغام نشوند.
اگر چند دیالوگ پشت سر هم وجود دارد، هر نوبت گفت‌وگو پاراگراف جداگانه باشد.
برای ظاهر صفحه، وسط جمله یا پاراگراف شکست خط ایجاد نکن؛ خط جدید فقط برای پاراگراف جدید یا دیالوگ جدید باشد.
نشانه‌گذاری، فاصله و نیم‌فاصله را اصلاح کن.
برچسب [صفحهٔ N] را دقیقاً حفظ کن.
فقط متن نهایی را برگردان؛ هیچ توضیح یا یادداشت نده."""

def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)

if not API_KEY:
    fail("GEMINI_API_KEY is not set.")

def normalize(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()

def markers(text):
    return re.findall(r"^\[صفحهٔ\s*\d+\]\s*$", text, re.M)

def load_sources():
    if not FIRST_SOURCE.exists():
        fail(f"Missing source: {FIRST_SOURCE}")
    texts = [normalize(FIRST_SOURCE.read_text(encoding="utf-8"))]
    for path in EXTRA_SOURCES:
        if not path.exists():
            fail(f"Missing source: {path}")
        texts.append(normalize(path.read_text(encoding="utf-8")))
    return texts

def split_pages(text, expected_start=None, expected_end=None):
    # بعضی از فایل‌های صفحه‌بندی‌شده، به‌دلیل استخراج PDF، برچسب یک صفحه را
    # جا انداخته‌اند. در این سه مورد، شروع صفحه با شماره فصل مشخص شده است.
    if expected_start is not None and expected_end is not None:
        inferred_starts = {
            12: r"^\[۳\]\s*$",
            57: r"^\[۹\]\s*$",
            62: r"^\[۱۰\]\s*$",
        }
        for page_no in range(expected_start, expected_end + 1):
            if not re.search(rf"^\[صفحهٔ\s*{page_no}\]\s*$", text, re.M):
                chapter_pattern = inferred_starts.get(page_no)
                if chapter_pattern:
                    match = re.search(chapter_pattern, text, re.M)
                    if match:
                        marker = f"[صفحهٔ {page_no}]"
                        text = text[:match.start()] + marker + "\n\n" + text[match.start():]
                        break

    matches = list(re.finditer(r"^\[صفحهٔ\s*(\d+)\]\s*$", text, re.M))
    if not matches:
        fail("No page markers found.")
    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks.append(text[start:end].strip())
    return chunks

def call_gemini(text):
    prompt = PROMPT + "\n\nبخش زیر را کامل ویرایش کن و هیچ بخشی را حذف یا خلاصه نکن:\n\n" + text
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 32768},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        response = json.loads(resp.read().decode("utf-8"))
    parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    edited = "".join(p.get("text", "") for p in parts).strip()
    if not edited:
        raise RuntimeError("Gemini returned empty output.")
    edited = re.sub(r"^```(?:text|markdown)?\s*", "", edited)
    edited = re.sub(r"\s*```$", "", edited).strip()
    return edited

def clean_dialogues(text):
    lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if re.match(r"^\s*[–-]\s+", line):
            line = re.sub(r"^\s*[–-]\s*", "— ", line)
        lines.append(line)
    return "\n".join(lines).strip()

sources = load_sources()
all_pages = []
ranges = [(1, 10)] + [(a, b) for a, b in [(11,15),(16,20),(21,25),(26,30),(31,35),(36,40),
                                           (41,45),(46,50),(51,55),(56,60),(61,65),(66,71)]]
for source, (start_page, end_page) in zip(sources, ranges):
    all_pages.extend(split_pages(source, start_page, end_page))

numbers = [int(re.match(r"^\[صفحهٔ\s*(\d+)\]", p).group(1)) for p in all_pages]
expected = list(range(1, 72))
if numbers != expected:
    fail(f"Page sequence is not 1..71: {numbers}")

edited_pages = []
for index, page in enumerate(all_pages, start=1):
    source_markers = markers(page)
    if len(source_markers) != 1:
        fail(f"Page chunk {index} does not contain exactly one page marker.")
    last_error = None
    for attempt in range(4):
        try:
            edited = clean_dialogues(call_gemini(page))
            if markers(edited) != source_markers:
                raise RuntimeError("Page marker changed or disappeared.")
            if len(edited) < int(len(page) * 0.70):
                raise RuntimeError("Output is suspiciously short.")
            edited_pages.append(edited)
            print(f"Edited page {numbers[index-1]} ({index}/{len(all_pages)}) with {MODEL}")
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            print(f"Page {numbers[index-1]} attempt {attempt+1}/4 failed: {exc}", file=sys.stderr)
            if attempt < 3:
                time.sleep(8 * (attempt + 1))
    else:
        fail(f"Failed page {numbers[index-1]} after 4 attempts: {last_error}")

OUTPUT.write_text("\n\n".join(edited_pages) + "\n", encoding="utf-8")
print(f"Created {OUTPUT}; pages={len(edited_pages)}; model={MODEL}")

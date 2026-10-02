#!/usr/bin/env python3
import json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "translations"
OUTPUT = TRANSLATIONS / "kotlovan-fa-v3-edited.txt"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
API_KEY = os.getenv("GEMINI_API_KEY")

FIRST_SOURCE = TRANSLATIONS / "kotlovan-fa-v2.txt"
EXTRA_SOURCES = [
    TRANSLATIONS / f"kotlovan-fa-v2-pages-{a}-{b}.txt"
    for a, b in [(11,15),(16,20),(21,25),(26,30),(31,35),(36,40),
                 (41,45),(46,50),(51,55),(56,60),(61,65),(66,71)]
]

PROMPT = """تو ویراستار ادبی حرفه‌ای زبان فارسی هستی و متن ترجمه‌شدهٔ رمان «گودال پی» اثر آندری پلاتونوف را برای انتشار ویرایش می‌کنی.

این متن قبلاً ترجمه شده و وظیفهٔ تو فقط ویرایش ادبی، زبانی و فنی همان ترجمه است؛ بازترجمه، خلاصه‌سازی یا تغییر محتوا ممنوع است.
هیچ جمله، پاراگراف، دیالوگ، رویداد، نام، عدد، جزئیات یا ابهامی را حذف یا اضافه نکن.
نثر ترجمه‌وار را به فارسی طبیعی، دقیق، روان و ادبی تبدیل کن، اما معنای دقیق متن موجود را حفظ کن.
لحن سرد، فلسفی، طنز تلخ و ابهام اثر را حفظ کن.
دستور زبان، نشانه‌گذاری، فاصله و نیم‌فاصله و یکدستی واژگان را اصلاح کن.
هر دیالوگ باید در یک خط فیزیکی مستقل باشد و با «— » آغاز شود؛ دیالوگ‌های پشت‌سرهم را در یک خط ادغام نکن.
نام‌ها و اصطلاحات کلیدی را تغییر نده و تا حد ممکن همان انتخاب‌های موجود در متن را حفظ کن؛ «ووشچف» را دقیقاً همین‌طور بنویس.
برچسب‌های [صفحهٔ N] را دقیقاً با همان شماره و در همان ترتیب حفظ کن.
هیچ مقدمه، توضیح، خلاصه، یادداشت ویراستار یا علامت اضافی خارج از متن نده.
فقط متن کامل ویرایش‌شدهٔ همین بخش را برگردان."""

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

def split_pages(text):
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
for source in sources:
    all_pages.extend(split_pages(source))

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

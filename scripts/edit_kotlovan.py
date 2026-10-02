#!/usr/bin/env python3
import json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"translations/kotlovan-fa-v2.txt"
OUTPUT=ROOT/"translations/kotlovan-fa-v2-edited.txt"
MODEL=os.getenv("GEMINI_MODEL","gemini-3.8-flash")
FALLBACK_MODELS=["gemini-3.8-flash","gemini-3.6-flash","gemini-3.5-flash-lite"]
API_KEY=os.getenv("GEMINI_API_KEY")
PROMPT="""تو ویراستار ادبی حرفه‌ای زبان فارسی هستی و متن ترجمه‌شدهٔ رمان «گودال پی» اثر آندری پلاتونوف را برای انتشار ویرایش می‌کنی.
وظیفه فقط ویرایش ادبی، زبانی و فنی است؛ بازترجمه یا تغییر محتوا ممنوع.
هیچ جمله، پاراگراف، دیالوگ، رویداد، نام، عدد یا جزئیات را حذف یا اضافه نکن.
نثر ترجمه‌وار را به فارسی طبیعی، دقیق، روان و ادبی تبدیل کن؛ لحن سرد، فلسفی، طنز تلخ و ابهام اثر را حفظ کن.
دستور زبان، نشانه‌گذاری، فاصله و نیم‌فاصله و یکدستی واژگان را اصلاح کن.
هر دیالوگ باید در یک خط مستقل باشد؛ دیالوگ‌های پشت‌سرهم را به هم نچسبان.
برای دیالوگ از «— » استفاده کن.
نام‌ها و اصطلاحات کلیدی را در سراسر کتاب یکسان نگه دار؛ «ووشچف» را تغییر نده.
برچسب‌های [صفحهٔ N] را دقیقاً با همان شماره و در همان نقطه حفظ کن.
هیچ مقدمه، خلاصه، توضیح ویراستار یا یادداشت اضافه نکن. فقط متن کامل ویرایش‌شده را برگردان.
"""
def fail(m): print(m,file=sys.stderr); sys.exit(1)
if not API_KEY: fail("GEMINI_API_KEY is not set.")
if not SOURCE.exists(): fail(f"Missing source: {SOURCE}")
source=SOURCE.read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")
markers=re.findall(r"^\[صفحهٔ\s*\d+\]\s*$",source,re.M)
if len(markers)<2: fail("Expected page markers were not found.")
prompt=PROMPT+"\n\nمتن زیر را کامل ویرایش کن. هیچ بخشی را خلاصه یا حذف نکن.\n\n"+source

payload={"contents":[{"role":"user","parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.2,"maxOutputTokens":65536}}
def call(model):
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json","x-goog-api-key":API_KEY},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=900) as resp: return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors="replace")
        raise RuntimeError(f"Gemini HTTP {e.code}: {body[:2000]}")
last=None
for attempt in range(4):
    try:
        model = FALLBACK_MODELS[min(attempt, len(FALLBACK_MODELS)-1)]
        response=call(model)
        parts=response.get("candidates",[{}])[0].get("content",{}).get("parts",[])
        edited="".join(p.get("text","") for p in parts).strip()
        if not edited: raise RuntimeError("Gemini returned empty output.")
        edited=re.sub(r"^```(?:text|markdown)?\s*","",edited)
        edited=re.sub(r"\s*```$","",edited).strip()
        out_markers=re.findall(r"^\[صفحهٔ\s*\d+\]\s*$",edited,re.M)
        if out_markers!=markers: raise RuntimeError(f"Page markers changed: {len(markers)} -> {len(out_markers)}")
        if len(edited)<int(len(source)*0.70): raise RuntimeError("Output is suspiciously short.")
        lines=edited.splitlines()
        cleaned=[]
        for line in lines:
            line=line.rstrip()
            if re.match(r"^\s*[–-]\s+",line): line=re.sub(r"^\s*[–-]\s*","— ",line)
            cleaned.append(line)
        edited="\n".join(cleaned).strip()+"\n"
        OUTPUT.write_text(edited,encoding="utf-8")
        print(f"Created {OUTPUT}; pages={len(markers)}; source_chars={len(source)}; edited_chars={len(edited)}; model={model}")
        break
    except Exception as e:
        last=e; print(f"Attempt {attempt+1}/4 failed: {e}",file=sys.stderr)
        if attempt<3: time.sleep(8*(attempt+1))
else: fail(f"Editing failed after 4 attempts: {last}")
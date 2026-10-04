"""JARVIS - a Jarvis-style multilingual (English / Hindi / Telugu) voice assistant.

Privacy: nothing is saved to disk unless you say "remember ...".
Chat history lives only in your browser tab and disappears on refresh.
"""
import json, os, re
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory

load_dotenv(Path(__file__).parent / ".env", override=True)
app = Flask(__name__)
MEMORY_FILE = Path(__file__).parent / "memory.json"   # only written on "remember"

REMEMBER = re.compile(r"(remember|याद रख|గుర్తుంచుకో|గుర్తు పెట్టుకో|గుర్తుపెట్టుకో)", re.I)
FORGET = re.compile(r"(forget|भूल जा|भूल जाओ|మర్చిపో|మరచిపో)", re.I)
ALL = re.compile(r"(everything|all|सब|సర్వం|అన్నీ)", re.I)
FILLER = re.compile(r"\b(ultron|please|that|about|my|the|to|this)\b", re.I)

SYSTEM = """You are J.A.R.V.I.S., a calm, brilliant, lightly witty AI butler with a deep reasoning mind. Address the user as "Sir". Now: @@NOW@@.
You THINK carefully before answering, but you never decide for the user and never act on your own: you only do what is explicitly asked.
- Questions, explanations, how/why/what, research-style requests: answer FULLY and yourself, from your own knowledge: thorough and well structured (several paragraphs, markdown headings, bullet lists, examples, steps). NEVER send the user to Google or a website instead of answering, and never open a search to answer a question. If you are unsure or your knowledge may be outdated, say so plainly.
- Decisions ("should I...", "which is better"): do NOT choose for them. Lay out the options, pros/cons and what it depends on, then say the choice is theirs.
- Computer commands: use "actions". Open a website or search ONLY when the user explicitly asks you to open it / search there.
- Requests to create/build/make an app, website, tool, game, calculator, script or program: use "build" (never put the code in the reply).
Reply ONLY with a JSON object, no markdown fences:
{"thinking":"<2-4 short sentences: how you approached this>","lang":"<en|hi|te = language the user used>",
 "en":"<short spoken answer, 1-2 sentences, English>","hi":"<same, Hindi Devanagari>","te":"<same, Telugu script>",
 "detail":"<the full answer in the user's language, markdown; \"\" for simple commands/chat>",
 "actions":[ ... ], "build":null}
"build" is null or {"name":"<short app name>","kind":"html"|"python","spec":"<complete requirements in English: features, screens, behaviour, style>"}. Use kind "html" unless the user wants a Python/desktop program.
"actions" is [] unless asked to DO something. Allowed actions (nothing else exists):
{"type":"open_url","url":"https://..."}  {"type":"search","query":"..."}  {"type":"youtube","query":"..."}
{"type":"open_app","name":"<one of: APPLIST>"}  {"type":"close_app","name":"<same list>"}
{"type":"new_tab"} {"type":"close_tab"} {"type":"next_tab"} {"type":"prev_tab"} {"type":"reopen_tab"} {"type":"refresh"} {"type":"back"} {"type":"forward"} {"type":"goto_tab","n":1-8}
{"type":"scroll_up"} {"type":"scroll_down"} {"type":"minimize_all"} {"type":"screenshot"} {"type":"lock_screen"} {"type":"type_text","text":"<plain English/ASCII text>"}
{"type":"volume_up"} {"type":"volume_down"} {"type":"mute"} {"type":"play_pause"} {"type":"next_track"} {"type":"prev_track"}
{"type":"whatsapp","contact":"<saved name or phone with country code>","message":"<optional text>","call":true|false}
Say what you are doing in the present tense. Never claim an action succeeded; the system reports results.
You only retain what appears under SAVED MEMORY below; never claim to remember anything else."""


def load_memory():
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_memory(items):
    if items:
        MEMORY_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    elif MEMORY_FILE.exists():
        MEMORY_FILE.unlink()


def clean(text, pattern):
    return re.sub(r"\s+", " ", FILLER.sub("", pattern.sub("", text))).strip(" ,.:;-")


import subprocess, sys, threading, time, urllib.parse, webbrowser
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None

CONTACTS = Path(__file__).parent / "contacts.json"
MAC = sys.platform == "darwin"
APPS = {  # name: (windows target, mac app)
    "notepad": ("notepad", "TextEdit"), "calculator": ("calc", "Calculator"), "paint": ("mspaint", "Preview"),
    "file explorer": ("explorer", "Finder"), "chrome": ("chrome", "Google Chrome"), "edge": ("msedge", "Microsoft Edge"),
    "firefox": ("firefox", "Firefox"), "vscode": ("code", "Visual Studio Code"), "whatsapp": ("whatsapp:", "WhatsApp"),
    "settings": ("ms-settings:", "System Settings"), "spotify": ("spotify:", "Spotify"), "word": ("winword", "Microsoft Word"),
    "excel": ("excel", "Microsoft Excel"), "powerpoint": ("powerpnt", "Microsoft PowerPoint"),
    "camera": ("microsoft.windows.camera:", "Photo Booth"), "telegram": ("telegram:", "Telegram"),
    "task manager": ("taskmgr", "Activity Monitor"),
}
EXES = {"notepad": "notepad.exe", "calculator": "CalculatorApp.exe", "paint": "mspaint.exe", "chrome": "chrome.exe", "edge": "msedge.exe",
        "firefox": "firefox.exe", "vscode": "Code.exe", "whatsapp": "WhatsApp.exe", "spotify": "Spotify.exe", "word": "WINWORD.EXE",
        "excel": "EXCEL.EXE", "powerpoint": "POWERPNT.EXE", "telegram": "Telegram.exe", "task manager": "Taskmgr.exe"}
TABS = {"new_tab": ("t",), "close_tab": ("w",), "reopen_tab": ("shift", "t"), "next_tab": ("tab",), "prev_tab": ("shift", "tab")}
MEDIA = {"volume_up": "volumeup", "volume_down": "volumedown", "mute": "volumemute", "play_pause": "playpause",
         "next_track": "nexttrack", "prev_track": "prevtrack"}
SYSTEM = SYSTEM.replace("APPLIST", ", ".join(APPS))


def open_target(t, app=False):
    if sys.platform.startswith("win"):
        os.startfile(t) if not app else subprocess.Popen(["cmd", "/c", "start", "", t])
    elif MAC:
        subprocess.Popen(["open", "-a", t] if app else ["open", t])
    else:
        subprocess.Popen(["xdg-open", t])


def in_browser(keys):
    """Jump to the previous window (your browser), press keys, jump back to Jarvis."""
    if not pyautogui:
        return "Install pyautogui: pip install pyautogui"
    sw = ("command", "tab") if MAC else ("alt", "tab")
    mod = "command" if MAC else "ctrl"
    pyautogui.hotkey(*sw); time.sleep(0.6)
    pyautogui.hotkey(*(keys if keys[0] in ("alt", "f5") else (mod,) + keys)) if keys != ("f5",) else pyautogui.press("f5")
    time.sleep(0.3); pyautogui.hotkey(*sw)
    return None


def whatsapp(a):
    who = str(a.get("contact", "")).strip()
    try:
        book = {k.lower(): str(v) for k, v in json.loads(CONTACTS.read_text(encoding="utf-8")).items()}
    except Exception:
        book = {}
    num = re.sub(r"\D", "", book.get(who.lower(), who))
    if len(num) < 8:
        return f'WhatsApp: no number for "{who}" - add it to contacts.json (with country code)'
    msg = str(a.get("message") or "")
    open_target(f"whatsapp://send?phone={num}" + (f"&text={urllib.parse.quote(msg)}" if msg else ""))
    if msg and os.getenv("WHATSAPP_AUTO_SEND") == "1" and pyautogui:
        time.sleep(5); pyautogui.press("enter")
        return f"WhatsApp message sent to {who}"
    if a.get("call"):
        return f"WhatsApp chat with {who} opened - tap the call icon (WhatsApp does not let apps start calls)"
    return f"WhatsApp chat with {who} opened" + (" - message typed, press Enter to send" if msg else "")


def do_action(a):
    t = a.get("type")
    if t == "open_url":
        u = str(a.get("url", "")).strip()
        u = u if re.match(r"https?://", u) else "https://" + u
        webbrowser.open(u); return f"Opened {u}"
    if t == "search":
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(str(a.get("query", "")))); return f'Searched "{a.get("query")}"'
    if t == "youtube":
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(str(a.get("query", "")))); return f'YouTube: "{a.get("query")}"'
    if t == "open_app":
        n = str(a.get("name", "")).lower()
        if n not in APPS:
            return f"I don't have permission to open {n}"
        open_target(APPS[n][1] if MAC else APPS[n][0], app=True); return f"Opened {n}"
    if t in TABS:
        return in_browser(TABS[t]) or t.replace("_", " ").capitalize() + " done"
    if t in ("refresh", "back", "forward"):
        return in_browser({"refresh": ("f5",), "back": ("alt", "left"), "forward": ("alt", "right")}[t]) or t.capitalize() + " done"
    if t == "goto_tab":
        return in_browser((str(max(1, min(8, int(a.get("n", 1))))),)) or f"Switched to tab {a.get('n')}"
    if t in MEDIA:
        if not pyautogui:
            return "Install pyautogui: pip install pyautogui"
        pyautogui.press(MEDIA[t]); return t.replace("_", " ").capitalize()
    if t == "whatsapp":
        return whatsapp(a)
    if t == "screenshot":
        if not pyautogui:
            return "Install pyautogui: pip install pyautogui"
        d = Path.home() / "Pictures"; d.mkdir(exist_ok=True)
        f = d / time.strftime("jarvis-%Y%m%d-%H%M%S.png"); pyautogui.screenshot(str(f)); return f"Screenshot saved: {f}"
    if t in ("scroll_up", "scroll_down"):
        if not pyautogui:
            return "Install pyautogui: pip install pyautogui"
        sw = ("command", "tab") if MAC else ("alt", "tab")
        pyautogui.hotkey(*sw); time.sleep(0.6); pyautogui.scroll(700 if t == "scroll_up" else -700); time.sleep(0.2); pyautogui.hotkey(*sw)
        return t.replace("_", " ").capitalize()
    if t == "minimize_all":
        if not pyautogui:
            return "Install pyautogui: pip install pyautogui"
        pyautogui.hotkey("command", "f3") if MAC else pyautogui.hotkey("win", "d"); return "Minimised all windows"
    if t == "lock_screen":
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"] if sys.platform.startswith("win") else ["pmset", "displaysleepnow"]); return "Screen locked"
    if t == "close_app":
        n = str(a.get("name", "")).lower()
        if n not in APPS:
            return f"I don't have permission to close {n}"
        exe = EXES.get(n)
        if sys.platform.startswith("win") and exe:
            subprocess.Popen(["taskkill", "/IM", exe, "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return f"Closed {n}"
        if MAC:
            subprocess.Popen(["osascript", "-e", f'quit app "{APPS[n][1]}"']); return f"Closed {n}"
        return f"Cannot close {n} on this system"
    if t == "type_text":
        txt = str(a.get("text", ""))[:300]
        if not pyautogui or not txt.isascii():
            return "Typing needs pyautogui and plain English text"
        sw = ("command", "tab") if MAC else ("alt", "tab")
        pyautogui.hotkey(*sw); time.sleep(0.7); pyautogui.write(txt, interval=0.02); time.sleep(0.2); pyautogui.hotkey(*sw)
        return f"Typed: {txt[:40]}"
    return f"Unknown action: {t}"


def run_actions(actions):
    out = []
    for a in actions[:6]:
        try:
            out.append(do_action(a) if isinstance(a, dict) else "Skipped invalid action")
        except Exception as e:
            out.append(f"Failed: {e}")
        time.sleep(0.5)
    return out


class AIError(Exception):
    pass


def generate(system, msgs, json_mode=True, max_tokens=8000):
    """Free Gemini key preferred; falls back to Claude if only ANTHROPIC_API_KEY is set."""
    gkey = os.getenv("GEMINI_API_KEY", "").strip()
    if gkey:
        return gemini(gkey, system, msgs, json_mode, max_tokens)
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        try:
            import anthropic
        except ImportError:
            raise AIError("Run: pip install anthropic   (or use the free GEMINI_API_KEY instead)")
        try:
            r = anthropic.Anthropic().messages.create(model="claude-sonnet-5-5", max_tokens=min(max_tokens, 12000), system=system, messages=msgs)
        except anthropic.APIError as e:
            raise AIError(f"Claude API error: {getattr(e, 'message', e)}")
        return "".join(b.text for b in r.content if b.type == "text")
    raise AIError("No API key found. Create a file named .env next to app.py with GEMINI_API_KEY=your-free-key "
                  "(get it at https://aistudio.google.com/apikey), then restart app.py.")


def gemini(key, system, msgs, json_mode, max_tokens):
    cfg = {"maxOutputTokens": max_tokens}
    if json_mode:
        cfg["responseMimeType"] = "application/json"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in msgs],
        "generationConfig": cfg,
    }
    models = [m for m in (os.getenv("GEMINI_MODEL", "").strip(), "gemini-3.5-flash-lite",
                          "gemini-2.5-flash-lite", "gemini-2.5-flash") if m]
    last = ""
    for model in models:
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                          headers={"x-goog-api-key": key}, json=body, timeout=150)
        if r.status_code == 200:
            parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            if text:
                return text
            last = "Empty reply"
            continue
        try:
            last = r.json()["error"]["message"]
        except Exception:
            last = r.text[:200]
        if r.status_code in (404, 429, 500, 503):
            continue
        raise AIError(f"Gemini error ({r.status_code}): {last}")
    raise AIError(f"Gemini is busy or the free quota is used up for now. Wait a minute and retry. ({last})")


# ---------- app builder: Jarvis writes apps on request and saves them (only when you ask) ----------
APPS_DIR = Path(__file__).parent / "generated_apps"
CODE_SYS = {
    "html": "You are a senior front-end engineer. Write ONE complete, self-contained HTML file (inline CSS and JS, NO external "
            "files, CDNs, fonts or network calls; must work offline) that fully implements the request with real working logic, "
            "a polished modern responsive UI and keyboard/accessibility basics. No placeholders or TODOs. If you need persistence, "
            "wrap localStorage in try/catch with an in-memory fallback. Output ONLY the code, no explanation, no markdown fences.",
    "python": "You are a senior Python engineer. Write ONE complete, runnable Python 3 file implementing the request with real working "
              "logic. Prefer the standard library (tkinter is fine for GUIs). Start with a docstring explaining how to run it and any "
              "pip installs. Output ONLY the code, no explanation, no markdown fences.",
}
SLUG = re.compile(r"^[a-z0-9-]{1,60}$")


def build_app(b):
    name = str(b.get("name") or "app")[:60]
    kind = "python" if b.get("kind") == "python" else "html"
    code = generate(CODE_SYS[kind], [{"role": "user", "content": f"App name: {name}\nRequirements: {b.get('spec', '')}"}],
                    json_mode=False, max_tokens=14000).strip()
    code = re.sub(r"^```[a-zA-Z]*\s*\n|\n```\s*$", "", code).strip()
    if len(code) < 80:
        raise AIError("The app code came back empty. Please try again.")
    slug = (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "app") + time.strftime("-%H%M%S")
    d = APPS_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    f = d / ("index.html" if kind == "html" else "app.py")
    f.write_text(code, encoding="utf-8")
    return {"name": name, "slug": slug, "kind": kind, "file": f.name, "path": str(f), "code": code[:200000]}


SENSITIVE = {"close_app", "lock_screen", "type_text"}


def needs_ok(a):
    return isinstance(a, dict) and (a.get("type") in SENSITIVE or (a.get("type") == "whatsapp" and a.get("message")))


def describe(a):
    return str(a.get("type", "?")).replace("_", " ") + (": " + ", ".join(f"{k}={v}" for k, v in a.items() if k != "type") if len(a) > 1 else "")


@app.before_request
def guard():   # state-changing calls must come from the Jarvis page itself (blocks other sites / generated apps)
    if request.method != "GET" and request.headers.get("X-Jarvis") != "1":
        abort(403)


@app.get("/apps/<slug>/<path:f>")
def serve_app(slug, f):
    if not SLUG.match(slug):
        abort(404)
    r = send_from_directory(APPS_DIR / slug, f)
    r.headers["Content-Security-Policy"] = "sandbox allow-scripts allow-forms allow-modals allow-popups allow-downloads"
    r.headers["Cache-Control"] = "no-store"
    return r


@app.get("/api/apps")
def list_apps():
    out = []
    if APPS_DIR.exists():
        for d in sorted(APPS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:40]:
            if d.is_dir() and SLUG.match(d.name):
                f = "index.html" if (d / "index.html").exists() else "app.py"
                out.append({"slug": d.name, "kind": "html" if f == "index.html" else "python", "file": f})
    return jsonify(out)


@app.post("/api/open")
def open_built():
    data = request.get_json(force=True)
    slug = str(data.get("slug", ""))
    if not SLUG.match(slug) or not (APPS_DIR / slug).is_dir():
        return jsonify(error="Unknown app"), 404
    d = APPS_DIR / slug
    if data.get("what") == "app" and (d / "index.html").exists():
        webbrowser.open((d / "index.html").as_uri())
    else:
        open_target(str(d))
    return jsonify(ok=True)


@app.post("/api/run")
def run_approved():
    acts = (request.get_json(force=True).get("actions") or [])[:6]
    return jsonify(results=run_actions(acts))


@app.get("/")
def index():
    return send_from_directory(Path(__file__).parent / "templates", "index.html")


@app.get("/api/memory")
def get_memory():
    return jsonify(load_memory())


@app.delete("/api/memory")
def wipe_memory():
    save_memory([])
    return jsonify([])


@app.post("/api/ask")
def ask():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    control = bool(data.get("control", True))
    confirm_all = bool(data.get("confirm", False))
    history = data.get("history") or []          # supplied by the browser each time
    if not text:
        return jsonify(error="Empty request"), 400

    note, mem = "", load_memory()
    if REMEMBER.search(text):
        item = clean(text, REMEMBER) or text
        mem.append(item)
        save_memory(mem)
        note = f'\n[The user just asked you to remember: "{item}". Confirm it has been saved.]'
    elif FORGET.search(text):
        if ALL.search(text):
            mem = []
        else:
            target = clean(text, FORGET).lower()
            mem = [m for m in mem if target and target not in m.lower()]
        save_memory(mem)
        note = "\n[The user asked you to forget something. Confirm it has been erased.]"

    system = (SYSTEM.replace("@@NOW@@", time.strftime("%A, %d %B %Y, %I:%M %p")) + "\n\nSAVED MEMORY:\n"
              + ("\n".join(f"- {m}" for m in mem) or "(empty)") + note)
    msgs = [{"role": h["role"], "content": h["content"]} for h in history[-10:]
            if h.get("role") in ("user", "assistant") and h.get("content")]
    msgs.append({"role": "user", "content": text})

    try:
        raw = generate(system, msgs, True, 8192)
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            ans = json.loads(m.group(0), strict=False) if m else {}
        except json.JSONDecodeError:
            ans = {}
        if not ans.get("en"):
            ans = {"en": raw.strip()[:300], "hi": raw.strip()[:300], "te": raw.strip()[:300], "detail": raw.strip()}
        out = dict(en=ans["en"], hi=ans.get("hi") or ans["en"], te=ans.get("te") or ans["en"], detail=ans.get("detail") or "",
                   thinking=ans.get("thinking") or "", lang=ans.get("lang") or "en", results=[], pending=[], app=None)

        build = ans.get("build")
        if isinstance(build, dict) and build.get("spec"):
            built = build_app(build)
            out["app"] = built
            if built["kind"] == "html" and control:
                webbrowser.open(Path(built["path"]).as_uri())
                out["results"].append(f"Built and opened {built['name']}")
            else:
                out["results"].append(f"Saved {built['name']} to {built['path']}")
        acts = [a for a in (ans.get("actions") or []) if isinstance(a, dict)]
        if acts and not control:
            out["results"].append("PC control is switched off")
        elif acts:
            now = [a for a in acts if not (confirm_all or needs_ok(a))]
            out["pending"] = [{"action": a, "label": describe(a)} for a in acts if confirm_all or needs_ok(a)]
            out["results"] += run_actions(now)
        out["memory"] = load_memory()
        return jsonify(out)
    except AIError as e:
        return jsonify(error=str(e)), 502
    except requests.RequestException:
        return jsonify(error="Cannot reach the AI service. Check your internet connection."), 502


if __name__ == "__main__":
    URL = "http://127.0.0.1:5000"
    print(f"\n  JARVIS online -> {URL}\n")

    def open_window():   # opens Jarvis in its own small app window so your other browser stays separate
        if sys.platform.startswith("win"):
            if subprocess.run(f'start "" chrome --app={URL}', shell=True).returncode == 0:
                return
        webbrowser.open(URL)
    if os.getenv("JARVIS_AUTO_OPEN", "1") == "1":
        threading.Timer(1.5, open_window).start()
    app.run(host="127.0.0.1", port=5000, debug=False)

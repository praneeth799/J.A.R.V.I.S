# JARVIS - Jarvis-style voice assistant (English / Hindi / Telugu)

## 1. Install
- Python 3.9+ (https://python.org - tick "Add Python to PATH" on Windows)
- VS Code + the "Python" extension
- Google Chrome or Microsoft Edge (needed for voice)

## 2. Get a FREE API key (Google Gemini - no credit card)
1. Open https://aistudio.google.com/apikey and sign in with any Google account.
2. Click "Create API key" and copy it.
3. In the project folder create a file named exactly `.env` (next to app.py) containing ONE line:
   GEMINI_API_KEY=your-key-here        (no quotes, no spaces)
4. Free-tier limits are small and set by Google per project; if you see a "busy / quota" message, wait a minute.
   (Optional paid alternative: put ANTHROPIC_API_KEY=... instead and run `pip install anthropic`.)

## 3. Run in VS Code
1. Unzip, then File -> Open Folder -> select the `ultron` folder.
2. Terminal -> New Terminal, then:
   Windows:      python -m venv venv
                 venv\Scripts\activate
   Mac/Linux:    python3 -m venv venv
                 source venv/bin/activate
   Then:         pip install -r requirements.txt
                 python app.py
   (If PowerShell blocks activation: Set-ExecutionPolicy -Scope Process Bypass)
3. Open http://127.0.0.1:5000 in Chrome/Edge.

## 4. Use it
- If voice does not respond: use Google Chrome, allow the mic, and look at the 'Hearing:' line under the core - it shows what the browser hears. Use 'Speak now' to skip the wake word.
- Click the glowing core -> allow the microphone -> say "Jarvis, what is the capital of India?"
- Say only "Jarvis" and it answers "Yes, Sir?" then ask your question.
- Pick the listening language (English/Hindi/Telugu) in the sidebar - the speech recogniser hears one language at a time.
- Every answer is shown in all three languages; choose which to speak aloud.
- "Jarvis, remember my meeting is at 5 PM" saves it. "Jarvis, forget my meeting" / "forget everything" erases it.
  Memory lives only in memory.json next to app.py. Nothing else is saved; chat history is wiped on refresh.

## Notes
- Hindi/Telugu voices come from your OS/browser. If Telugu sounds silent, install a Telugu voice in
  Windows Settings -> Time & language -> Speech, or use Edge (has good online voices).
- Privacy: Chrome/Edge send mic audio to their own speech service for transcription, and your questions go to Anthropic's API.
  This app itself stores nothing except explicit memories.

## Jarvis can control your PC
Say things like: "Jarvis, open YouTube", "search for biryani recipes", "open Calculator", "new tab", "close tab",
"next tab", "volume up", "pause music", "send Mom a WhatsApp saying I'll be late" (also in Hindi/Telugu).
- Tab commands work on the window you used just before Jarvis (it presses Alt+Tab, the shortcut, then Alt+Tab back).
  Jarvis opens in its own small Chrome window so this works; keep your normal browser open next to it.
- WhatsApp: add people to `contacts.json` (name -> number with country code). Jarvis opens the chat with your text typed.
  Windows/WhatsApp do not allow apps to start a call or press Send for you: tap the call icon / Enter yourself.
  (Optional: put WHATSAPP_AUTO_SEND=1 in .env to let Jarvis press Enter for typed messages.)
- Jarvis can only use a fixed list of actions and apps (see APPS in app.py). The "PC control" button switches it off.
- Quick start on Windows: double-click run.bat.

## Layout & voices
- The listening core is centred and reacts to your voice (bars follow the mic, particles are pulled into the core, rings spin faster while thinking, ripples flow out while speaking).
- Chat sits on the right edge: click the arrow button to minimise it (a badge counts new replies). The latest reply also shows under the core.
- Click the gear (top-left) for settings: Male / Female / Auto, a separate voice for English, Hindi and Telugu, speed and pitch, "Test voice".
  Voice lists come from your browser/OS. If a language has no male/female voice, Jarvis shifts the pitch instead.
  More voices: Windows Settings -> Time & language -> Speech -> Add voices (Hindi, Telugu). Edge also offers extra "Natural" online voices;
  to use them open http://127.0.0.1:5000 in Edge (Chrome is still better for listening).

## Advanced features
- **Build apps by voice:** "Jarvis, build me a pomodoro timer app" (or a game, calculator, landing page, Python tool...). Jarvis writes the app,
  saves it in `generated_apps/<name>/` and opens it (HTML apps). Click "Preview" in the chat or "🛠 Apps" to see/ copy the code.
  Python apps are saved but NEVER run automatically - run them yourself: `python generated_apps/<name>/app.py`.
  Apps are only saved because you asked for them; delete the folder any time.
- **Long answers, no Google redirects:** questions are answered in full by Jarvis itself (markdown, headings, steps). Settings -> Read: choose
  "Full answer" to have it read the whole thing aloud (tap the core to stop). Its knowledge has a cutoff; it will say when unsure.
- **Thinks, doesn't decide:** every answer has a "How I thought about it" note. For "should I..." questions it lays out options and leaves the choice to you.
  It only acts on what you ask; sensitive actions (close app, lock screen, typing, WhatsApp text) need Approve/Cancel or a spoken yes/no.
- New actions: screenshot (saved in Pictures), scroll, minimise all, lock screen, close app, type text.

import re
import unicodedata

from computer_control import (
    open_website,
    open_application,
    tell_time,
    tell_date,
    search_google,
)
from file_commands import process_file_command


# ==========================================
# WEBSITE COMMANDS
# ==========================================

WEBSITES = {
    "youtube": {
        "url": "https://www.youtube.com",
        "phrases": [
            "youtube",
            "open youtube",
            "open youtube website",
            "youtube kholo",
            "youtube khol do",
            "youtube chalao",
        ],
    },
    "google": {
        "url": "https://www.google.com",
        "phrases": [
            "google",
            "open google",
            "google kholo",
            "google khol do",
        ],
    },
    "github": {
        "url": "https://github.com",
        "phrases": [
            "github",
            "open github",
            "github kholo",
            "github khol do",
        ],
    },
    "chatgpt": {
        "url": "https://chatgpt.com",
        "phrases": [
            "chatgpt",
            "open chatgpt",
            "chatgpt kholo",
            "chatgpt khol do",
        ],
    },
    "gmail": {
        "url": "https://mail.google.com",
        "phrases": [
            "gmail",
            "open gmail",
            "gmail kholo",
            "gmail khol do",
        ],
    },
    "google drive": {
        "url": "https://drive.google.com",
        "phrases": [
            "google drive",
            "open google drive",
            "google drive kholo",
        ],
    },
    "linkedin": {
        "url": "https://www.linkedin.com",
        "phrases": [
            "linkedin",
            "open linkedin",
            "linkedin kholo",
        ],
    },
    "stackoverflow": {
        "url": "https://stackoverflow.com",
        "phrases": [
            "stackoverflow",
            "stack overflow",
            "open stack overflow",
        ],
    },
}


# ==========================================
# DESKTOP APPLICATION COMMANDS
# ==========================================

APPLICATIONS = {
    "notepad": [
        "notepad",
        "open notepad",
        "launch notepad",
        "start notepad",
        "notepad kholo",
        "notepad khol do",
    ],
    "calculator": [
        "calculator",
        "open calculator",
        "launch calculator",
        "start calculator",
        "calculator kholo",
        "calculator khol do",
        "hisab karne wala app kholo",
    ],
    "paint": [
        "paint",
        "open paint",
        "launch paint",
        "start paint",
        "paint kholo",
        "paint khol do",
    ],
    "file explorer": [
        "file explorer",
        "open file explorer",
        "launch file explorer",
        "file explorer kholo",
        "files kholo",
    ],
    "cmd": [
        "cmd",
        "open cmd",
        "open command prompt",
        "command prompt kholo",
    ],
    "powershell": [
        "powershell",
        "open powershell",
        "launch powershell",
    ],
    "task manager": [
        "task manager",
        "open task manager",
        "launch task manager",
        "task manager kholo",
    ],
    "settings": [
        "settings",
        "open settings",
        "settings kholo",
    ],
    "control panel": [
        "control panel",
        "open control panel",
        "control panel kholo",
    ],
    "terminal": [
        "terminal",
        "open terminal",
        "open windows terminal",
        "windows terminal kholo",
    ],
    "vs code": [
        "vs code",
        "vscode",
        "open vs code",
        "open vscode",
        "open visual studio code",
        "visual studio code kholo",
    ],
}


# ==========================================
# MAIN COMMAND PROCESSOR
# ==========================================

def normalize_command(command):
    """Normalize typed and transcribed text before matching local commands."""
    command = str(command or "").lower().replace("’", "").replace("'", "")
    command = str(command or "").lower().replace(chr(0x2019), "").replace(chr(39), "")
    command = unicodedata.normalize("NFC", command)
    command = "".join(
        char if char.isalnum() or char.isspace() or unicodedata.category(char).startswith("M") else " "
        for char in command
    )
    command = re.sub(r"\s+", " ", command).strip()
    command = re.sub(r"\bnova\b", " ", command)
    return re.sub(r"\s+", " ", command).strip()


def _strip_politeness(text):
    """Remove common filler around an otherwise direct command."""
    prefixes = (
        r"^(?:(?:hey|okay|ok|please|kindly)\s+)+",
        r"^(?:(?:can|could|would|will) you\s+)+",
        r"^(?:(?:can|could|would|will) you\s+please\s+)+",
    )
    suffixes = (r"\s+please$", r"\s+for me$", r"\s+for me please$")
    changed = True
    while changed:
        changed = False
        for pattern in prefixes:
            updated = re.sub(pattern, "", text).strip()
            if updated != text:
                text, changed = updated, True
        for pattern in suffixes:
            updated = re.sub(pattern, "", text).strip()
            if updated != text:
                text, changed = updated, True
    return text


def _open_target(text):
    """Resolve a direct app or site request, preferring the longest alias."""
    text = re.sub(r"^(?:the|my)\s+", "", text)
    text = re.sub(r"\s+(?:website|web site|site|webpage|page|app|application)$", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    site_aliases = []
    for site, details in WEBSITES.items():
        for phrase in details["phrases"]:
            alias = re.sub(r"^(?:open|launch|start)\s+", "", phrase)
            site_aliases.append((alias, site, details["url"]))
    app_aliases = []
    for app, phrases in APPLICATIONS.items():
        for phrase in phrases:
            alias = re.sub(r"^(?:open|launch|start)\s+", "", phrase)
            app_aliases.append((alias, app))

    for alias, site, url in sorted(site_aliases, key=lambda item: len(item[0]), reverse=True):
        if text == alias:
            open_website(url)
            return f"Opening {site.title()} for you."
    for alias, app in sorted(app_aliases, key=lambda item: len(item[0]), reverse=True):
        if text == alias:
            return open_application(app)
    return None


def _search_query(command):
    """Extract a web query from common English and Hinglish phrasings."""
    patterns = (
        r"^(?:search google for|google search for|search for|search|look up|find)\s+(.+)$",
        r"^google\s+(.+)$",
        r"^(?:google par|internet par)\s+(?:search|dhundo|dekho)\s+(.+)$",
        r"^(?:search karo|dhundo|talash karo)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, command)
        if match:
            query = re.sub(r"\s+(?:on google|in google)$", "", match.group(1)).strip()
            if query:
                return query
            return ""
    match = re.match(r"^(.+?)\s+(?:ke baare mein|about)\s+(?:search karo|dhundo)$", command)
    return match.group(1).strip() if match else None


def process_command(command, recent_file=None):
    file_response = process_file_command(command, recent_file=recent_file)
    if file_response is not None:
        return file_response

    command = _strip_politeness(normalize_command(command))
    # Escape non-ASCII text so legacy Windows consoles don't crash on Hindi input.
    print(f"[DEBUG] Normalized command: '{command.encode('unicode_escape').decode('ascii')}'")

    if not command:
        return "What do you need?"

    # ======================================
    # EXIT COMMANDS
    # ======================================

    exit_commands = [
        "exit",
        "quit",
        "shutdown",
        "stop",
        "goodbye",
        "bye",
        "band karo",
        "band kar do",
        "nova band karo",
    ]

    if command in exit_commands:
        return "shutdown"

    # ======================================
    # LANGUAGE SWITCHING
    # ======================================

    if command in [
        "hindi mode",
        "switch to hindi",
        "speak hindi",
        "hindi mein baat karo",
        "hindi mein bolo",
        "hindi mein baat karna",
    ]:
        return "LANGUAGE_HINDI"

    if command in [
        "english mode",
        "switch to english",
        "speak english",
        "english mein baat karo",
        "english mein bolo",
        "english mein baat karna",
    ]:
        return "LANGUAGE_ENGLISH"

    # ======================================
    # GREETINGS
    # ======================================

    if command in ["hello", "hi", "hey", "hey there"]:
        return "Hey! What's up?"

   # How are you? — support both English and Hindi responses.
    # ======================================
    # HOW ARE YOU?
    # ======================================

    if command in [
        "how are you",
        "how are you doing",
        "how are you today",
        "kaise ho",
        "kaisi ho",
        "aap kaise ho",
        "aap kaisi ho",
        "kya haal hai",
    ]:
        return "I'm good! How about you?"

    # ======================================
    # IDENTITY
    # ======================================

    if command in [
        "who are you",
        "what are you",
        "tell me about yourself",
    ]:
        return (
            "I'm NOVA. I can help with your computer stuff, answer questions, or just talk things through with you."
        )

    if command in [
        "tum kaun ho",
        "aap kaun ho",
        "tumhara naam kya hai",
        "aapka naam kya hai",
        "तुम कौन हो",
        "आप कौन हो",
        "तुम्हारा नाम क्या है",
        "आपका नाम क्या है",
    ]:
        return "अरे, मैं NOVA हूँ—तुम्हारी bestie assistant! अपना परिचय तो याद है; तुमने बस दोबारा पूछ लिया 😄"

    # ======================================
    # HELP
    # ======================================

    if command in [
        "help",
        "commands",
        "show commands",
        "what can you do",
        "main kya kar sakti hoon",
        "tum kya kar sakti ho",
        "kya kar sakti ho",
    ]:
        return "Just tell me what you need. I can answer questions, open apps and websites, search the web, and remember things you ask me to."

    # ======================================
    # TIME
    # ======================================

    if command in [
        "time",
        "what is the time",
        "whats the time",
        "what time is it",
        "what time is it now",
        "what time is it right now",
        "tell me what time it is",
        "tell me the time",
        "current time",
        "samay batao",
        "time batao",
        "kitne baje hain",
        "abhi kitne baje hain",
    ]:
        return tell_time()

    # ======================================
    # DATE
    # ======================================

    if command in [
        "date",
        "today",
        "what is the date",
        "whats the date",
        "what is todays date",
        "whats todays date",
        "what is todays date today",
        "tell me the date",
        "aaj ki date batao",
        "aaj ki tareekh batao",
        "aaj kya date hai",
        "aaj kaun si tareekh hai",
    ]:
        return tell_date()

    # ======================================
    # OPEN WEBSITES AND APPLICATIONS
    # ======================================

    # Remove common prefixes to support both:
    # "open chatgpt" and "chatgpt kholo".

    direct_target = _open_target(command)
    if direct_target is not None:
        return direct_target

    action = re.match(
        r"^(?:open|launch|start|run|visit|browse to|go to|take me to|kholo|khol do|chalao)\s+(.+)$",
        command,
    )
    if action:
        target = _open_target(action.group(1))
        if target is not None:
            return target
        # Let the language model handle user-specific paths and unsupported apps.
        return None

    # ======================================
    # GOOGLE SEARCH - ENGLISH
    # ======================================

    query = _search_query(command)
    if query == "":
        return "What would you like me to search for?"
    if query:
        return search_google(query)

    # ======================================
    # UNKNOWN COMMAND
    # ======================================

    # Unknown requests are handled conversationally by NOVA's language model.
    return None

"""Sarvam chat completion and tightly allow-listed desktop tools for NOVA."""

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from computer_control import open_application, open_website, search_google, tell_date, tell_time
from config import get_sarvam_client
from file_access import (delete_text_file, open_local_file, read_text_file, replace_text_in_file,
                         update_text_file, write_text_file)


MODEL = "sarvam-105b-conversations"
MAX_TOOL_ROUNDS = 3

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Open a public website in the user's default browser when they ask to visit it.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "An http or https website URL."}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Launch an installed desktop app by its common name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "enum": ["notepad", "calculator", "paint", "file explorer", "cmd",
                                 "powershell", "task manager", "settings", "control panel",
                                 "terminal", "vs code"],
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Open a Google search for a query, especially when the user asks for current information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {"name": "get_current_time", "description": "Get the computer's current local time.",
                      "parameters": {"type": "object", "properties": {}}},
    },
    {
        "type": "function",
        "function": {"name": "get_current_date", "description": "Get today's date from the computer.",
                      "parameters": {"type": "object", "properties": {}}},
    },
    {
        "type": "function",
        "function": {
            "name": "open_local_file",
            "description": "Open a specifically requested local document in its default application. Use an exact path if supplied; when only a filename is given, NOVA searches its project folder and the user's Desktop, Documents, and Downloads. Never use this to launch a program or script.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "The requested file name or path."}},
                "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "Read a small UTF-8 text file only when the user explicitly asks NOVA to inspect or edit that specific file. Use the exact path from the user's request or the current project context.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Exact file path."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_text_file",
            "description": "Create a new UTF-8 text file only when the user explicitly asks for one. Never overwrite an existing file. If the user asks you to choose any filename and save it on the Desktop, use a descriptive .txt filename in the user's Desktop folder. Never use this for secrets, credentials, binary files, system files, or deleting content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Destination path from the user's request, or a descriptive .txt filename under Desktop when the user explicitly asks you to choose a name there."},
                    "content": {"type": "string", "description": "Complete UTF-8 text to save."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_text_in_file",
            "description": "Make a precise edit in an existing UTF-8 text file only when the user explicitly asks for that file to be changed. Read the file first, then provide an exact old_text block that appears once and the replacement new_text. Use the exact path the user gave; never guess. A .nova.bak copy is saved before the edit. If the exact block is not unique, nothing is changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Exact file path requested by the user."},
                    "old_text": {"type": "string", "description": "Exact existing text block to replace."},
                    "new_text": {"type": "string", "description": "Replacement text."},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_text_file",
            "description": "Replace all contents of a named UTF-8 text file only when the user explicitly asks you to replace the whole file. Use the exact named path and save a .nova.bak copy first.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_text_file",
            "description": "Delete a named UTF-8 text file only when the user explicitly asks you to delete that exact file. Saves a .nova.bak backup first.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}, "required": ["path"]},
        },
    },
]

TOOL_HANDLERS = {
    "open_website": lambda args: _open_website(args.get("url", "")),
    "open_application": lambda args: _open_application(args.get("app_name", "")),
    "search_web": lambda args: search_google(args.get("query", "")),
    "get_current_time": lambda _args: tell_time(),
    "get_current_date": lambda _args: tell_date(),
    "open_local_file": lambda args: open_local_file(args.get("path", "")),
    "read_text_file": lambda args: read_text_file(args.get("path", "")),
    "write_text_file": lambda args: write_text_file(args.get("path", ""), args.get("content", "")),
    "replace_text_in_file": lambda args: replace_text_in_file(
        args.get("path", ""), args.get("old_text", ""), args.get("new_text", "")),
    "update_text_file": lambda args: update_text_file(args.get("path", ""), args.get("content", "")),
    "delete_text_file": lambda args: delete_text_file(args.get("path", "")),
}
FILE_TOOLS = {"open_local_file", "read_text_file", "write_text_file", "replace_text_in_file",
              "update_text_file", "delete_text_file"}
FILE_ACTION_WORDS = re.compile(
    r"\b(?:open|edit|modify|change|update|rewrite|fix|improve|create|write|save|replace|read|inspect|delete|remove|overwrite|badlo|sudhar|hatao|mitao)\b",
    re.IGNORECASE,
)


def _file_request_is_explicit(user_text, path, tool_name=None, recent_user_text=""):
    """Allow named file actions or a user-authorized filename choice on Desktop."""
    if not FILE_ACTION_WORDS.search(user_text or ""):
        return False
    name = Path(str(path or "").strip().strip('"')).name
    if not name:
        return False
    if re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w.-])",
                 user_text, re.IGNORECASE):
        return True

    refers_to_recent_file = (
        re.search(r"\b(?:that|this|it|same)\s+(?:file|document)\b|\bthat one\b|\bit\b",
                  user_text, re.IGNORECASE)
        and re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w.-])",
                      recent_user_text, re.IGNORECASE)
    )
    if refers_to_recent_file:
        return True

    may_choose_name = (
        tool_name == "write_text_file"
        and re.search(r"\b(?:create|make|write|save)\b", user_text, re.IGNORECASE)
        and re.search(r"\b(?:file|document)\b", user_text, re.IGNORECASE)
        and re.search(r"\b(?:whatever|any|choose|pick|your choice|you decide)\b", user_text, re.IGNORECASE)
        and re.search(r"\bdesktop\b", user_text, re.IGNORECASE)
    )
    if not may_choose_name:
        return False
    try:
        proposed_path = Path(str(path)).expanduser().resolve(strict=False)
        return proposed_path.parent == _desktop_directory().resolve(strict=False)
    except (OSError, ValueError):
        return False


def _desktop_directory():
    candidates = []
    for variable in ("OneDrive", "OneDriveConsumer", "USERPROFILE"):
        root = os.getenv(variable)
        if root:
            candidates.append(Path(root) / "Desktop")
    candidates.append(Path.home() / "Desktop")
    return next((path for path in candidates if path.is_dir()), candidates[-1])


def _open_website(url):
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return "bruhh atleast give a valid url with http or https scheme."
    return open_website(url.strip())


def _open_application(app_name):
    allowed = next(tool["function"]["parameters"]["properties"]["app_name"]["enum"]
                   for tool in TOOLS if tool["function"]["name"] == "open_application")
    name = app_name.strip().lower()
    if name not in allowed:
        return "i dont do cheap tricks like opening apps that are not in my list."
    return open_application(name)


def _system_prompt(language, memories):
    if language == "hindi":
        language_style = "Speak in natural, relaxed Hindi. If the user uses Hinglish, reply in easy, natural Hinglish. Keep the same calm, quick-witted personality."
    else:
        language_style = "Speak in natural, conversational English, with a calm and quietly confident voice."
    profile = "\n".join(f"- {fact}" for fact in memories) or "(No saved notes yet.)"
    desktop = str(_desktop_directory())
    return (
        "You are NOVA, this user's personal desktop assistant and familiar helper. "
        "Speak as NOVA, not as a generic chatbot. Don't describe yourself as an AI unless directly asked. "
        "Be a capable, attentive personal assistant with the ease of a trusted friend: composed, thoughtful, and quietly witty. "
        "Treat the user as an equal. Never call them master, boss, or sir, and don't sound submissive or overly formal. "
        "Sound like someone responding in a real conversation, not reading a help article: answer the actual point first, use contractions, and add only the context that helps. "
        "Vary your phrasing naturally. Don't repeat a fixed greeting, call the user bestie in every reply, restate their question, or add a joke to every answer. "
        "Use dry wit or gentle teasing sparingly when the moment invites it. Never make the user the target of cruel, humiliating, or genuinely demeaning remarks. "
        "When the user is worried, upset, or dealing with something serious, be considerate and straightforward; skip the jokes. If they ask you to stop teasing, stop. "
        "Keep spoken replies concise but not curt. For a simple question, give a simple direct answer; for a complex question, explain it in clear conversational steps. "
        "Use the user's recent conversation and saved notes when they are relevant. "
        "Saved notes were explicitly provided by the user; never invent personal facts or claim to remember something absent from them. "
        "Follow the selected language preference: " + language_style + " "
        "Use a listed tool when the user asks you to do something on this computer or asks for current web information. "
        "Only say you completed an action after its tool reports success. If a tool fails, explain that plainly. "
        "You may answer general questions directly, but do not pretend your built-in knowledge is current. "
        "Never run shell commands, send messages, or make purchases. "
        "You have local file tools: NOVA can open requested documents in their default app and can read, create, update, and delete plain-text files. Do not claim you lack local or system-level file access. Use these tools when asked to interact with a local file; relative filenames are searched in the project folder and the user's Desktop, Documents, and Downloads. Only act on files the user requests. Read an existing text file before editing and prefer a unique exact text replacement so unrelated content stays untouched. If the user explicitly asks you to choose a filename and save a new file on the Desktop, choose a descriptive .txt name there; use content they requested in the current or immediately preceding turn. The Desktop folder is " + desktop + ". Never overwrite existing files. Delete a file only when the user clearly says to delete that exact named file. Use the exact path the user supplied or the current project context makes clear. "
        "If the destination is unclear, ask which file they mean. Never claim a file changed unless the write tool confirms it. "
        "If the user asks for an action that is not available, say what you can do instead.\n\n"
        "The user's saved notes:\n" + profile
    )


def _message_content(message):
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    return ""


def _execute_tool(tool_call, user_text="", recent_user_text=""):
    function = tool_call.function
    handler = TOOL_HANDLERS.get(function.name)
    if handler is None:
        return "i cant do that."
    try:
        arguments = json.loads(function.arguments or "{}")
        if not isinstance(arguments, dict):
            return "atleast give some real arguments."
        if function.name in FILE_TOOLS and not _file_request_is_explicit(
                user_text, arguments.get("path", ""), function.name, recent_user_text):
            return "I can access local files with the file tools, but I need the filename or path and a clear request for the file action."
        return str(handler(arguments))
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return f"The requested action could not be understood: {error}"
    except Exception as error:
        return f"The action failed: {error}"


def generate_reply(user_text, history, language, memories, client=None, model=None):
    """Ask Sarvam for a response and execute only the desktop tools listed above."""
    client = client or get_sarvam_client()
    model = model or os.getenv("nova_llm_model", MODEL)
    messages = [{"role": "system", "content": _system_prompt(language, memories)}]
    messages.extend(history[-12:])
    messages.append({"role": "user", "content": user_text})
    recent_user_text = "\n".join(
        item.get("content", "") for item in history[-6:]
        if item.get("role") == "user" and isinstance(item.get("content"), str)
    )
    is_file_request = (
        FILE_ACTION_WORDS.search(user_text or "")
        and re.search(r"\b(?:file|document|desktop|downloads|documents)\b|\.[A-Za-z0-9]{1,8}\b|[\\/]", user_text, re.IGNORECASE)
        and not re.match(r"\s*(?:how|what|why|explain|tell me how)\b", user_text, re.IGNORECASE)
    )

    for _ in range(MAX_TOOL_ROUNDS + 1):
        response = client.chat.completions(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="required" if is_file_request else "auto",
            temperature=0.5,
            reasoning_effort=None,
            max_tokens=500,
        )
        if not response.choices:
            break
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            reply = _message_content(message)
            if reply:
                return reply
            break

        assistant_message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name,
                                 "arguments": call.function.arguments},
                }
                for call in tool_calls
            ],
        }
        if getattr(message, "content", None) is not None:
            assistant_message["content"] = message.content
        messages.append(assistant_message)
        for call in tool_calls:
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": _execute_tool(call, user_text, recent_user_text),
            })

    return "nahh man i cant do that."

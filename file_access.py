"""Careful text-file access for actions the user explicitly requests."""

import os
import shutil
import tempfile
from pathlib import Path

from config import BASE_DIR


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_READ_CHARS = 40_000
SENSITIVE_NAMES = {".env", ".env.local", "credentials", "secrets", "id_rsa"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".kdbx"}
EXECUTABLE_SUFFIXES = {".exe", ".com", ".bat", ".cmd", ".ps1", ".msi",
                       ".dll", ".scr", ".vbs", ".js", ".jar", ".py",
                       ".hta", ".wsf", ".lnk", ".reg"}


def _user_folders():
    roots = [Path.home()]
    for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial", "USERPROFILE"):
        value = os.environ.get(variable)
        if value:
            roots.append(Path(value))
    folders = [BASE_DIR]
    for root in roots:
        folders.extend(root / name for name in ("Desktop", "Documents", "Downloads"))
    unique = []
    seen = set()
    for folder in folders:
        resolved = folder.resolve(strict=False)
        key = str(resolved).casefold()
        if key not in seen and resolved.is_dir():
            seen.add(key)
            unique.append(resolved)
    return unique


def _resolve_user_file(path, for_creation=False):
    raw = str(path or "").strip().strip('"')
    if not raw:
        raise ValueError("Tell me the file's path first.")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        parts = candidate.parts
        relative_candidates = []
        # A path such as Desktop/report.txt is relative to the user's profile.
        if parts and parts[0].lower() in {"desktop", "documents", "downloads"}:
            relative_candidates.extend(root / candidate for root in (Path.home(), *[
                Path(os.environ[key]) for key in ("OneDrive", "OneDriveConsumer", "USERPROFILE")
                if os.environ.get(key)
            ]))
        elif len(parts) > 1:
            relative_candidates.extend(folder / candidate for folder in (Path.home(), BASE_DIR))
        else:
            relative_candidates.extend(folder / candidate for folder in _user_folders())

        existing = [item.resolve(strict=False) for item in relative_candidates if item.is_file()]
        if len(existing) > 1:
            paths = "; ".join(str(item) for item in existing[:5])
            raise ValueError(f"I found more than one file named {candidate.name}: {paths}. Tell me which path to use.")
        if existing:
            candidate = existing[0]
        elif for_creation and len(parts) == 1:
            candidate = next((folder / candidate for folder in _user_folders()
                              if folder.name.lower() == "desktop"),
                             Path.home() / "Desktop" / candidate)
        elif relative_candidates:
            candidate = relative_candidates[0]
    target = candidate.resolve(strict=False)
    if target.name.lower() in SENSITIVE_NAMES or target.suffix.lower() in SENSITIVE_SUFFIXES:
        raise ValueError("I can't access credential or key files.")
    if not target.parent.is_dir():
        raise ValueError("That folder doesn't exist. Check the path and try again.")
    if target.exists() and not target.is_file():
        raise ValueError("That path isn't a regular file.")

    protected_roots = []
    for variable in ("WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        value = os.environ.get(variable)
        if value:
            protected_roots.append(Path(value).resolve(strict=False))
    for root in protected_roots:
        try:
            target.relative_to(root)
        except ValueError:
            continue
        raise ValueError("I can't edit files inside Windows or installed-program folders.")
    return target


def read_text_file(path):
    """Read a small UTF-8 text file for an explicitly requested edit."""
    target = _resolve_user_file(path)
    if not target.is_file():
        raise ValueError("I couldn't find that file.")
    if target.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("That file is too large for me to edit safely (limit: 2 MB).")
    try:
        with target.open("r", encoding="utf-8", newline="") as source:
            content = source.read()
    except UnicodeError as error:
        raise ValueError("That file isn't UTF-8 text, so I can't safely edit it.") from error
    if "\x00" in content:
        raise ValueError("That looks like a binary file, so I can't safely edit it.")
    if len(content) > MAX_READ_CHARS:
        raise ValueError("That file is too long for a safe edit (limit: 40,000 characters).")
    return f"Contents of {target}:\n{content}"


def write_text_file(path, content):
    """Create a new UTF-8 text file; existing files use exact replacement."""
    target = _resolve_user_file(path, for_creation=True)
    if target.exists():
        raise ValueError("That file already exists. Read it and use an exact text replacement instead.")
    text = str(content)
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_FILE_BYTES:
        raise ValueError("The updated file is too large (limit: 2 MB).")
    if b"\x00" in encoded:
        raise ValueError("That content looks binary, so I can't save it as a text file.")

    _atomic_write(target, encoded)
    return f"Created {target}."


def update_text_file(path, content):
    """Replace a file's contents with UTF-8 text after preserving a backup."""
    target = _resolve_user_file(path)
    if not target.is_file():
        raise ValueError("I couldn't find that file.")
    encoded = str(content).encode("utf-8")
    if len(encoded) > MAX_FILE_BYTES or b"\x00" in encoded:
        raise ValueError("The new content is too large or isn't plain text.")
    backup = target.with_name(target.name + ".nova.bak")
    shutil.copy2(target, backup)
    _atomic_write(target, encoded)
    return f"Updated {target}. Original saved as {backup}."


def append_text_file(path, content):
    """Append UTF-8 text to an existing text file after preserving a backup."""
    target = _resolve_user_file(path)
    if not target.is_file():
        raise ValueError("I couldn't find that file.")
    original = _ensure_utf8_text(target)
    addition = str(content)
    updated = original + addition
    if len(updated.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("The updated file is too large (limit: 2 MB).")
    backup = target.with_name(target.name + ".nova.bak")
    shutil.copy2(target, backup)
    _atomic_write(target, updated.encode("utf-8"))
    return f"Added content to {target}. Original saved as {backup}."


def delete_text_file(path):
    """Delete a file only after preserving an exact backup beside it."""
    target = _resolve_user_file(path)
    if not target.is_file():
        raise ValueError("I couldn't find that file.")
    backup = target.with_name(target.name + ".nova.bak")
    shutil.copy2(target, backup)
    target.unlink()
    return f"Deleted {target}. A backup is saved as {backup}."


def open_local_file(path):
    """Open a specifically requested local document in its default application."""
    target = _resolve_user_file(path)
    if not target.is_file():
        raise ValueError("I couldn't find that file.")
    if target.suffix.lower() in EXECUTABLE_SUFFIXES:
        raise ValueError("I can't launch programs or scripts as if they were documents.")
    if os.name != "nt" or not hasattr(os, "startfile"):
        raise ValueError("Opening local files in their default app is supported on Windows.")
    os.startfile(str(target))
    return f"Opened {target} in its default app."


def replace_text_in_file(path, old_text, new_text):
    """Replace one exact text block in an existing file and retain a backup."""
    target = _resolve_user_file(path)
    if not target.is_file():
        raise ValueError("I couldn't find that file.")
    old_text = str(old_text)
    if not old_text:
        raise ValueError("I need the exact text to replace.")
    if len(str(new_text).encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("The replacement is too large (limit: 2 MB).")
    original = _ensure_utf8_text(target)
    occurrences = original.count(old_text)
    if occurrences != 1:
        raise ValueError(f"I found that text {occurrences} times. Nothing changed; give me a more specific exact section.")

    updated = original.replace(old_text, str(new_text), 1)
    backup = target.with_name(target.name + ".nova.bak")
    shutil.copy2(target, backup)
    _atomic_write(target, updated.encode("utf-8"))
    return f"Updated {target}. Original saved as {backup}."


def _ensure_utf8_text(target):
    if target.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("That file is too large for a safe edit (limit: 2 MB).")
    try:
        with target.open("r", encoding="utf-8", newline="") as source:
            content = source.read()
    except UnicodeError as error:
        raise ValueError("That file isn't UTF-8 text, so I can't safely edit it.") from error
    if "\x00" in content:
        raise ValueError("That looks like a binary file, so I can't safely edit it.")
    return content


def _atomic_write(target, encoded):
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=target.parent, prefix=".nova-",
                                         suffix=".tmp", delete=False) as temporary:
            temporary.write(encoded)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, target)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

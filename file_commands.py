"""Direct, single-command CRUD actions for explicitly named text files."""

import re

from file_access import (append_text_file, delete_text_file, open_local_file, read_text_file,
                         replace_text_in_file, update_text_file, write_text_file)


def _clean_target(value):
    value = value.strip().rstrip(".,!? ")
    value = re.sub(
        r"^(?:(?:a|an|new|the|this|my|plain[- ]text|text|notepad)\s+)*(?:file|document)\s+(?:(?:called|named)\s+)?",
        "", value, count=1, flags=re.IGNORECASE,
    )
    value = re.sub(r"^(?:called|named)\s+", "", value, count=1, flags=re.IGNORECASE)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value.strip()


def _looks_like_file(value, explicit_file_word=False):
    return explicit_file_word or bool(
        re.search(r"\.[A-Za-z0-9]{1,10}$", value.strip().strip('"\''))
        or "\\" in value or "/" in value
    )


def _file_command(text):
    text = str(text or "").strip()
    text = re.sub(r"^\s*(?:(?:hey\s+)?nova[, :]?\s*)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:(?:can|could|would|will) you\s+)?please\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:can|could|would|will) you\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+dot\s+(txt|md|py|json|csv|html|css|js|jsx|ts|tsx)\b", r".\1", text, flags=re.IGNORECASE)
    return text.strip()


def process_file_command(command, recent_file=None):
    try:
        return _process_file_command(command, recent_file)
    except (OSError, ValueError) as error:
        return f"I couldn't do that: {error}"


def _process_file_command(command, recent_file=None):
    """Run simple create/read/update/delete instructions without an LLM round trip.

    Supported examples:
      create a file named notes.txt with content Hello
      read notes.txt
      edit notes.txt replace Hello with Hi
      update notes.txt with content New contents
      delete notes.txt
    """
    text = _file_command(command)
    if recent_file and re.search(
            r"\b(?:create|make|write|save|edit|modify|change|update|rewrite|replace|set|append|add|delete|remove)\b",
            text, re.IGNORECASE):
        quoted_path = f'"{recent_file}"'
        text = re.sub(
            r"\b(?:that\s+same|the\s+same|that|this|same)\s+(?:file|document)\b|\bthat one\b",
            lambda _match: quoted_path, text, flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b((?:edit|modify|change|update|rewrite|replace|set|delete|remove|open|read)\s+)it\b",
            lambda match: match.group(1) + quoted_path, text, flags=re.IGNORECASE,
        )

    create = re.match(r"^(?:create|make|write|save)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if create:
        rest = create.group(1).strip()
        marker = re.search(r"\s+(?:(?:with|containing|and\s+(?:write|put|save))\s+(?:(?:the\s+)?(?:text|content)\s*)?(?:is\s*)?[:=]?)\s*", rest, re.IGNORECASE)
        target_source = rest[:marker.start()] if marker else rest
        content = rest[marker.end():] if marker else ""
        explicit_file_word = bool(re.search(r"\b(?:file|document)\b", target_source, re.IGNORECASE))
        target = _clean_target(target_source)
        if target and _looks_like_file(target, explicit_file_word):
            return write_text_file(target, content)

    append = re.match(
        r"^(?:append|add)\s+(.+?)\s+(?:to|onto|in|into|at\s+the\s+end\s+of)\s+(.+)$",
        text, re.IGNORECASE | re.DOTALL,
    )
    if append:
        content = append.group(1).strip()
        target_source = append.group(2).strip()
        target = _clean_target(target_source)
        explicit_file_word = bool(re.search(r"\b(?:file|document)\b", target_source, re.IGNORECASE))
        if content and target and _looks_like_file(target, explicit_file_word):
            if len(content) >= 2 and content[0] == content[-1] and content[0] in "\"'":
                content = content[1:-1]
            return append_text_file(target, content)

    # An exact phrase replacement edits only one matching occurrence and saves a backup.
    edit = re.match(r"^(?:edit|modify|change|update|rewrite|replace|set)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if edit:
        rest = edit.group(1).strip()
        replace_match = re.search(r"\s+replace\s+(.+?)\s+with\s+(.+)$", rest, re.IGNORECASE | re.DOTALL)
        if replace_match:
            target = _clean_target(rest[:replace_match.start()])
            explicit_file_word = bool(re.search(r"\b(?:file|document)\b", rest[:replace_match.start()], re.IGNORECASE))
            if _looks_like_file(target, explicit_file_word):
                old = replace_match.group(1).strip()
                new = replace_match.group(2).strip()
                old = old[1:-1] if len(old) >= 2 and old[0] == old[-1] and old[0] in "\"'" else old
                new = new[1:-1] if len(new) >= 2 and new[0] == new[-1] and new[0] in "\"'" else new
                return replace_text_in_file(target, old, new)

        # A full-content update is explicit and useful when the replacement is supplied.
        content_match = re.match(
            r"^(.+?)\s+(?:with|so\s+it\s+says?|to\s+say|to|as)\s+"
            r"(?:(?:the\s+)?(?:text|content)\s*)?(?:is\s*)?[:=]?\s*(.+)$",
            rest, re.IGNORECASE | re.DOTALL,
        )
        if content_match:
            target = _clean_target(content_match.group(1))
            explicit_file_word = bool(re.search(r"\b(?:file|document)\b", content_match.group(1), re.IGNORECASE))
            if _looks_like_file(target, explicit_file_word):
                return update_text_file(target, content_match.group(2))

    delete = re.match(r"^(?:delete|remove)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if delete:
        target_source = delete.group(1).strip()
        explicit_file_word = bool(re.search(r"\b(?:file|document)\b", target_source, re.IGNORECASE))
        target = _clean_target(target_source)
        if target and _looks_like_file(target, explicit_file_word):
            return delete_text_file(target)

    read = re.match(r"^(?:read|show|display|open)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if read:
        target_source = read.group(1).strip()
        explicit_file_word = bool(re.search(r"\b(?:file|document)\b", target_source, re.IGNORECASE))
        target = _clean_target(target_source)
        if target and _looks_like_file(target, explicit_file_word):
            if text.lower().startswith("open "):
                return open_local_file(target)
            return read_text_file(target)

    # Explicit file actions must not fall through to the language model, which
    # can claim success without touching the filesystem.
    if (re.search(r"\b(?:create|make|write|save|edit|modify|change|update|rewrite|replace|set|append|add|delete|remove)\b", text, re.IGNORECASE)
            and re.search(r"\b(?:file|document)\b|[\\/]", text, re.IGNORECASE)):
        if recent_file and re.match(r"^(?:edit|modify|change|update|rewrite|replace|set)\b", text, re.IGNORECASE):
            return f"What should I change in {recent_file}? Tell me the new content, or the exact text to replace."
        return ("I couldn't identify the file action. Try: create a file named notes.txt with content Hello; "
                "update notes.txt with content New text; edit notes.txt replace old text with new text; "
                "or delete notes.txt.")
    return None

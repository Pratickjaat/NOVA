"""Direct, single-command CRUD actions for explicitly named text files."""

import re

from file_access import (append_text_file, delete_text_file, open_local_file, read_text_file,
                         rename_text_file, replace_text_in_file, update_text_file,
                         write_text_file)


def _clean_target(value):
    value = value.strip().rstrip(".,!? ")
    value = re.sub(r"\s+please$", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(
        r"^(?:(?:me|a|an|new|another|different|the|this|my|plain[- ]text|text|txt|\.txt|notepad)\s+)*(?:file|document)\s+(?:(?:called|named)\s+)?",
        "", value, count=1, flags=re.IGNORECASE,
    )
    value = re.sub(r"^(?:called|named)\s+", "", value, count=1, flags=re.IGNORECASE)
    value = re.sub(r"\s+(?:file|document)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^(?:(?:for|to)\s+me|me|please)$", "", value, flags=re.IGNORECASE)
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
    text = re.sub(
        r"^(?:(?:okay|ok|right|wait|now|hey|nova|clear)[, :]\s*)+"
        r"(?=(?:create|make|write|save|generate|read|show|display|open|edit|modify|change|update|rewrite|replace|set|append|add|delete|remove|erase|trash|rename|you have to|you need to|i want you to)\b)",
        "", text, flags=re.IGNORECASE,
    )
    text = re.sub(r"^(?:you have to|you need to|i want you to)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*(?:(?:hey\s+)?nova[, :]?\s*)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:(?:can|could|would|will) you\s+)?please\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:can|could|would|will) you\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:please|for me|for me please)$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+dot\s+(txt|md|py|json|csv|html|css|js|jsx|ts|tsx)\b", r".\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\btx(?=\s+file\b)", "text", text, flags=re.IGNORECASE)
    # Speech recognition and natural phrasing often add a destination after
    # the filename. Keep the destination as a folder, not part of the name.
    return text.strip()


def _target_and_location(source):
    """Split a filename from a simple Desktop/Documents/Downloads location."""
    match = re.match(r"^(.*?)(?:\s+(?:on|to|in|into)\s+(?:my\s+)?(desktop|documents|downloads))$",
                    source.strip(), re.IGNORECASE)
    if not match:
        return source.strip()
    name, folder = match.groups()
    name = _clean_target(name)
    if name and not re.search(r"[\\/]", name):
        return folder + "/" + name
    return source.strip()


def process_file_command(command, recent_file=None, default_extension=""):
    try:
        return _process_file_command(command, recent_file, default_extension)
    except (OSError, ValueError) as error:
        return f"I couldn't do that: {error}"


def _process_file_command(command, recent_file=None, default_extension=""):
    """Run simple create/read/update/delete instructions without an LLM round trip.

    Supported examples:
      create a file named notes.txt with content Hello
      read notes.txt
      edit notes.txt replace Hello with Hi
      update notes.txt with content New contents
      delete notes.txt
    """
    text = _file_command(command)
    # This is a standing preference, not a request to create a strangely
    # named file. The assistant records/acknowledges it separately.
    if re.search(r"\b(?:from now on|going forward|for future files)\b", text, re.IGNORECASE):
        return None
    if recent_file and re.search(
            r"\b(?:create|make|write|save|generate|read|show|display|open|edit|modify|change|update|rewrite|replace|set|append|add|delete|remove|erase|trash|rename)\b",
            text, re.IGNORECASE):
        quoted_path = f'"{recent_file}"'
        if (re.search(r"\b(?:delete|remove|erase)\s+(?:that|this|it)(?:\s+(?:same\s+)?file)?\s*[.!?]*$",
                      text, re.IGNORECASE)
                or re.search(r"\bthe file (?:that )?you (?:have )?just created\b.*?\b(?:delete|remove)\s+(?:that|it)\s*[.!?]*$",
                             text, re.IGNORECASE)):
            text = "delete " + quoted_path

        write_to_recent = re.match(
            r"^(?:write|put|type)\s+(.+?)\s+(?:in|into|to)\s+(?:that|this|it|the same|same)(?:\s+(?:file|document))?[.!?]*$",
            text, re.IGNORECASE | re.DOTALL,
        )
        if write_to_recent:
            content = write_to_recent.group(1).strip()
            content = re.sub(r"\s+(?:in|into|to)\s+(?:this|that)\s*$", "", content,
                             flags=re.IGNORECASE).strip()
            if content:
                return update_text_file(recent_file, content)

        append_to_recent = re.match(
            r"^(?:append|add)\s+(.+?)\s+(?:to|onto|in|into)\s+(?:that|this|it|the same|same)(?:\s+(?:file|document))?[.!?]*$",
            text, re.IGNORECASE | re.DOTALL,
        )
        if append_to_recent:
            return append_text_file(recent_file, append_to_recent.group(1).strip())

        text = re.sub(
            r"\b(?:that\s+same|the\s+same|that|this|same)\s+(?:file|document)\b|\bthat one\b|\bthe file (?:that )?(?:you|i) (?:have )?just created\b",
            lambda _match: quoted_path, text, flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b((?:edit|modify|change|update|rewrite|replace|set|delete|remove|open|read|rename)\s+)it\b",
            lambda match: match.group(1) + quoted_path, text, flags=re.IGNORECASE,
        )

        backup_request = re.match(
            r"^(?:delete|remove|erase)\s+(?:the\s+)?(?:backup(?:\s+file)?|(?:its|that file's)\s+backup)(?:\s+(?:too|also|as well))?$",
            text, re.IGNORECASE,
        )
        if backup_request:
            return delete_text_file(recent_file + ".nova.bak")

        if re.match(r"^(?:delete|remove|erase)\s+(?:those|both|all)\s+files?\b", text, re.IGNORECASE):
            return f"Which file should I delete? The latest file I handled was {recent_file}."
        if re.match(r"^(?:delete|remove|erase)\s+(?:the\s+)?another\s+file\b", text, re.IGNORECASE):
            return "Which file do you mean? Please give me its name or path so I don't remove the wrong one."

        content_edit = re.match(
            r"^(?:edit|change|update)\s+(?:the\s+)?content(?:\s+(?:of\s+)?(?:the\s+)?file)?\s+"
            r"(?:and\s+)?(?:write|put|say)\s+(?:in\s+it\s+)?(?:that\s+)?(.+)$",
            text, re.IGNORECASE | re.DOTALL,
        )
        if content_edit:
            return update_text_file(recent_file, content_edit.group(1).strip())

        # A write directed into the current file changes its contents; it is
        # not a request to create a file whose name is the written sentence.
        if re.match(r"^(?:write|put|type)\s+", text, re.IGNORECASE):
            content = re.sub(
                r"\s+(?:in|into|to)\s+(?:the\s+same|that|this|same)(?:\s+(?:file|document))?(?:\s+(?:in|into|to)\s+(?:this|that))?$",
                "", text.split(None, 1)[1], flags=re.IGNORECASE,
            ).strip()
            content = re.sub(r"\s+(?:in|into|to)\s+(?:this|that)\s*$", "", content, flags=re.IGNORECASE)
            if content:
                return update_text_file(recent_file, content)

        rename = re.match(r"^rename\s+(.+?)\s+(?:to|as)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
        if rename:
            source = _clean_target(rename.group(1))
            destination = _clean_target(rename.group(2))
            if _looks_like_file(source, True) and destination:
                return rename_text_file(source, destination)
        if re.match(r"^rename\s+.+$", text, re.IGNORECASE):
            return f"What should I rename {recent_file} to?"

    if re.match(r"^write\s+(?:(?:a|an|new|plain[- ]text|text|txt)\s+)*file\b",
                text, re.IGNORECASE):
        text = re.sub(r"^write\s+", "create ", text, count=1, flags=re.IGNORECASE)

    create = re.match(r"^(?:create|make|save|generate)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if create:
        rest = create.group(1).strip()
        destination_match = re.search(
            r"\s+(?:and\s+)?(?:put|save|place)\s+it\s+(?:on|in|to)\s+(?:the\s+)?(desktop|documents|downloads)\s*[.!?]*$",
            rest, re.IGNORECASE,
        )
        requested_location = destination_match.group(1) if destination_match else ""
        if destination_match:
            rest = rest[:destination_match.start()].strip()
        marker = re.search(r"\s+(?:(?:with|containing|and\s+(?:write|put|save))\s+(?:(?:the\s+)?(?:text|content)\s*)?(?:is\s*)?[:=]?)\s*", rest, re.IGNORECASE)
        target_source = rest[:marker.start()] if marker else rest
        location_match = re.search(
            r"\s+(?:on|to|in|into)\s+(?:my\s+)?(desktop|documents|downloads)$",
            target_source, re.IGNORECASE,
        )
        location = requested_location or (location_match.group(1) if location_match else "")
        if location_match:
            target_source = target_source[:location_match.start()]
        explicit_file_word = bool(re.search(r"\b(?:file|document)\b", target_source, re.IGNORECASE))
        content = rest[marker.end():] if marker else ""
        target = _clean_target(target_source)
        if not target and explicit_file_word:
            # A generic request such as “create a text file for me” has no
            # filename. Give it a neutral, useful name instead of treating
            # “for me” or “a text file” as the literal path.
            extension = ".txt" if re.search(r"\b(?:text|txt)\s+file\b|\.txt\s+file\b", rest,
                                             re.IGNORECASE) else (default_extension or ".txt")
            target = _unused_default_name(extension, location)
        elif (target and explicit_file_word and not re.search(r"\.[A-Za-z0-9]{1,10}$", target)):
            if re.search(r"\b(?:text|txt)\s+file\b|\.txt\s+file\b", rest, re.IGNORECASE):
                target += ".txt"
            elif default_extension:
                target += default_extension
        if target and location:
            target = location + "/" + target
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

    write_into_file = re.match(
        r"^(?:write|put|type)\s+(.+?)\s+(?:in|into|to)\s+(.+)$",
        text, re.IGNORECASE | re.DOTALL,
    )
    if write_into_file:
        content = write_into_file.group(1).strip()
        target_source = write_into_file.group(2).strip()
        target = _clean_target(target_source)
        explicit_file_word = bool(re.search(r"\b(?:file|document)\b", target_source, re.IGNORECASE))
        if content and target and _looks_like_file(target, explicit_file_word):
            return update_text_file(target, content)

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

    delete = re.match(r"^(?:delete|remove|erase|trash)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if delete:
        target_source = delete.group(1).strip()
        explicit_file_word = bool(re.search(r"\b(?:file|document)\b", target_source, re.IGNORECASE))
        target_source = _target_and_location(target_source)
        target = _clean_target(target_source)
        if target and _looks_like_file(target, explicit_file_word):
            return delete_text_file(target)

    rename = re.match(r"^rename\s+(.+?)\s+(?:to|as)\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if rename:
        source = _clean_target(rename.group(1))
        destination = _clean_target(rename.group(2))
        if source and destination and _looks_like_file(source):
            return rename_text_file(source, destination)

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
    if (re.search(r"\b(?:create|make|write|save|generate|edit|modify|change|update|rewrite|replace|set|append|add|delete|remove|erase|trash|rename)\b", text, re.IGNORECASE)
            and re.search(r"\b(?:file|document)\b|[\\/]", text, re.IGNORECASE)):
        if recent_file and re.match(r"^(?:edit|modify|change|update|rewrite|replace|set)\b", text, re.IGNORECASE):
            return f"What should I change in {recent_file}? Tell me the new content, or the exact text to replace."
        return ("I couldn't identify the file action. Try: create a file named notes.txt with content Hello; "
                "update notes.txt with content New text; edit notes.txt replace old text with new text; "
                "or delete notes.txt.")
    return None


def _unused_default_name(extension, location=""):
    """Choose a non-overwriting neutral name for an unnamed new file."""
    from file_access import _resolve_user_file

    stem = "new_file"
    index = 1
    while True:
        name = f"{stem}{'' if index == 1 else f'_{index}'}{extension}"
        try:
            candidate_path = f"{location}/{name}" if location else name
            candidate = _resolve_user_file(candidate_path, for_creation=True)
            if candidate.exists():
                index += 1
                continue
        except ValueError as error:
            # _resolve_user_file resolves a future creation path without
            # creating it; return the first safe candidate.
            if "more than one file" in str(error).lower():
                index += 1
                continue
        return name

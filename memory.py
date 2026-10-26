"""Small, local store for facts the user explicitly asks NOVA to remember."""

import json
import threading

from config import MEMORY_FILE


class PersonalMemory:
    def __init__(self, path=MEMORY_FILE):
        self.path = path
        self._lock = threading.Lock()

    def all(self):
        with self._lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                return []
            except (OSError, json.JSONDecodeError):
                return []
            facts = data.get("facts", []) if isinstance(data, dict) else []
            return [fact for fact in facts if isinstance(fact, str) and fact.strip()]

    def remember(self, fact):
        fact = " ".join(fact.strip().split())
        if not fact:
            return False
        with self._lock:
            facts = self._read_unlocked()
            if fact.casefold() not in {saved.casefold() for saved in facts}:
                facts.append(fact)
            self._write_unlocked(facts[-100:])
        return True

    def forget(self, fact=None):
        with self._lock:
            if fact is None:
                self._write_unlocked([])
                return True
            target = " ".join(fact.strip().split()).casefold()
            facts = self._read_unlocked()
            remaining = [saved for saved in facts if saved.casefold() != target]
            if len(remaining) == len(facts):
                return False
            self._write_unlocked(remaining)
            return True

    def _read_unlocked(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            facts = data.get("facts", []) if isinstance(data, dict) else []
            return [fact for fact in facts if isinstance(fact, str) and fact.strip()]
        except (OSError, json.JSONDecodeError):
            return []

    def _write_unlocked(self, facts):
        self.path.write_text(
            json.dumps({"facts": facts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

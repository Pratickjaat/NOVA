"""Small local store for recent conversation context across NOVA restarts."""

import json
import sqlite3
import threading
from contextlib import contextmanager

from config import CHAT_DATABASE


class ChatStore:
    def __init__(self, path=CHAT_DATABASE, limit=200):
        self.path = path
        self.limit = limit
        self._lock = threading.Lock()
        with self._database() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS chat_turns ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)"
            )

    def load(self):
        with self._lock, self._database() as connection:
            rows = connection.execute(
                "SELECT payload FROM chat_turns ORDER BY id DESC LIMIT ?",
                (self.limit * 2,),
            ).fetchall()
        messages = []
        for (payload,) in reversed(rows):
            try:
                item = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                continue
            if (isinstance(item, dict) and item.get("role") in {"user", "assistant"}
                    and isinstance(item.get("content"), str)):
                messages.append(item)
        return messages

    def append(self, user_text, assistant_text):
        rows = [
            json.dumps({"role": "user", "content": user_text}, ensure_ascii=False),
            json.dumps({"role": "assistant", "content": assistant_text}, ensure_ascii=False),
        ]
        with self._lock, self._database() as connection:
            connection.executemany("INSERT INTO chat_turns(payload) VALUES (?)", [(row,) for row in rows])
            connection.execute(
                "DELETE FROM chat_turns WHERE id NOT IN "
                "(SELECT id FROM chat_turns ORDER BY id DESC LIMIT ?)",
                (self.limit * 2,),
            )

    def clear(self):
        with self._lock, self._database() as connection:
            connection.execute("DELETE FROM chat_turns")

    @contextmanager
    def _database(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

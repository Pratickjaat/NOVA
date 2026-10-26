"""Best-effort bridge from NOVA to the optional Java conversation history app."""

import os
import threading
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def save_conversation_entry(speaker, message):
    """Send one message to the Java Servlet endpoint without blocking NOVA."""
    endpoint = os.getenv(
        "NOVA_HISTORY_URL", "http://localhost:8080/nova-history/api/history"
    ).strip()
    if not endpoint or not message:
        return
    body = urlencode({"speaker": speaker, "message": message}).encode("utf-8")
    request = Request(endpoint, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }, method="POST")

    def send():
        try:
            with urlopen(request, timeout=3) as response:
                if response.status not in (200, 201):
                    print(f"NOVA history service returned HTTP {response.status}")
        except Exception as error:
            print(f"NOVA history entry was not saved: {error}")

    threading.Thread(target=send, daemon=True).start()

"""Shared NOVA paths and lazily initialized Sarvam client."""

import os
import threading
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LANGUAGE_FILE = BASE_DIR / "nova_language.json"
MEMORY_FILE = BASE_DIR / "nova_memory.json"
VOSK_MODEL_PATH = BASE_DIR / "models" / "vosk-model-small-en-us-0.15"

_client = None
_client_lock = threading.Lock()


def get_sarvam_client():
    """Load credentials only when a Sarvam operation is requested."""
    global _client
    if _client is not None:
        return _client

    with _client_lock:
        if _client is not None:
            return _client

        try:
            from dotenv import load_dotenv
            from sarvamai import SarvamAI
        except ImportError as error:
            raise RuntimeError(
                "Sarvam services require the packages in requirements.txt."
            ) from error

        load_dotenv(BASE_DIR / ".env")
        api_key = os.getenv("sarvam_api")
        if not api_key:
            raise RuntimeError(
                "Sarvam API key is missing. Add sarvam_api to the project .env file."
            )

        _client = SarvamAI(api_subscription_key=api_key)
        return _client

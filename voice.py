"""Sarvam text-to-speech with the NOVA voice configuration."""

import os
import re
import tempfile
import threading
from urllib.parse import urlsplit

import sounddevice as sd
import soundfile as sf

from config import get_sarvam_client
from sarvamai.play import save


FILE_EXTENSIONS = {
    ".txt": "text file", ".md": "Markdown file", ".pdf": "PDF file",
    ".docx": "Word document", ".doc": "Word document", ".csv": "CSV file",
    ".xlsx": "Excel file", ".pptx": "PowerPoint file", ".json": "JSON file",
    ".py": "Python file", ".sql": "SQL file", ".html": "HTML file",
    ".css": "CSS file", ".js": "JavaScript file",
}


def _url_for_speech(match):
    """Speak a website's host, skipping protocol, query strings, and long URLs."""
    raw = match.group(0)
    value = raw.rstrip(".,!?;:)")
    punctuation = raw[len(value):]
    try:
        host = urlsplit(value if "://" in value else "https://" + value).hostname or value
    except ValueError:
        host = value
    host = host.removeprefix("www.")
    return host.replace(".", " dot ") + punctuation


def _path_for_speech(match):
    """Read a local path as its filename, not a character-by-character address."""
    raw = match.group(0)
    path = raw.rstrip(".,!?;:)")
    punctuation = raw[len(path):]
    filename = re.split(r"[\\/]", path)[-1]
    suffix = os.path.splitext(filename)[1].lower()
    stem = filename[:-len(suffix)] if suffix else filename
    file_type = FILE_EXTENSIONS.get(suffix)
    return (f"{stem} {file_type}" if file_type else stem) + punctuation


def prepare_text_for_speech(text):
    """Make spoken replies concise around symbols, URLs, and local paths.

    The UI keeps the original response, including the exact URL or path.
    """
    spoken = str(text or "")
    # Backup paths are useful on screen but noisy when read aloud.
    spoken = re.sub(r"\. Original saved as\s+.+?\.nova\.bak\.?", ". A backup was kept.", spoken,
                    flags=re.IGNORECASE)
    spoken = re.sub(r"\. A backup is saved as\s+.+?\.nova\.bak\.?", ". A backup was kept.", spoken,
                    flags=re.IGNORECASE)
    spoken = re.sub(r"https?://[^\s<>]+|\bwww\.[^\s<>]+", _url_for_speech, spoken, flags=re.IGNORECASE)
    # Windows drive paths and ordinary slash paths; leave the full form in UI text.
    spoken = re.sub(r"\b[A-Za-z]:\\[^\s<>\"']+", _path_for_speech, spoken)
    spoken = re.sub(r"(?<![:\w])(?:\.[\\/])?(?:[\w -]+[\\/])+[\w.-]+", _path_for_speech, spoken)
    spoken = re.sub(r"`{1,3}|\*{1,2}|_{1,2}|#{1,6}", "", spoken)
    spoken = spoken.replace("&", " and ").replace("+", " plus ").replace("=", " equals ")
    spoken = spoken.replace("/", " ").replace("\\", " ")
    spoken = re.sub(r"[<>\[\]{}|~^]", " ", spoken)
    spoken = re.sub(r"\s+([,.;!?])", r"\1", spoken)
    spoken = re.sub(r"([,;:]){2,}", r"\1", spoken)
    spoken = re.sub(r"\s{2,}", " ", spoken)
    return spoken.strip()


class NOVAVoice:
    def __init__(self):
        self.model = "bulbul:v4-flash"
        self.language = "en-IN"
        self.speaker = "simran_en_customer"
        self._playback_lock = threading.Lock()
        self._stopped = threading.Event()
        self._shutdown = threading.Event()

    def set_language(self, language):
        language = language.lower().strip()
        if language in ("hindi", "hi", "hi-in"):
            self.language = "hi-IN"
            self.speaker = "simran_hi_narration"
        elif language in ("english", "en", "en-in"):
            self.language = "en-IN"
            self.speaker = "simran_en_customer"
        else:
            print("Unsupported language setting.")
            return False
        print(f"[NOVA] Language changed to {self.language}")
        return True

    def speak(self, text):
        if not text or not text.strip():
            return False

        spoken_text = prepare_text_for_speech(text)
        audio_path = None
        try:
            with self._playback_lock:
                if self._shutdown.is_set():
                    return False
                self._stopped.clear()
                audio = get_sarvam_client().text_to_speech.convert(
                    text=spoken_text,
                    model=self.model,
                    language_code=self.language,
                    speaker=self.speaker,
                )
                if self._stopped.is_set() or self._shutdown.is_set():
                    return False
                descriptor, audio_path = tempfile.mkstemp(prefix="nova_", suffix=".wav")
                os.close(descriptor)
                save(audio, audio_path)
                data, sample_rate = sf.read(audio_path)
                sd.play(data, sample_rate)
                sd.wait()
            print(f"NOVA: {spoken_text}")
            return True
        except Exception as error:
            print(f"NOVA voice error: {error}")
            return False
        finally:
            if audio_path:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

    def stop(self):
        """Stop active playback during application shutdown."""
        self._shutdown.set()
        self.interrupt()

    def interrupt(self):
        """Cancel current speech while allowing later NOVA responses to play."""
        self._stopped.set()
        try:
            sd.stop()
        except Exception as error:
            print(f"Could not stop audio playback: {error}")

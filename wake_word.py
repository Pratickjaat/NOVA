import json
import queue
import threading
from pathlib import Path

import sounddevice as sd
from vosk import Model, KaldiRecognizer

from config import VOSK_MODEL_PATH


MODEL_PATH = VOSK_MODEL_PATH

WAKE_WORDS = [
    "nova",
    "noah",
    "hey nova",
    "hey noah",
    "are you listening",
    "are you there",
    "wake up nova",
]


class WakeWordDetector:

    def __init__(self):
        print("Loading NOVA's wake-word model...")
        if not Path(MODEL_PATH).is_dir():
            raise RuntimeError(
                "Vosk model is missing. See SETUP.md for the expected model folder."
            )
        self.model = Model(str(MODEL_PATH))
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.resume_event = threading.Event()
        self.resume_event.set()

    def stop(self):
        """Ask an active wake-word wait to leave its audio stream promptly."""
        self.stop_event.set()
        self.resume_event.set()
        self.audio_queue.put(None)

    def pause(self):
        """Close wake capture temporarily so command handling can use the mic."""
        self.pause_event.set()
        self.resume_event.clear()
        self.audio_queue.put(None)

    def resume(self):
        if not self.stop_event.is_set():
            self.pause_event.clear()
            self.resume_event.set()

    def audio_callback(self, indata, frames, time, status):
        if status:
            print("Microphone status:", status)

        self.audio_queue.put(bytes(indata))

    def wait_for_wake_word(self, announce=True):

        if self.stop_event.is_set():
            return None
        if self.pause_event.is_set():
            return "__paused__"

        # Discard audio queued by the previous capture before opening a new one.
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        recognizer = KaldiRecognizer(
            self.model,
            16000,
            json.dumps(WAKE_WORDS)
        )

        if announce:
            print("\nNOVA is in standby mode.")
            print("Try saying:")
            print("- NOVA")
            print("- Hey NOVA")
            print("- Are you listening?")
            print("- Are you there?")
            print("- Wake up NOVA")
            print("Press Ctrl+C to stop.\n")

        with sd.RawInputStream(
            samplerate=16000,
            blocksize=2000,
            dtype="int16",
            channels=1,
            callback=self.audio_callback,
        ):

            while True:
                if self.stop_event.is_set():
                    return None
                if self.pause_event.is_set():
                    return "__paused__"
                try:
                    audio_data = self.audio_queue.get(timeout=0.25)
                except queue.Empty:
                    continue
                if audio_data is None or self.stop_event.is_set():
                    if self.pause_event.is_set() and not self.stop_event.is_set():
                        return "__paused__"
                    return None

                if recognizer.AcceptWaveform(audio_data):

                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower().strip()

                    if text:
                        if announce:
                            print("Recognized:", text)

                        for phrase in WAKE_WORDS:
                            if phrase in text.split() or phrase in text:
                                if announce:
                                    print("Wake phrase detected:", phrase)

                                if phrase in ["nova", "noah"]:
                                    print("NOVA: Yes, I'm listening!")

                                elif phrase in ["hey nova", "hey noah"]:
                                    print("NOVA: I'm here. Go ahead.")

                                elif phrase == "are you listening":
                                    print("NOVA: Always! What's up?")

                                elif phrase == "are you there":
                                    print("NOVA: I'm right here.")

                                elif phrase == "wake up nova":
                                    print("NOVA: I'm awake. Tell me.")

                                return phrase


if __name__ == "__main__":

    detector = WakeWordDetector()

    try:
        while True:
            detector.wait_for_wake_word()

    except KeyboardInterrupt:
        print("\nWake-word detection stopped.")

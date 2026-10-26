"""NOVA assistant orchestration shared by the desktop UI and console entrypoint."""

import json
import re
import threading

from commands import normalize_command, process_command
from config import LANGUAGE_FILE
from language_model import generate_reply
from memory import PersonalMemory
from speech import listen
from voice import NOVAVoice
from wake_word import WakeWordDetector


LANGUAGE_COMMANDS = {
    "hindi": {
        "hindi mode", "switch to hindi", "speak hindi",
        "hindi mein baat karo", "hindi mein bolo", "hindi mein baat karna",
    },
    "english": {
        "english mode", "switch to english", "speak english",
        "english mein baat karo", "english mein bolo", "english mein baat karna",
    },
}


class NOVA:
    def __init__(self):
        self.running = True
        self._shutdown_lock = threading.Lock()
        self.voice = NOVAVoice()
        self.wake_detector = WakeWordDetector()
        self.language_file = LANGUAGE_FILE
        self.language = self.load_language()
        self.voice.set_language(self.language)
        self.memory = PersonalMemory()
        self.chat_history = []
        self.awake_mode = False
        self._interrupted_command = None
        self._interrupted_command_lock = threading.Lock()

    def load_language(self):
        try:
            with self.language_file.open("r", encoding="utf-8") as file:
                language = json.load(file).get("language", "english")
            if language in ("hindi", "english"):
                print(f"[NOVA] Saved language: {language}")
                return language
        except FileNotFoundError:
            pass
        except Exception as error:
            print(f"Could not load language preference: {error}")
        return "english"

    def save_language(self):
        try:
            with self.language_file.open("w", encoding="utf-8") as file:
                json.dump({"language": self.language}, file, indent=4)
        except Exception as error:
            print(f"Could not save language preference: {error}")

    def speak(self, text, on_state=None):
        if on_state:
            on_state("SPEAKING", text)
        detector = self.wake_detector
        if (not detector or detector.pause_event.is_set() or detector.stop_event.is_set()):
            return self.voice.speak(text)

        def watch_for_barge_in():
            try:
                phrase = detector.wait_for_wake_word(announce=False)
            except Exception as error:
                print(f"Could not monitor for a speech interruption: {error}")
                return
            if not phrase or phrase == "__paused__":
                return
            self.voice.interrupt()
            if on_state:
                on_state("LISTENING", "I heard you. Go ahead.")
            try:
                command = listen(on_state=lambda state: on_state(
                    "THINKING" if state == "THINKING" else "LISTENING",
                    "Transcribing your command" if state == "THINKING" else "Listening to your command",
                ) if on_state else None)
                if command:
                    with self._interrupted_command_lock:
                        self._interrupted_command = command
            except Exception as error:
                print(f"Could not capture the interruption command: {error}")

        monitor = threading.Thread(target=watch_for_barge_in, daemon=True)
        monitor.start()
        try:
            return self.voice.speak(text)
        finally:
            # Cancel the extra wake listener once speech ends. Keep it paused if
            # the user disabled the microphone while NOVA was talking.
            already_paused = detector.pause_event.is_set()
            detector.pause()
            monitor.join()
            if not already_paused and not detector.stop_event.is_set():
                detector.resume()

    def take_interrupted_command(self):
        """Return a command captured after the user interrupted spoken output."""
        with self._interrupted_command_lock:
            command = self._interrupted_command
            self._interrupted_command = None
            return command

    def greet(self, on_state=None):
        if self.language == "hindi":
            text = "Hey, main yahin hoon. Aaj kya tackle karna hai?"
        else:
            text = "Hey, I'm here. What are we tackling today?"
        return self.speak(text, on_state)

    def acknowledge(self, on_state=None):
        text = "Haan, bolo. Main sun rahi hoon." if self.language == "hindi" else "I'm listening. Go ahead."
        return self.speak(text, on_state)

    def switch_language(self, language, announce=True, on_state=None):
        language = language.lower().strip()
        if language not in ("hindi", "english"):
            return False
        if not self.voice.set_language(language):
            return False
        self.language = language
        self.save_language()
        if announce:
            text = ("Cool, ab Hindi mein baat karte hain."
                    if language == "hindi" else
                    "Sure, English it is.")
            self.speak(text, on_state)
        return True

    def get_acknowledgement(self, command):
        """Compatibility helper for callers that want a short action preface."""
        normalized = normalize_command(command)
        websites = {"youtube": "YouTube", "google": "Google", "github": "GitHub",
                    "chatgpt": "ChatGPT", "gmail": "Gmail", "linkedin": "LinkedIn"}
        for key, name in websites.items():
            if normalized in (f"open {key}", f"open {key} website", f"launch {key}",
                              f"{key} kholo", f"{key} khol do", f"{key} chalao"):
                return f"Sure! Opening {name}." if self.language == "english" else f"Theek hai! {name} khol rahi hoon."
        applications = {"notepad": "Notepad", "calculator": "Calculator", "paint": "Paint",
                        "file explorer": "File Explorer", "cmd": "Command Prompt",
                        "powershell": "PowerShell", "task manager": "Task Manager",
                        "settings": "Settings", "control panel": "Control Panel",
                        "terminal": "Terminal", "vs code": "Visual Studio Code"}
        for key, name in applications.items():
            if normalized in (f"open {key}", f"launch {key}", f"start {key}",
                              f"{key} kholo", f"{key} khol do"):
                return f"Sure! Opening {name}." if self.language == "english" else f"Theek hai! {name} khol rahi hoon."
        return None

    def get_response(self, command):
        """Keep the existing response API available to integrations."""
        normalized = normalize_command(command)
        if normalized in {"how are you", "how are you doing", "how are you today",
                          "kaise ho", "kaisi ho", "aap kaise ho", "aap kaisi ho",
                          "kya haal hai", "कैसे हो", "कैसी हो", "आप कैसे हो",
                          "आप कैसी हो", "क्या हाल है"}:
            if self.language == "hindi":
                return "Main badhiya hoon, shukriya. Tum batao, sab theek?"
            return "Pretty good, thanks. All systems behaving themselves for once. How are you?"
        if normalized in {"namaste", "namaskar"}:
            if self.language == "hindi":
                return "Namaste! Kaise ho?"
            return "Hey! How's it going?"
        latest_assistant = next(
            (message.get("content", "") for message in reversed(self.chat_history)
             if message.get("role") == "assistant"),
            "",
        )
        if (isinstance(latest_assistant, str)
                and latest_assistant.startswith("What should I change in ")
                and self._last_file_path()
                and not re.match(r"\s*(?:what|why|how|cancel|never mind|nevermind|stop)\b", command, re.IGNORECASE)):
            # Treat the user's immediate follow-up as the content they were
            # just asked to provide (e.g. "hello world").
            return process_command(f"set it to {command}", recent_file=self._last_file_path())
        return process_command(command, recent_file=self._last_file_path())

    def _last_file_path(self):
        """Get the last path NOVA confirmed creating or changing in this chat."""
        for message in reversed(self.chat_history):
            if message.get("role") != "assistant":
                continue
            response = message.get("content", "")
            if not isinstance(response, str):
                continue
            for action in ("Created ", "Updated ", "Deleted "):
                if not response.startswith(action):
                    continue
                path = response[len(action):]
                for marker in (". Original saved as ", ". A backup is saved as "):
                    if marker in path:
                        path = path.split(marker, 1)[0]
                        break
                else:
                    path = path.rstrip(".")
                if path:
                    return path
        return None

    def handle_command(self, command, on_state=None):
        """Process a typed or recognized command through one shared route."""
        normalized = normalize_command(command)
        if normalized in {"sleep", "go to sleep", "standby", "stand by", "take a nap"}:
            self.awake_mode = False
            response = ("Theek hai, main standby mein ja rahi hoon. Jab chaho NOVA bula lena."
                        if self.language == "hindi" else
                        "Okay, I'll go to standby. Say NOVA when you're ready.")
            self.speak(response, on_state)
            self._remember_turn(command, response)
            return response
        if normalized in {"wake up", "wake up nova", "im back", "resume listening"}:
            self.awake_mode = True
            response = ("Haan, wapas aa gayi. Bolo, kya karna hai?"
                        if self.language == "hindi" else
                        "I'm back. What can I help with?")
            self.speak(response, on_state)
            self._remember_turn(command, response)
            return response
        if normalized in LANGUAGE_COMMANDS["hindi"]:
            self.switch_language("hindi", announce=True, on_state=on_state)
            return "Hindi mode enabled."
        if normalized in LANGUAGE_COMMANDS["english"]:
            self.switch_language("english", announce=True, on_state=on_state)
            return "English mode enabled."

        memory_response = self.handle_memory_request(command)
        if memory_response is not None:
            self._remember_turn(command, memory_response)
            self.speak(memory_response, on_state)
            return memory_response

        response = self.get_response(command)
        if response == "LANGUAGE_HINDI":
            self.switch_language("hindi", announce=True, on_state=on_state)
            return "Hindi mode enabled."
        if response == "LANGUAGE_ENGLISH":
            self.switch_language("english", announce=True, on_state=on_state)
            return "English mode enabled."
        if response == "shutdown":
            self.shutdown(speak=True, on_state=on_state)
            return "shutdown"
        if response is None:
            try:
                response = generate_reply(
                    user_text=command,
                    history=self.chat_history,
                    language=self.language,
                    memories=self.memory.all()[-20:],
                )
            except Exception as error:
                print(f"NOVA language model error: {error}")
                response = (
                    "bruhh, not again internet is not working?"
                    if self.language == "english" else
                    "thoda seekh ke aati hu abhi net nhi chal rha mera?"
                )
        if response:
            self.speak(response, on_state)
            self._remember_turn(command, response)
        return response

    def handle_memory_request(self, command):
        """Save or remove only details the user explicitly asks NOVA to remember."""
        normalized = normalize_command(command)
        if normalized in {
            "what do you remember about me", "what do you remember",
            "show what you remember about me", "list my memories",
            "tumhe mere baare mein kya yaad hai", "aapko mere baare mein kya yaad hai",
        }:
            facts = self.memory.all()
            if not facts:
                return "i don't have that much time."
            return "Here's what I've got: " + "; ".join(facts[:12])

        clear_phrases = {
            "forget everything you remember about me", "forget what you remember about me",
            "clear my memories", "forget all my memories", "forget everything about me",
        }
        if normalized in clear_phrases:
            self.memory.forget()
            return "done, although i dont even know you"

        remember = re.match(
            r"^(?:nova\s+)?(?:please\s+)?remember\s+(?:that\s+)?(.+)$",
            command.strip(), re.IGNORECASE,
        )
        if remember:
            fact = remember.group(1).strip()
            if fact.lower().startswith(("to ", "where i put ", "where i left ")):
                return None
            if self.memory.remember(fact):
                return f"I'll remember that: {fact}"

        forget = re.match(r"^(?:nova\s+)?(?:please\s+)?forget\s+(?:that\s+)?(.+)$",
                          command.strip(), re.IGNORECASE)
        if forget and normalized not in clear_phrases:
            fact = forget.group(1).strip()
            if self.memory.forget(fact):
                return "Got it, I forgot that note."
            return "I couldn't find that note."
        return None

    def _remember_turn(self, user_text, assistant_text):
        self.chat_history.extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ])
        self.chat_history = self.chat_history[-24:]

    def clear_chat_history(self):
        """Clear current-session context without deleting explicitly saved notes."""
        self.chat_history.clear()

    def start(self):
        print("==============================")
        print("    NOVA PERSONAL ASSISTANT")
        print("==============================")
        print("NOVA is online.")
        print("Current language:", self.language)
        print("Say 'NOVA' or another wake phrase to activate me.")
        self.greet()
        self.run()

    def run(self):
        while self.running:
            try:
                if not self.awake_mode:
                    self.wake_detector.wait_for_wake_word()
                    if not self.running:
                        break
                    self.awake_mode = True
                    self.acknowledge()
                command = listen(duration=5)
                if not command:
                    print("NOVA couldn't hear you. Returning to standby.")
                    continue
                print("You:", command)
                response = self.handle_command(command)
                if response == "shutdown":
                    break
            except KeyboardInterrupt:
                self.shutdown(speak=False)
            except Exception as error:
                print(f"NOVA command error: {error}")

    def shutdown(self, speak=True, on_state=None):
        """Stop listening and playback; optionally speak the goodbye first."""
        with self._shutdown_lock:
            first_shutdown = self.running
            self.running = False
        if not first_shutdown:
            self.voice.stop()
            return

        self.wake_detector.stop()
        if speak:
            goodbye = ("chal bhai milte h." if self.language == "hindi"
                       else "finally some peace from you.")
            self.speak(goodbye, on_state)
        self.voice.stop()
        print("NOVA is shutting down.")


if __name__ == "__main__":
    NOVA().start()

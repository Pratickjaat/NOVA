"""PySide6 bridge between NOVA's Python services and its HTML interface."""

import queue
import threading
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView


HTML_FILE = Path(__file__).with_name("frontend") / "dist" / "index.html"


class NOVABridge(QObject):
    stateChanged = Signal()
    conversationChanged = Signal()
    languageChanged = Signal()
    busyChanged = Signal()
    pageChanged = Signal()

    def __init__(self, assistant_factory=None, parent=None):
        super().__init__(parent)
        self.assistant_factory = assistant_factory
        self.assistant = None
        self.state = "STANDBY"
        self.status_message = "Starting NOVA..." if assistant_factory else "Ready when you are."
        self.busy = bool(assistant_factory)
        self.mic_enabled = False
        self.language = "English"
        self.page = "Home"
        self.conversation = []
        self.running = True
        self.events = queue.Queue()
        self._view = None

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.drain_events)
        self.timer.start()
        if assistant_factory:
            self.start_worker(self.initialize_assistant)

    @Property(str, notify=stateChanged)
    def status(self):
        return self.state

    @Property(str, notify=stateChanged)
    def statusMessage(self):
        return self.status_message

    @Property(bool, notify=busyChanged)
    def busyProperty(self):
        return self.busy

    @Property(bool, notify=stateChanged)
    def microphoneEnabled(self):
        return self.mic_enabled

    @Property(str, notify=languageChanged)
    def languageProperty(self):
        return self.language

    @Property(str, notify=pageChanged)
    def currentPage(self):
        return self.page

    @Property("QVariantList", notify=conversationChanged)
    def messages(self):
        return self.conversation

    def set_status(self, state, message=None):
        if state in {"STANDBY", "LISTENING", "THINKING", "SPEAKING"}:
            self.state = state
        if message:
            self.status_message = message
        self.stateChanged.emit()

    def start_worker(self, function, *args):
        threading.Thread(target=self.worker, args=(function, args), daemon=True).start()

    def worker(self, function, args):
        try:
            function(*args)
        except Exception as exc:
            traceback.print_exc()
            self.events.put(("error", str(exc)))
            self.events.put(("done", None))

    def initialize_assistant(self):
        self.assistant = self.assistant_factory()
        self.assistant.greet(on_state=lambda state, message: self.events.put(
            ("state", (state, message))))
        self.events.put(("ready", None))

    def wake_loop(self):
        detector = self.assistant.wake_detector
        while self.running and self.mic_enabled:
            interrupted_command = self.assistant.take_interrupted_command()
            if interrupted_command:
                self.process_command(interrupted_command)
                continue
            if not self.assistant.awake_mode:
                self.events.put(("state", ("STANDBY", "Sleeping. Say NOVA to wake me.")))
                wake = detector.wait_for_wake_word()
                if wake == "__paused__":
                    detector.resume_event.wait()
                    continue
                if wake is None or not self.running:
                    return
                self.assistant.awake_mode = True
                self.events.put(("busy", True))
                self.assistant.acknowledge(on_state=lambda state, message: self.events.put(
                    ("state", (state, message))))
            else:
                self.events.put(("state", ("LISTENING", "Listening for your next command")))
            from speech import listen
            command = listen(on_state=lambda state: self.events.put((
                "state", (state, "Transcribing your voice" if state == "THINKING"
                          else "Listening to your command"))))
            if command:
                self.process_command(command)
            else:
                self.events.put(("state", ("LISTENING", "I didn't catch that. Listening again.")))
                self.events.put(("done", None))

    def process_command(self, command):
        if not self.assistant:
            self.events.put(("error", "NOVA services are unavailable."))
            return
        try:
            self.events.put(("state", ("THINKING", "Working on that")))
            self.events.put(("user", command))
            self.save_history_entry("You", command)
            response = self.assistant.handle_command(
                command, on_state=lambda state, message: self.events.put(
                    ("state", (state, message))))
            if response == "shutdown":
                self.events.put(("reply", "NOVA is shutting down."))
                self.events.put(("shutdown", None))
                return
            if response and response not in ("LANGUAGE_HINDI", "LANGUAGE_ENGLISH"):
                self.events.put(("reply", response))
                self.save_history_entry("NOVA", response)
            if self.assistant.awake_mode:
                next_state = "LISTENING" if self.mic_enabled else "STANDBY"
                next_message = response or "Ready for your next command."
            else:
                next_state = "STANDBY"
                next_message = "Sleeping. Say NOVA when you want me again."
            self.events.put(("state", (next_state, next_message)))
        finally:
            self.events.put(("done", None))

    @staticmethod
    def save_history_entry(speaker, text):
        try:
            from conversation_history import save_conversation_entry
            save_conversation_entry(speaker, text)
        except Exception as error:
            print(f"Could not send conversation to history service: {error}")

    def drain_events(self):
        if not self.running:
            return
        changed_busy = False
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "ready":
                    self.busy = False
                    self.language = "Hindi" if self.assistant.language == "hindi" else "English"
                    self.languageChanged.emit()
                    self.mic_enabled = True
                    self.assistant.wake_detector.resume()
                    self.set_status("LISTENING", "NOVA is ready and listening for the wake phrase")
                    self.start_worker(self.wake_loop)
                    changed_busy = True
                elif kind == "busy":
                    self.busy = bool(payload)
                    changed_busy = True
                elif kind == "state":
                    self.set_status(*payload)
                elif kind == "user":
                    self.conversation.append({"speaker": "You", "text": payload})
                    self.conversationChanged.emit()
                elif kind == "reply":
                    self.conversation.append({"speaker": "NOVA", "text": payload})
                    self.conversationChanged.emit()
                elif kind == "error":
                    self.mic_enabled = False
                    self.set_status("STANDBY", f"NOVA couldn't start or process that request: {payload}")
                elif kind == "shutdown":
                    self.close()
                    return
                elif kind == "done":
                    self.busy = False
                    if self.mic_enabled and self.assistant:
                        self.assistant.wake_detector.resume()
                    changed_busy = True
                elif kind == "language":
                    self.language = payload
                    self.languageChanged.emit()
        except queue.Empty:
            pass
        if changed_busy:
            self.busyChanged.emit()

    @Slot(str)
    def submitCommand(self, text):
        text = text.strip()
        if not text or self.busy:
            return
        self.busy = True
        self.busyChanged.emit()
        if self.mic_enabled and self.assistant:
            self.assistant.wake_detector.pause()
        self.set_status("THINKING", f"You: {text}")
        self.start_worker(self.process_command, text)

    @Slot()
    def toggleMicrophone(self):
        if not self.assistant or self.busy:
            return
        self.mic_enabled = not self.mic_enabled
        if self.mic_enabled:
            self.assistant.wake_detector.resume()
            message = ("NOVA is listening for your next command" if self.assistant.awake_mode
                       else "NOVA is listening for the wake phrase")
            self.set_status("LISTENING" if self.assistant.awake_mode else "STANDBY", message)
            self.start_worker(self.wake_loop)
        else:
            self.assistant.wake_detector.pause()
            self.set_status("STANDBY", "Microphone paused. Tap the mic to resume.")
        self.stateChanged.emit()

    @Slot()
    def interruptSpeech(self):
        if not self.assistant:
            return
        self.assistant.voice.interrupt()
        self.set_status("THINKING", "Speech interrupted. NOVA is finishing the current request.")

    @Slot()
    def clearConversation(self):
        self.conversation.clear()
        if self.assistant:
            self.assistant.clear_chat_history()
        self.conversationChanged.emit()

    @Slot(str)
    def setPage(self, page):
        self.page = page
        self.pageChanged.emit()
        if page != "Home":
            self.set_status(self.state, f"{page} is ready")

    @Slot(str)
    def runQuickAction(self, action):
        self.submitCommand(action)

    @Slot()
    def toggleFullscreen(self):
        if not self._view:
            return
        if self._view.isFullScreen():
            self._view.showNormal()
        else:
            self._view.showFullScreen()

    @Slot()
    def minimizeWindow(self):
        if self._view:
            self._view.showMinimized()

    @Slot()
    def toggleWindowMaximize(self):
        if not self._view:
            return
        if self._view.isMaximized():
            self._view.showNormal()
        else:
            self._view.showMaximized()

    @Slot()
    def closeWindow(self):
        self.close()

    @Slot(int, int)
    def moveWindow(self, delta_x, delta_y):
        if self._view and not self._view.isMaximized() and not self._view.isFullScreen():
            self._view.move(self._view.x() + delta_x, self._view.y() + delta_y)

    @Slot(str, int, int)
    def resizeWindow(self, edge, delta_x, delta_y):
        if not self._view or self._view.isMaximized() or self._view.isFullScreen():
            return
        geometry = self._view.geometry()
        left, top = geometry.x(), geometry.y()
        right, bottom = left + geometry.width(), top + geometry.height()
        minimum_width, minimum_height = self._view.minimumWidth(), self._view.minimumHeight()
        if "left" in edge:
            left = min(left + delta_x, right - minimum_width)
        if "right" in edge:
            right = max(right + delta_x, left + minimum_width)
        if "top" in edge:
            top = min(top + delta_y, bottom - minimum_height)
        if "bottom" in edge:
            bottom = max(bottom + delta_y, top + minimum_height)
        self._view.setGeometry(left, top, right - left, bottom - top)

    @Slot(str)
    def setLanguage(self, language):
        if not self.assistant or self.busy:
            return
        self.busy = True
        self.busyChanged.emit()
        if self.mic_enabled:
            self.assistant.wake_detector.pause()
        self.start_worker(self.change_language_worker, language.lower())

    def change_language_worker(self, language):
        self.assistant.switch_language(
            language, on_state=lambda state, message: self.events.put(("state", (state, message))))
        self.language = language.title()
        self.events.put(("language", self.language))
        self.events.put(("state", ("LISTENING" if self.mic_enabled else "STANDBY",
                                  f"{language.title()} selected.")))
        self.events.put(("done", None))

    def close(self):
        if not self.running:
            return
        self.running = False
        self.timer.stop()
        if self.assistant:
            try:
                self.assistant.shutdown(speak=False)
            except Exception:
                pass
        if self._view:
            self._view.close()


class NOVAUI:
    def __init__(self, assistant_factory=None):
        if not HTML_FILE.is_file():
            raise RuntimeError(
                "NOVA's React interface is not built yet. Run `npm ci` and `npm run build` "
                "from the frontend folder."
            )
        self.app = QApplication.instance() or QApplication([])
        self.view = QWebEngineView()
        self.view.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.view.setWindowTitle("NOVA | Personal AI Assistant")
        self.view.setMinimumSize(1050, 680)
        available = self.app.primaryScreen().availableGeometry()
        width = min(1536, available.width())
        height = min(1024, available.height())
        self.view.resize(max(1050, width), max(680, height))
        self.view.move(
            available.x() + (available.width() - self.view.width()) // 2,
            available.y() + (available.height() - self.view.height()) // 2,
        )
        self.channel = QWebChannel(self.view.page())
        self.bridge = NOVABridge(assistant_factory)
        self.channel.registerObject("nova", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.bridge._view = self.view
        self.view.load(QUrl.fromLocalFile(str(HTML_FILE)))
        self.view.show()
        self.app.lastWindowClosed.connect(self.bridge.close)

    def run(self):
        return self.app.exec()


if __name__ == "__main__":
    NOVAUI().run()

# NOVA setup

## Requirements

- Windows with Python 3.10 or newer
- A working microphone and speakers
- A Sarvam API key for speech recognition and text-to-speech
- The Vosk English small model listed below

Create a fresh environment from the project folder in PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The interface is a React frontend hosted locally in Qt WebEngine. Install
Node.js 20 or newer, then build the bundled UI once from the project folder:

```powershell
cd frontend
npm ci
npm run build
cd ..
```

The Python install above provides NOVA's desktop host and voice dependencies.

Put the extracted Vosk model at:

```text
models/vosk-model-small-en-us-0.15/
```

Create a project `.env` file containing the Sarvam credential:

```text
sarvam_api=YOUR_SARVAM_API_KEY
nova_llm_model=sarvam-105b-conversations
```

NOVA uses Sarvam Chat Completions for open-ended conversation and natural
language requests. Recent turns and saved notes are sent to Sarvam when NOVA
needs a model response. Notes you explicitly ask NOVA to remember are kept
locally in `nova_memory.json`; chat history is kept in memory for the current
session only. The model setting is optional and defaults to
`sarvam-105b-conversations`.

For a direct file action, name the file in one command. For example: “Create a
file named notes.txt with content Hello”, “Read notes.txt”, “Edit notes.txt,
replace Hello with Hi”, “Update notes.txt with content New text”, or “Delete
notes.txt”. NOVA performs these file actions locally and replies with the
confirmed full path; if an operation fails, it reports the error instead of
claiming it succeeded. A filename without a folder is searched in the project
folder and the user's Desktop, Documents, and Downloads; newly created
relative files go to Desktop. New files can have no extension if you say
“create file xyz”. NOVA can open requested documents in their default
application. After NOVA confirms a file action, you can refer to it as “that
same file”; for example, “update that same file to say hello again”. If you
ask to update it without giving the new content, NOVA asks what to change and
uses your next reply as the new content. You can also say “set it to …” or
“append … to that same file”.
Existing files are backed up beside the original with a
`.nova.bak` suffix before updates or deletion. Credential files and files
inside Windows or installed-program folders are blocked. After the wake phrase,
NOVA says “I'm listening.”; capture ends after roughly half a second of silence,
then the UI switches to transcription while speech recognition runs.

You can ask NOVA to choose a `.txt` filename when you explicitly request a new
file on your Desktop. To edit or read a file, include its filename in your
request. While NOVA is speaking, use the stop button beside the microphone to
interrupt playback. After the first wake phrase, NOVA stays ready for the next
voice command; say “sleep” to put it back into wake phrase standby.

Keep `.env` private and do not commit it. Start NOVA with:

```powershell
python main.py
```

## Optional Java conversation history (AIP component)

The separate `java-history` web app adds a JSP conversation history page backed
by Servlets and JDBC. NOVA sends each new user message and assistant reply to
its save endpoint when the service is running. The desktop assistant continues
working if the web app or database is offline.

Requirements:

- JDK 17 or newer
- Apache Maven 3.9 or newer
- Apache Tomcat 10.1 or newer (Jakarta Servlet 6)
- MySQL 8.x

Create the database using `java-history/database.sql`. Build the app from the
`java-history` folder with `mvn clean package`, then copy
`target/nova-history.war` to Tomcat's `webapps` folder and start Tomcat. Open
`http://localhost:8080/nova-history/history` to view saved entries.

By default the Java app connects to MySQL at
`jdbc:mysql://localhost:3306/nova_history` as user `root` with an empty
password. Set `NOVA_DB_URL`, `NOVA_DB_USER`, and `NOVA_DB_PASSWORD` in the
Tomcat process environment to override these defaults. In NOVA's environment,
set `NOVA_HISTORY_URL` if the endpoint differs from
`http://localhost:8080/nova-history/api/history`.

The UI loads first. Once the backend and Vosk model load, NOVA greets you and
starts listening for the configured wake phrases. The microphone button pauses
or resumes wake-word listening.

# NOVA

NOVA is a Windows desktop voice assistant. It combines a Python backend, a
React interface hosted in a local Qt window, Vosk wake-word detection, and
Sarvam speech and language services.

## Features

- Wake-word listening and voice commands using a microphone.
- Speech recognition and spoken responses through Sarvam.
- Natural-language conversation, with recent conversation context saved locally.
- Notes you ask NOVA to remember, stored locally between runs.
- Local file commands to create, read, update, and delete files, with safeguards
  for credential files and protected Windows or installed-program locations.
- Optional Java web app for viewing conversation history.

## Requirements

- Windows
- Python 3.10 or newer
- Node.js 20 or newer (to build the desktop interface)
- A microphone and speakers
- A Sarvam API key
- The Vosk English small model, extracted to
  `models/vosk-model-small-en-us-0.15/`

The Java conversation-history component is optional. It additionally requires
JDK 17+, Maven 3.9+, Apache Tomcat 10.1+, and MySQL 8.x.

## Setup

Open PowerShell in the project folder and create the Python environment:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Build the React interface:

```powershell
cd frontend
npm ci
npm run build
cd ..
```

Download and extract the Vosk English small model into:

```text
models/vosk-model-small-en-us-0.15/
```

Create a file named `.env` in the project root and add your Sarvam key:

```dotenv
sarvam_api=YOUR_SARVAM_API_KEY
nova_llm_model=sarvam-105b-conversations
```

The model setting is optional; NOVA uses `sarvam-105b-conversations` by
default. Keep `.env` private. It is listed in `.gitignore`; never commit or
share your API key.

Start NOVA from the project root:

```powershell
python main.py
```

The interface opens first. Once the backend and Vosk model are ready, NOVA
greets you and begins listening. Use the microphone button to pause or resume
wake-word listening. After NOVA wakes, say “sleep” to return to standby.

## Local data and privacy

Conversation history and saved notes are stored on your computer in
`nova_chat.sqlite3` and `nova_memory.json`. Clearing conversation history in
the interface clears the local chat history but keeps saved notes. When NOVA
needs a model response, recent turns and saved notes are sent to Sarvam.

NOVA's file commands operate on local files. When updating or deleting an
existing file, NOVA creates a `.nova.bak` backup beside it. See
[`SETUP.md`](./SETUP.md) for additional usage details and configuration.

## Optional Java conversation history

The `java-history` application can save conversations to a MySQL database and
provide a web history page. Follow the detailed instructions in
[`SETUP.md`](./SETUP.md), including database setup and deployment to Tomcat.
The desktop assistant remains usable when this optional service is offline.

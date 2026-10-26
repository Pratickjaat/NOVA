"""Microphone recording and Sarvam speech recognition."""

import collections
import os
import tempfile

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad

from config import get_sarvam_client


SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
# End a spoken command soon after the user pauses, without waiting for a fixed
# recording length. Around half a second still filters short natural pauses.
SILENCE_DURATION = 0.45
MAX_RECORDING_SECONDS = 10
VAD_AGGRESSIVENESS = 2


def listen(duration=None, on_state=None):
    """Record speech through silence, then transcribe the temporary WAV file.

    ``duration`` remains accepted for compatibility. ``on_state`` can receive
    LISTENING and THINKING updates from callers that expose assistant status.
    """
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    frames = collections.deque()
    silence_frames = 0
    required_silence_frames = int(SILENCE_DURATION * 1000 / FRAME_DURATION_MS)
    maximum_frames = int(MAX_RECORDING_SECONDS * 1000 / FRAME_DURATION_MS)
    speech_detected = False

    if on_state:
        on_state("LISTENING")
    print("NOVA is listening... Speak now!")

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=FRAME_SIZE,
                               dtype="int16", channels=1) as stream:
            for _ in range(maximum_frames):
                audio_data, overflowed = stream.read(FRAME_SIZE)
                if overflowed:
                    print("Microphone warning: audio overflow.")
                frame = bytes(audio_data)
                if len(frame) != FRAME_SIZE * 2:
                    continue
                is_speech = vad.is_speech(frame, SAMPLE_RATE)
                frames.append(frame)
                if is_speech:
                    speech_detected = True
                    silence_frames = 0
                elif speech_detected:
                    silence_frames += 1
                if speech_detected and silence_frames >= required_silence_frames:
                    break
    except Exception as error:
        print(f"Microphone recording error: {error}")
        raise RuntimeError("Microphone recording failed. Check the input device and permissions.") from error

    if not speech_detected:
        print("No speech detected.")
        return ""

    print("Got it. Transcribing...")
    if on_state:
        on_state("THINKING")

    audio_path = None
    try:
        descriptor, audio_path = tempfile.mkstemp(prefix="nova_input_", suffix=".wav")
        os.close(descriptor)
        audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)
        sf.write(audio_path, audio_data, SAMPLE_RATE, subtype="PCM_16")
        with open(audio_path, "rb") as audio_file:
            response = get_sarvam_client().speech_to_text.transcribe(
                file=audio_file,
                model="saaras:v4",
                mode="transcribe",
            )
        transcript = response.transcript.strip()
        if transcript:
            print("You said:", transcript)
        return transcript
    except Exception as error:
        print(f"Speech recognition error: {error}")
        raise RuntimeError("Speech recognition failed. Check the Sarvam service and API key.") from error
    finally:
        if audio_path:
            try:
                os.remove(audio_path)
            except OSError:
                pass

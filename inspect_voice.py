import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("sarvam_api")
)

print("Sarvam client loaded successfully.")
print("TTS conversion method:")
import inspect
print(inspect.signature(client.text_to_speech.convert))
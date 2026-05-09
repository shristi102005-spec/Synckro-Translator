import sounddevice as sd
import queue
import json
import numpy as np
import vosk
from datetime import datetime
import pyttsx3
from deep_translator import GoogleTranslator
import os
import time

# -----------------------
# Configuration
# -----------------------
samplerate = 16000            # kept at 16 kHz as in your pasted code
q = queue.Queue()
RMS_THRESHOLD = 35          # user requested RMS threshold

CONFIG_PATH = "config.json"
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    config = {
        "speaker_index": 1,
        "earphone_index": 5,
        "default_target_lang": "en"
    }

SPEAKER_INDEX = config.get("speaker_index", 1)
EARPHONE_INDEX = config.get("earphone_index", 5)
DEFAULT_LANG = config.get("default_target_lang", "en")

# -----------------------
# Load Vosk models
# -----------------------
vosk_models = {}
try:
    vosk_models["en"] = vosk.Model("C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-en-us-0.15")
    print("✅ English model loaded")
except Exception as e:
    print("⚠️ English model not loaded:", e)

try:
    vosk_models["hi"] = vosk.Model("C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-hi-0.22")
    print("✅ Hindi model loaded")
except Exception as e:
    print("⚠️ Hindi model not loaded:", e)

# -----------------------
# Audio callback
# -----------------------
def callback(indata, frames, time_info, status):
    if status:
        print("⚠️", status)
    # Put raw bytes into queue
    q.put(bytes(indata))

# -----------------------
# TTS and translation helpers
# -----------------------
def speak_output(text, mode="broadcast"):
    engine = pyttsx3.init()
    engine.setProperty("rate", 160)
    # Route output device by setting sd.default.device for pyttsx3 to use system default
    # Note: pyttsx3 uses system TTS; switching sd.default.device helps some setups but may not affect all TTS backends.
    if mode == "broadcast":
        sd.default.device = (None, SPEAKER_INDEX)
    else:
        sd.default.device = (None, EARPHONE_INDEX)
    engine.say(text)
    engine.runAndWait()

def hybrid_translate(text, src_lang, target_lang):
    try:
        return GoogleTranslator(source=src_lang, target=target_lang).translate(text)
    except Exception as e:
        print("⚠️ Translation failed:", e)
        return None

def log_conversation(src_lang, target_lang, original, translated):
    with open("conversation_history.txt", "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{ts}] {src_lang} → {target_lang} | {original} | {translated}\n")

# -----------------------
# Safe voice selection helpers
# -----------------------
def _valid_buffer(data, min_bytes=400):
    if not data:
        return False
    if len(data) < min_bytes:
        return False
    if len(data) % 2 != 0:
        return False
    return True

def choose_mode_by_voice(recognizers, device=None, timeout_seconds=10):
    speak_output("Please say Whisper or Broadcast to choose your mode.", "whisper")
    print("🎧 Listening for mode selection...")
    start_time = time.time()

    with sd.RawInputStream(samplerate=samplerate, blocksize=4000, device=device,
                           dtype="int16", channels=1, callback=callback):
        while True:
            if time.time() - start_time > timeout_seconds:
                print("⏳ Mode selection timeout, defaulting to broadcast")
                speak_output("No response detected. Defaulting to Broadcast mode.", "whisper")
                return "broadcast"

            data = q.get()
            if not _valid_buffer(data, min_bytes=400):
                continue

            for lang, rec in recognizers.items():
                try:
                    # Prefer partial result check first for faster detection
                    partial = json.loads(rec.PartialResult())
                    p = partial.get("partial", "").lower()
                    if "whisper" in p:
                        speak_output("You are now in Whisper mode.", "whisper")
                        return "whisper"
                    if "broadcast" in p:
                        speak_output("You are now in Broadcast mode.", "whisper")
                        return "broadcast"

                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").lower()
                        if "whisper" in text:
                            speak_output("You are now in Whisper mode.", "whisper")
                            return "whisper"
                        if "broadcast" in text:
                            speak_output("You are now in Broadcast mode.", "whisper")
                            return "broadcast"
                except Exception:
                    # Skip invalid buffers or processing errors
                    continue

def choose_language_by_voice(recognizers, device=None, timeout_seconds=10):
    speak_output("Please say the target language, for example English or Hindi.", "whisper")
    print("🎧 Listening for target language...")
    lang_map = {
        "english": "en",
        "hindi": "hi",
        "german": "de",
        "french": "fr",
        "spanish": "es"
    }
    start_time = time.time()

    with sd.RawInputStream(samplerate=samplerate, blocksize=4000, device=device,
                           dtype="int16", channels=1, callback=callback):
        while True:
            if time.time() - start_time > timeout_seconds:
                print("⏳ Language selection timeout, defaulting to English")
                speak_output("No response detected. Defaulting to English.", "whisper")
                return "en"

            data = q.get()
            if not _valid_buffer(data, min_bytes=400):
                continue

            for lang, rec in recognizers.items():
                try:
                    partial = json.loads(rec.PartialResult())
                    p = partial.get("partial", "").lower()
                    for spoken, code in lang_map.items():
                        if spoken in p:
                            speak_output(f"Target language set to {spoken}.", "whisper")
                            return code

                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").lower()
                        for spoken, code in lang_map.items():
                            if spoken in text:
                                speak_output(f"Target language set to {spoken}.", "whisper")
                                return code
                except Exception:
                    continue

# -----------------------
# Main recognition loop
# -----------------------
def auto_detect_and_translate(target_code="en", mode="broadcast", timeout=10, device=None):
    if not vosk_models:
        print("❌ No models loaded.")
        return

    try:
        info = sd.query_devices(device, 'input')
        channels = info.get('max_input_channels', 1)
        print(f"🎤 Using {channels} channel(s) on {info['name']}")
    except Exception as e:
        print("⚠️ Could not query device, defaulting to 1 channel:", e)
        channels = 1

    recognizers = {lang: vosk.KaldiRecognizer(model, samplerate) for lang, model in vosk_models.items()}

    with sd.RawInputStream(samplerate=samplerate, blocksize=2000, device=device,
                           dtype="int16", channels=channels, callback=callback):
        print("🎙 Speak now... (say 'stop' to exit, 'whisper' or 'broadcast' to change mode)")
        start_time = datetime.now()
        while True:
            if (datetime.now() - start_time).seconds > timeout:
                print("⏳ Still listening...")
                start_time = datetime.now()

            data = q.get()
            if not _valid_buffer(data, min_bytes=400):
                continue

            audio_array = np.frombuffer(data, dtype=np.int16)
            if audio_array.size == 0:
                continue

            rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
            if np.isnan(rms) or rms < RMS_THRESHOLD:
                continue

            for lang, rec in recognizers.items():
                try:
                    # Final result
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").lower()
                        conf = result.get("confidence", 1.0)

                        if text.strip() and conf > 0.5:
                            # One-word voice commands
                            if "stop" in text:
                                speak_output("Stopping translation.", mode)
                                print("👋 Stopping translation.")
                                return
                            elif "whisper" in text:
                                mode = "whisper"
                                speak_output("You are now in Whisper mode.", mode)
                                continue
                            elif "broadcast" in text:
                                mode = "broadcast"
                                speak_output("You are now in Broadcast mode.", mode)
                                continue

                            # Normal final translation
                            print(f"✔ Final ({lang}, conf={conf:.2f}): {text}")
                            translated = hybrid_translate(text, lang, target_code)
                            if translated:
                                print(f"➡ Final Translation → {translated}")
                                log_conversation(lang, target_code, text, translated)
                                speak_output(translated, mode)
                    else:
                        # Partial results for live translation
                        partial = json.loads(rec.PartialResult())
                        ptext = partial.get("partial", "").lower()
                        if ptext.strip():
                            # Avoid repeating identical short partials too frequently
                            translated = hybrid_translate(ptext, lang, target_code)
                            if translated:
                                print(f"⏳ Partial: {ptext}")
                                print(f"➡ Live Translation → {translated}")
                                speak_output(translated, mode)
                except Exception:
                    # Skip problematic buffers
                    continue

# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    print("Available audio devices:")
    print(sd.query_devices())

    try:
        device_index = input("Enter microphone device index (leave blank for auto): ").strip()
        if device_index:
            device = int(device_index)
        else:
            default_input = sd.default.device[0]
            info = sd.query_devices(default_input, 'input')
            device = default_input
            print(f"🎤 Auto-selected: {info['name']} (channels={info.get('max_input_channels',1)})")
    except Exception:
        device = None

    # Build recognizers for voice selection
    recognizers = {lang: vosk.KaldiRecognizer(model, samplerate) for lang, model in vosk_models.items()}

    # Voice-based mode selection (speaks into earphone by default)
    mode = choose_mode_by_voice(recognizers, device=device)

    # Voice-based language selection
    target_code = choose_language_by_voice(recognizers, device=device)

    # Confirm and start main loop
    speak_output(f"Starting translation to {target_code}. Say stop to end.", mode)
    auto_detect_and_translate(target_code=target_code, mode=mode, device=device)

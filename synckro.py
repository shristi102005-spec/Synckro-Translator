import warnings
warnings.filterwarnings("ignore")

import os, sys, queue, vosk, sounddevice as sd, pyttsx3, json, subprocess, numpy as np
import argostranslate.package, argostranslate.translate
from deep_translator import GoogleTranslator
from datetime import datetime

# === Load Vosk Models (Offline ASR) ===
vosk_model_paths = {
    "en": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-en-us-0.15",
    "de": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-de-0.15",
    "fr": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-fr-0.22",
    "hi": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-hi-0.22",
    "es": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-es-0.42",
    "ru": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-ru-0.22",
    "ko": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-ko-0.22"
}

vosk_models = {}
for lang, path in vosk_model_paths.items():
    try:
        if os.path.exists(path):
            vosk_models[lang] = vosk.Model(path)
            print(f"✅ Loaded {lang} model")
        else:
            print(f"❌ Path not found for {lang}: {path}")
    except Exception as e:
        print(f"❌ Failed to load {lang} model: {e}")

# === Speech Recognition Setup ===
q = queue.Queue()
samplerate = 16000
device = None

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

# === Conversation Logging ===
def log_conversation(src, tgt, original, translated):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("conversation_history.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {src} → {tgt} | {original} → {translated}\n")
    print(f"💾 Saved: {original} → {translated}")

# === Audio Output ===
def speak_output(text, mode="broadcast"):
    engine = pyttsx3.init()
    if mode == "whisper":
        voices = engine.getProperty('voices')
        if len(voices) > 1:
            engine.setProperty('voice', voices[1].id)
    engine.say(text)
    engine.runAndWait()

# === Hybrid Translation ===
def ensure_argos_package(src_lang, target_lang):
    available = argostranslate.translate.get_installed_languages()
    src = next((l for l in available if l.code == src_lang), None)
    tgt = next((l for l in available if l.code == target_lang), None)
    if src and tgt:
        try:
            translation = src.get_translation(tgt)
            if translation:
                return translation
        except Exception:
            pass
    print(f"📦 Installing Argos package {src_lang}_{target_lang}...")
    subprocess.run(["argos-translate", "--install-package", f"{src_lang}_{target_lang}"])
    argostranslate.package.update_package_index()
    available = argostranslate.translate.get_installed_languages()
    src = next((l for l in available if l.code == src_lang), None)
    tgt = next((l for l in available if l.code == target_lang), None)
    return src.get_translation(tgt) if src and tgt else None

def hybrid_translate(text, src_lang, target_lang="en"):
    try:
        result = GoogleTranslator(source=src_lang, target=target_lang).translate(text)
        if result:
            print("🌐 Online translation used")
            return result
    except Exception as e:
        print("⚠️ Online translation failed:", e)

    translation = ensure_argos_package(src_lang, target_lang)
    if translation is None:
        print(f"⚠️ No Argos package for {src_lang} → {target_lang}")
        return None
    print("📦 Offline Argos translation used")
    return translation.translate(text)

# === Auto-detect with noise filter ===
def auto_detect_and_translate(target_code="en", mode="broadcast", timeout=10):
    if not vosk_models:
        print("❌ No models loaded. Please check your paths.")
        return

    recognizers = {lang: vosk.KaldiRecognizer(model, samplerate) for lang, model in vosk_models.items()}
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=device,
                           dtype="int16", channels=1, callback=callback):
        print("🎙 Speak now... (say 'exit' to stop)")
        start_time = datetime.now()
        while True:
            if (datetime.now() - start_time).seconds > timeout:
                print("⏳ Still listening... speak clearly into the mic.")
                start_time = datetime.now()

            data = q.get()
            audio_array = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array**2))
            if rms < 25:  # lowered threshold for sensitivity
                continue

            for lang, rec in recognizers.items():
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    conf = result.get("confidence", 1.0)
                    if text.strip() and conf > 0.5:
                        if text.lower() == "exit":
                            print("👋 Exiting translator.")
                            return
                        print(f"✔ Recognized ({lang}, conf={conf:.2f}): {text}")
                        translated = hybrid_translate(text, lang, target_code)
                        if translated:
                            print(f"➡ Translated → {translated}")
                            log_conversation(lang, target_code, text, translated)
                            speak_output(translated, mode)

# === Runtime Menu ===
if __name__ == "__main__":
    print("Available audio devices:")
    print(sd.query_devices())

    try:
        device_index = input("Enter microphone device index (default = None): ").strip()
        if device_index:
            device = int(device_index)
        else:
            device = None
    except Exception:
        device = None

    print("Select output mode:")
    print("1. Broadcast (speaker)")
    print("2. Whisper (earbud/headset)")
    choice = input("Enter 1 or 2: ").strip()
    mode = "broadcast" if choice == "1" else "whisper"

    print("Select target language code (default = en):")
    target_code = input("Enter code: ").strip()
    if not target_code:
        target_code = "en"

    auto_detect_and_translate(target_code, mode)








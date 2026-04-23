from vosk import Model

# List of all your model paths
vosk_model_paths = {
    "English": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-en-us-0.15",
    "German": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-de-0.15",
    "French": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-fr-0.22",
    "Hindi": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-hi-0.22",
    "Spanish": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-es-0.42",
    "Russian": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-ru-0.22",
    "Korean": "C:/Users/Acer/Desktop/Synkro_Project/vosk-model-small-ko-0.22"
}

for lang, path in vosk_model_paths.items():
    try:
        print(f"Loading {lang} model...")
        model = Model(path)
        print(f"{lang} model loaded successfully ✅\n")
    except Exception as e:
        print(f"❌ Failed to load {lang} model: {e}\n")

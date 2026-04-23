# Synckro Translator

A **Flask web application** for real-time speech translation and conversation management.  
It provides a chat-style interface with multilingual support, per-language archives, and trash/restore functionality.

---

## 🚀 Features
- Real-time speech-to-text and translation (supports multiple languages).
- Chat-style dashboard UI with cut/copy/save options.
- Language-wise folders and archives for organized conversation logs.
- Trash folder with restore and permanent delete.
- Auto-purge for deleted items after configurable days.
- Search and filter conversations by text and language code.

---

## 📦 Installation

Clone the repository:
```bash
git clone https://github.com/shristi102005-spec/Synckro-Translator.git
cd Synckro-Translator


Synckro-Translator/
│
├── dashboard.py              # Main Flask app with UI
├── synckro.py                # Core translation logic
├── test_model.py              # Model testing script
├── install_argos_models.bat.py # Helper for Argos models
├── requirements.txt           # Dependencies
└── README.md                  # Project documentation



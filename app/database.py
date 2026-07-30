import os
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

# Wskazanie pliku .env w głównym katalogu projektu
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError(
        f"Brak zmiennej MONGO_URI! Szukano w ścieżce: {ENV_PATH}."
    )

# Inicjalizacja połączenia z klientem MongoDB
client = MongoClient(MONGO_URI)

# JAWNE WSKAZANIE NAZWY BAZY DANYCH
# Dzięki temu kod zadziała niezależnie od postaci URI w pliku .env
db = client.get_database("bezpiecznik_db")

# Kolekcja dla raportów
reports_collection = db["reports"]
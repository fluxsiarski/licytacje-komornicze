import os
import requests
import hashlib

# ======= KONFIGURACJA ========
URL = "https://licytacje.komornik.pl/wyszukiwarka/obwieszczenia-o-licytacji?city=Wroc%C5%82aw&mainCategory=REAL_ESTATE"

# Dane biorę z sekretów GitHub (ustawisz je później)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Plik z hashem będzie przechowywany w folderze "cache" (który GitHub zapamięta między uruchomieniami)
HASH_FILE = "cache/last_hash.txt"

# ======= FUNKCJE ========
def get_page_hash(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return hashlib.sha256(response.text.encode('utf-8')).hexdigest()
    except Exception as e:
        print(f"Błąd pobierania: {e}")
        return None

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print("Powiadomienie wysłane.")
    except Exception as e:
        print(f"Błąd wysyłki: {e}")

def load_last_hash():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    return None

def save_hash(hash_value):
    # Upewniam się, że folder istnieje
    os.makedirs(os.path.dirname(HASH_FILE), exist_ok=True)
    with open(HASH_FILE, "w") as f:
        f.write(hash_value)

# ======= GŁÓWNA LOGIKA ========
def main():
    print("Monitor uruchomiony...")
    
    # Sprawdzam, czy dane Telegram są ustawione
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Brak danych Telegram! Ustaw sekrety TELEGRAM_TOKEN i TELEGRAM_CHAT_ID.")
        return

    current_hash = get_page_hash(URL)
    if current_hash is None:
        print("Nie udało się pobrać strony.")
        return

    last_hash = load_last_hash()

    if last_hash is None:
        save_hash(current_hash)
        print("Zapisano stan początkowy.")
    elif current_hash != last_hash:
        save_hash(current_hash)
        message = (
            "🔔 <b>NOWA ZMIANA NA STRONIE LICYTACJI!</b>\n\n"
            f"<a href='{URL}'>Kliknij tutaj, aby zobaczyć</a>\n\n"
            "Prawdopodobnie dodano nowe ogłoszenie. Sprawdź."
        )
        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
        print("Zmiana wykryta – wysłano powiadomienie.")
    else:
        print("Brak zmian.")

if __name__ == "__main__":
    main()

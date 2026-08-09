import os
import requests
import hashlib
import re

# ======= KONFIGURACJA ========
URL = "https://licytacje.komornik.pl/wyszukiwarka/obwieszczenia-o-licytacji?city=Wroc%C5%82aw&mainCategory=REAL_ESTATE"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HASH_FILE = "cache/listings_hash.txt"

# ======= FUNKCJE ========
def get_listings_hash(url):
    """Pobiera stronę, wyciąga same ogłoszenia i zwraca ich hash."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        text = response.text

        # Wyciągamy wszystkie bloki ogłoszeń.
        # Każde ogłoszenie zaczyna się od "Licytacja nieruchomości" i kończy na dacie "Początek:"
        pattern = r'Licytacja nieruchomości.*?Początek:.*?\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}'
        matches = re.findall(pattern, text, re.DOTALL)

        # Jeśli nie znalazło (np. strona zmieniła strukturę) – używamy starego hasha całej strony
        if not matches:
            print("Nie znaleziono ogłoszeń w nowym formacie – używam hasha całej strony.")
            return hashlib.sha256(text.encode('utf-8')).hexdigest()

        # Sortujemy listę, żeby kolejność wyświetlania nie miała znaczenia
        matches.sort()
        combined = ''.join(matches)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    except Exception as e:
        print(f"Błąd pobierania/parsowania: {e}")
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
    os.makedirs(os.path.dirname(HASH_FILE), exist_ok=True)
    with open(HASH_FILE, "w") as f:
        f.write(hash_value)

def main():
    print("Monitor uruchomiony (wersja parsująca ogłoszenia)...")
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Brak danych Telegram! Ustaw sekrety.")
        return

    current_hash = get_listings_hash(URL)
    if current_hash is None:
        print("Nie udało się pobrać/obliczyć hasha.")
        return

    last_hash = load_last_hash()

    if last_hash is None:
        save_hash(current_hash)
        print("Zapisano stan początkowy (teraz porównujemy tylko ogłoszenia).")
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
        print("Brak zmian (lista ogłoszeń bez zmian).")

if __name__ == "__main__":
    main()

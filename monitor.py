import os
import requests
import hashlib
import re

# ======= KONFIGURACJA ========
URL = "https://licytacje.komornik.pl/wyszukiwarka/obwieszczenia-o-licytacji?city=Wroc%C5%82aw&mainCategory=REAL_ESTATE&province=dolno%C5%9Bl%C4%85skie"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Plik do przechowywania poprzedniej listy tytułów
LISTINGS_FILE = "cache/listings.txt"

# ======= FUNKCJE ========
def get_listings(url):
    """Pobiera stronę i zwraca listę tytułów ogłoszeń."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        text = response.text

        # Wyciągamy tytuły: wszystko po "Licytacja nieruchomości" do "map_"
        pattern = r'Licytacja nieruchomości (.*?) map_'
        matches = re.findall(pattern, text, re.DOTALL)

        # Czyścimy tytuły z zbędnych znaków
        titles = [re.sub(r'\s+', ' ', t).strip() for t in matches]

        if not titles:
            print("Nie znaleziono ogłoszeń – używam hasha całej strony jako awaryjnego.")
            # Awaryjnie: hash całej strony
            return [hashlib.sha256(text.encode('utf-8')).hexdigest()]

        return titles

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

def load_previous_listings():
    """Wczytuje poprzednią listę tytułów z pliku."""
    if os.path.exists(LISTINGS_FILE):
        with open(LISTINGS_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()]
    return None

def save_listings(listings):
    """Zapisuje obecną listę tytułów do pliku."""
    os.makedirs(os.path.dirname(LISTINGS_FILE), exist_ok=True)
    with open(LISTINGS_FILE, "w", encoding="utf-8") as f:
        for title in listings:
            f.write(title + "\n")

def main():
    print("Monitor uruchomiony (wersja z tytułami)...")
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Brak danych Telegram! Ustaw sekrety.")
        return

    current_listings = get_listings(URL)
    if current_listings is None:
        print("Nie udało się pobrać listy ogłoszeń.")
        return

    previous_listings = load_previous_listings()

    if previous_listings is None:
        # Pierwsze uruchomienie – zapisujemy stan
        save_listings(current_listings)
        print(f"Zapisano stan początkowy. Znaleziono {len(current_listings)} ogłoszeń.")
        return

    # Porównujemy listy – szukamy nowych tytułów
    current_set = set(current_listings)
    previous_set = set(previous_listings)

    new_titles = current_set - previous_set

    if new_titles:
        # Aktualizujemy zapisany stan
        save_listings(current_listings)

        # Budujemy wiadomość
        message = "🔔 <b>NOWE OGŁOSZENIA NA STRONIE LICYTACJI!</b>\n\n"
        for title in new_titles:
            message += f"• {title}\n"

        message += f"\n<a href='{URL}'>Kliknij tutaj, aby zobaczyć wszystkie</a>"

        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
        print(f"Zmiana wykryta – dodano {len(new_titles)} nowych ogłoszeń.")
    else:
        print("Brak nowych ogłoszeń.")

if __name__ == "__main__":
    main()

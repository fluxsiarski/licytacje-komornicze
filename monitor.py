import os
import requests
import re

# ======= KONFIGURACJA ========
URL = "https://licytacje.komornik.pl/wyszukiwarka/obwieszczenia-o-licytacji?city=Wroc%C5%82aw&mainCategory=REAL_ESTATE&province=dolno%C5%9Bl%C4%85skie"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

LISTINGS_FILE = "cache/listings.txt"

# ======= FUNKCJE ========
def get_listings_with_details(url):
    """Pobiera stronę i zwraca listę słowników z tytułem, adresem i datą."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        text = response.text

        # Wzorzec: każdy blok ogłoszenia
        pattern = r'(Licytacja nieruchomości.*??) map_dolnoslaskie.*?map_marker (.*?) calendar_month Początek: (.*?)(?=Licytacja nieruchomości|$)'
        matches = re.findall(pattern, text, re.DOTALL)

        listings = []
        for title, address, date in matches:
            # Czyszczenie tytułu i adresu
            clean_title = re.sub(r'\s+', ' ', title).strip()
            clean_address = re.sub(r'\s+', ' ', address).strip()
            clean_date = date.strip()
            listings.append({
                "title": clean_title,
                "address": clean_address,
                "date": clean_date
            })

        if not listings:
            print("Nie znaleziono ogłoszeń – używam awaryjnego hasha.")
            # Awaryjnie: hash całej strony
            import hashlib
            return [{"title": hashlib.sha256(text.encode('utf-8')).hexdigest(), "address": "", "date": ""}]

        return listings

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
    """Wczytuje poprzednią listę (zapisane jako linie: tytuł|adres|data)."""
    if os.path.exists(LISTINGS_FILE):
        with open(LISTINGS_FILE, "r", encoding="utf-8") as f:
            return [line.strip().split("|") for line in f.readlines()]
    return None

def save_listings(listings):
    """Zapisuje obecną listę (tytuł|adres|data)."""
    os.makedirs(os.path.dirname(LISTINGS_FILE), exist_ok=True)
    with open(LISTINGS_FILE, "w", encoding="utf-8") as f:
        for item in listings:
            f.write(f"{item['title']}|{item['address']}|{item['date']}\n")

def main():
    print("Monitor uruchomiony (z adresem i datą)...")
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Brak danych Telegram! Ustaw sekrety.")
        return

    current_listings = get_listings_with_details(URL)
    if current_listings is None:
        print("Nie udało się pobrać listy ogłoszeń.")
        return

    previous = load_previous_listings()
    if previous is None:
        save_listings(current_listings)
        print(f"Zapisano stan początkowy. Znaleziono {len(current_listings)} ogłoszeń.")
        return

    # Tworzymy zbiór identyfikatorów (tytuł + adres) dla porównania
    current_ids = {f"{item['title']}|{item['address']}" for item in current_listings}
    previous_ids = {f"{line[0]}|{line[1]}" for line in previous}

    new_ids = current_ids - previous_ids

    if new_ids:
        save_listings(current_listings)

        # Znajdujemy pełne dane dla nowych ogłoszeń
        new_items = [item for item in current_listings if f"{item['title']}|{item['address']}" in new_ids]

        message = "🔔 <b>NOWE OGŁOSZENIA NA STRONIE LICYTACJI!</b>\n\n"
        for item in new_items:
            message += f"🏠 <b>{item['title']}</b>\n"
            message += f"📍 {item['address']}\n"
            message += f"📅 Początek: {item['date']}\n\n"

        message += f"<a href='{URL}'>Kliknij tutaj, aby zobaczyć wszystkie</a>"

        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
        print(f"Zmiana wykryta – dodano {len(new_items)} nowych ogłoszeń.")
    else:
        print("Brak nowych ogłoszeń.")

if __name__ == "__main__":
    main()

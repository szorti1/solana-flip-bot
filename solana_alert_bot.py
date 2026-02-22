import requests
import time
import os
import json
from telegram import Bot
from datetime import datetime, timezone

# =====================
# 🔐 ZMIENNE ŚRODOWISKOWE
# =====================
TELEGRAM_TOKEN = os.environ.get("8398851903:AAHxvBNjfEJeO6J6a1WcjuDnGWyAo_QwQb8")
CHAT_ID = os.environ.get("1725153905")

# =====================
# 🔥 FLIP SETTINGS
# =====================
MIN_MC = 500_000
MAX_MC = 2_000_000
MIN_VOLUME = 300_000
MAX_AGE_HOURS = 48
CHECK_INTERVAL = 180  # co 3 min
MIN_LIQUIDITY = 100_000

bot = Bot(token=8398851903:AAHxvBNjfEJeO6J6a1WcjuDnGWyAo_QwQb8)

SEEN_FILE = "seen_tokens.json"
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen = set(json.load(f))
else:
    seen = set()

def save_seen():
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

# =====================
# Rug Check Function
# =====================
def rug_check(token_address):
    try:
        url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return False
        data = r.json()
        score = data.get("score", 0)
        risks = data.get("risks", [])
        mint_auth = data.get("token", {}).get("mintAuthority")
        freeze_auth = data.get("token", {}).get("freezeAuthority")
        if score < 60:
            return False
        if mint_auth is not None or freeze_auth is not None:
            return False
        if len(risks) > 2:
            return False
        return True
    except:
        return False

# =====================
# Fetch new token pairs
# =====================
def fetch_pairs():
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    r = requests.get(url)
    return r.json()["pairs"]

def is_fresh(pair):
    created = pair.get("pairCreatedAt")
    if not created:
        return False
    created_time = datetime.fromtimestamp(created / 1000, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
    return age_hours <= MAX_AGE_HOURS

# =====================
# Main check function
# =====================
def check_market():
    print("Sprawdzam rynek...")
    pairs = fetch_pairs()
    for pair in pairs:
        try:
            mc = float(pair.get("fdv") or 0)
            volume = float(pair.get("volume", {}).get("h24") or 0)
            liquidity = float(pair.get("liquidity", {}).get("usd") or 0)
            token_address = pair["baseToken"]["address"]
            if (
                MIN_MC <= mc <= MAX_MC
                and volume >= MIN_VOLUME
                and liquidity >= MIN_LIQUIDITY
                and is_fresh(pair)
                and token_address not in seen
                and rug_check(token_address)
            ):
                seen.add(token_address)
                save_seen()
                message = (
                    f"🚀 FLIP ALERT (SOLANA)\n\n"
                    f"{pair['baseToken']['name']} ({pair['baseToken']['symbol']})\n"
                    f"MC: ${mc:,.0f}\n"
                    f"Volume 24h: ${volume:,.0f}\n"
                    f"Liquidity: ${liquidity:,.0f}\n\n"
                    f"DEX: {pair['url']}"
                )
                bot.send_message(chat_id=CHAT_ID, text=message)
                print("Alert wysłany")
        except Exception:
            continue

print("Bot flip uruchomiony...")
while True:
    try:
        check_market()
    except Exception as e:
        print("Błąd:", e)
    time.sleep(CHECK_INTERVAL)
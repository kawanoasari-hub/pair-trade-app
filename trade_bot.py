import requests
import json
import os
import time
from datetime import datetime
import yfinance as yf

BOT_TOKEN = "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

STOCK_FILE = "positions.json"
PAIR_FILE = "positions_pair.json"


def send(msg, keyboard=None):

    url = f"{BASE_URL}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    if keyboard:
        data["reply_markup"] = keyboard

    requests.post(url, json=data)


def answer_callback(callback_id):
    url = f"{BASE_URL}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_id})


def load_json(file):
    if not os.path.exists(file):
        return []
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_price(code):
    try:
        ticker = yf.Ticker(code)
        return float(ticker.fast_info["lastPrice"])
    except:
        return None


def entry_pair_auto(c1, c2, beta, z):

    pairs = load_json(PAIR_FILE)

    pair_name = f"{c1}_{c2}"

    # 🔥 重複防止
    for p in pairs:
        if p.get("pair") == pair_name and p["status"] == "open":
            send("⚠️ すでにペア保有中")
            return

    p1 = get_price(c1)
    p2 = get_price(c2)

    if p1 is None or p2 is None:
        send("⚠️ 価格取得失敗")
        return

    side1 = "SELL" if float(z) > 0 else "BUY"
    side2 = "BUY" if float(z) > 0 else "SELL"

    pair = {
        "pair": pair_name,
        "stock1": c1,
        "entry_price1": p1,
        "qty1": 100,
        "side1": side1,
        "stock2": c2,
        "entry_price2": p2,
        "qty2": 100,
        "side2": side2,
        "beta": float(beta),
        "entry_z": float(z),
        "entry_date": str(datetime.now().date()),
        "status": "open"
    }

    pairs.append(pair)
    save_json(PAIR_FILE, pairs)

    send(f"🤖 PAIR ENTRY\n{pair_name}")


def close_pair(pair_name):

    pairs = load_json(PAIR_FILE)

    for p in pairs:

        name = p.get("pair")

        if name == pair_name and p["status"] == "open":

            price1 = get_price(p["stock1"])
            price2 = get_price(p["stock2"])

            if price1 is None or price2 is None:
                send("⚠️ 価格取得失敗")
                return

            p["status"] = "closed"

            send(f"📉 PAIR CLOSE\n{pair_name}")

            save_json(PAIR_FILE, pairs)
            return

    send("⚠️ ペアなし")


def get_updates(offset=None):

    url = f"{BASE_URL}/getUpdates"

    params = {
        "timeout": 100,
        "allowed_updates": ["message", "callback_query"]
    }

    if offset:
        params["offset"] = offset

    return requests.get(url, params=params).json()


def main():

    print("BOT起動")
    update_id = None

    while True:

        try:
            data = get_updates(update_id)

            for item in data.get("result", []):

                update_id = item["update_id"] + 1

                if "callback_query" in item:

                    callback_id = item["callback_query"]["id"]
                    answer_callback(callback_id)

                    data_cb = item["callback_query"]["data"]
                    parts = data_cb.split("|")

                    if parts[0] == "entry":
                        entry_pair_auto(parts[1], parts[2], parts[3], parts[4])

                    elif parts[0] == "exit_pair":
                        close_pair(parts[1])

            time.sleep(1)

        except Exception as e:
            print("error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
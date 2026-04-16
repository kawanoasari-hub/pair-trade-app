import yfinance as yf
import requests
import json
import os
from datetime import datetime

# ===== Telegram =====
TOKEN = "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== ログファイル =====
BREAK_FILE = "breakout_log.json"

# ===== ログ読み込み =====
if os.path.exists(BREAK_FILE):
    with open(BREAK_FILE) as f:
        breakout_log = json.load(f)
else:
    breakout_log = {}

# ===== 今日の日付 =====
today = datetime.now().strftime("%Y-%m-%d")

# ===== 監視銘柄（watchlistから） =====
WATCHLIST_FILE = "watchlist.json"

if not os.path.exists(WATCHLIST_FILE):
    send("⚠️ watchlistがありません")
    exit()

with open(WATCHLIST_FILE) as f:
    watchlist = json.load(f)

# ===== メイン =====
results = []

for item in watchlist:

    code = item["code"]
    name = item["name"]
    prev_high = item["prev_high"]

    try:
        df = yf.download(code, period="5d", interval="1m", progress=False)

        if len(df) < 10:
            continue

        close = df["Close"]

        price = close.iloc[-1].item()

        # ===== ブレイク判定 =====
        if price > prev_high:

            # ===== すでに今日通知済みかチェック =====
            if code in breakout_log:
                if breakout_log[code] == today:
                    continue

            # ===== 通知 =====
            msg = (
                f"🚀 ブレイク検出\n"
                f"{name} ({code})\n"
                f"現在値：{round(price,1)}\n"
                f"前日高値：{round(prev_high,1)}"
            )

            send(msg)

            # ===== 記録 =====
            breakout_log[code] = today

    except:
        continue

# ===== ログ保存 =====
with open(BREAK_FILE, "w") as f:
    json.dump(breakout_log, f, indent=2)
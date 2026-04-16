import json
from datetime import datetime
import requests
import os

# ===== Telegram設定 =====
TOKEN = "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


# ===== ファイル =====
STOCK_FILE = "positions.json"
PAIR_FILE = "positions_pair.json"


# ===== 初期化 =====
total_trades = 0
win_trades = 0
lose_trades = 0
total_pnl = 0

stock_trades = 0
stock_pnl = 0

pair_trades = 0
pair_pnl = 0

monthly = {}


# ===== 単独株 =====
if os.path.exists(STOCK_FILE):

    with open(STOCK_FILE, "r", encoding="utf-8") as f:
        stocks = json.load(f)

    for t in stocks:

        if t.get("status") != "closed":
            continue

        entry = t["entry_price"]
        exitp = t["exit_price"]
        qty = t["qty"]

        pnl = int((exitp - entry) * qty)

        total_pnl += pnl
        stock_pnl += pnl

        total_trades += 1
        stock_trades += 1

        if pnl > 0:
            win_trades += 1
        else:
            lose_trades += 1

        exit_date = datetime.strptime(t["exit_date"], "%Y-%m-%d")
        key = exit_date.strftime("%Y-%m")

        if key not in monthly:
            monthly[key] = 0

        monthly[key] += pnl


# ===== ペアトレード =====
if os.path.exists(PAIR_FILE):

    with open(PAIR_FILE, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    for t in pairs:

        if t.get("status") != "closed":
            continue

        entry1 = t["entry_price1"]
        exit1 = t["exit_price1"]
        qty1 = t["qty1"]

        entry2 = t["entry_price2"]
        exit2 = t["exit_price2"]
        qty2 = t["qty2"]

        # BUY側
        pnl1 = (exit1 - entry1) * qty1

        # SELL側
        pnl2 = (entry2 - exit2) * qty2

        pnl = int(pnl1 + pnl2)

        total_pnl += pnl
        pair_pnl += pnl

        total_trades += 1
        pair_trades += 1

        if pnl > 0:
            win_trades += 1
        else:
            lose_trades += 1

        exit_date = datetime.strptime(t["exit_date"], "%Y-%m-%d")
        key = exit_date.strftime("%Y-%m")

        if key not in monthly:
            monthly[key] = 0

        monthly[key] += pnl


# ===== 結果 =====
if total_trades == 0:
    send("📊 運用成績：決済トレードなし")
    exit()

win_rate = win_trades / total_trades * 100
avg_pnl = total_pnl / total_trades


msg = "📈 運用成績サマリー（全期間）\n"

msg += (
    f"\n総トレード数：{total_trades}"
    f"\n勝ち：{win_trades}"
    f"\n負け：{lose_trades}"
    f"\n勝率：{win_rate:.1f}%"
    f"\n総損益：{total_pnl:+,} 円"
    f"\n平均損益：{int(avg_pnl):+,} 円"
)


msg += "\n\n【内訳】"

msg += (
    f"\n単独株：{stock_trades}トレード / {stock_pnl:+,} 円"
    f"\nペア：{pair_trades}トレード / {pair_pnl:+,} 円"
)


msg += "\n\n【月次損益】"

for m in sorted(monthly.keys()):
    msg += f"\n{m} : {monthly[m]:+,} 円"


send(msg)
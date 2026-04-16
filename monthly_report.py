import json
from datetime import datetime
import requests
from collections import defaultdict
import os

# ===== Telegram設定 =====
TOKEN = "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== ファイル =====
POSITIONS_FILE = "positions.json"

if not os.path.exists(POSITIONS_FILE):
    send("📊 月次レポート：データがありません")
    exit()

# ===== positions.json 読み込み =====
with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
    positions = json.load(f)

monthly_pnl = defaultdict(int)
monthly_trades = defaultdict(int)
monthly_wins = defaultdict(int)

total_pnl = 0
total_trades = 0
win_trades = 0

for t in positions:
    # closedのみ対象
    if t.get("status") != "closed":
        continue

    entry = t["entry_price"]
    exitp = t["exit_price"]
    qty = t["qty"]
    exit_date = datetime.strptime(t["exit_date"], "%Y-%m-%d")

    pnl = int((exitp - entry) * qty)

    key = exit_date.strftime("%Y-%m")

    monthly_pnl[key] += pnl
    monthly_trades[key] += 1
    total_pnl += pnl
    total_trades += 1

    if pnl > 0:
        monthly_wins[key] += 1
        win_trades += 1

# ===== 出力 =====
if total_trades == 0:
    send("📊 月次レポート：決済済みトレードがありません")
    exit()

msg = "📊 月次運用レポート\n"

for m in sorted(monthly_pnl.keys()):
    trades_m = monthly_trades[m]
    wins_m = monthly_wins[m]
    win_rate_m = wins_m / trades_m * 100
    pnl_m = monthly_pnl[m]

    msg += (
        f"\n【{m}】"
        f"\n損益：{pnl_m:+,} 円"
        f"\nトレード数：{trades_m}"
        f"\n勝率：{win_rate_m:.1f}%\n"
    )

total_win_rate = win_trades / total_trades * 100

msg += (
    "\n===== 累計 ====="
    f"\n総損益：{total_pnl:+,} 円"
    f"\n総トレード数：{total_trades}"
    f"\n勝率：{total_win_rate:.1f}%"
)

send(msg)

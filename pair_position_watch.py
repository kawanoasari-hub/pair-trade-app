import yfinance as yf
import pandas as pd
import numpy as np
import json
import requests
from datetime import datetime
import statsmodels.api as sm


# ===== Telegram =====

TOKEN = "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def send(msg, keyboard=None):

    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)

    requests.post(url, json=payload)


# ===== 設定 =====

WINDOW = 60
EXIT_Z = 0.5
PAIR_FILE = "positions_pair.json"


# ===== JSON =====

def load_pairs():

    try:
        with open(PAIR_FILE, "r") as f:
            return json.load(f)
    except:
        return []


# ===== Zscore =====

def calc_zscore(spread):

    mean = spread.mean()
    std = spread.std()

    if std == 0:
        return 0

    return (spread.iloc[-1] - mean) / std


# ===== half life =====

def calc_half_life(spread):

    lag = spread.shift(1).bfill()
    delta = spread - lag

    model = sm.OLS(delta, sm.add_constant(lag)).fit()

    hl = -np.log(2) / model.params.iloc[1]

    if hl < 0:
        hl = 100

    return hl


# ===== Zコメント =====

def z_comment(z):

    az = abs(z)

    if az < 0.5:
        return "🎯 利確ゾーン"
    elif az < 1.5:
        return "🟢 保有"
    elif az < 2.5:
        return "⚠ 拡大注意"
    else:
        return "❌ 損切警戒"


# ===== Half-life コメント =====

def half_life_comment(days, hl):

    if days < hl * 0.5:
        return "⏳ 平均回帰途中"
    elif days < hl:
        return "↩ 回帰進行中"
    elif days < hl * 2:
        return "⚠ 長期化"
    else:
        return "❌ 回帰失敗疑い"


# ===== メイン =====

pairs = load_pairs()

open_pairs = [p for p in pairs if p["status"] == "open"]

if len(open_pairs) == 0:
    send("PAIRポジションなし")
    exit()


# ===== ティッカー収集 =====

tickers = []

for p in open_pairs:
    tickers.append(p["stock1"])
    tickers.append(p["stock2"])

tickers = list(set(tickers))


# ===== データ取得 =====

data = yf.download(
    tickers,
    period="3mo",
    auto_adjust=True,
    progress=False
)["Close"].dropna()


today = datetime.now().date()


# ===== 各ポジション処理 =====

for p in open_pairs:

    s1 = p["stock1"]
    s2 = p["stock2"]

    pair_name = p.get("pair", f"{s1}_{s2}")

    try:
        price1 = data[s1].tail(WINDOW)
        price2 = data[s2].tail(WINDOW)
    except:
        continue

    log1 = np.log(price1)
    log2 = np.log(price2)

    model = sm.OLS(log1, sm.add_constant(log2)).fit()
    beta = model.params.iloc[1]

    spread = log1 - beta * log2

    z = calc_zscore(spread)
    hl = calc_half_life(spread)

    price_now1 = price1.iloc[-1]
    price_now2 = price2.iloc[-1]

    entry1 = p["entry_price1"]
    entry2 = p["entry_price2"]

    qty1 = p["qty1"]
    qty2 = p["qty2"]

    side1 = p["side1"].lower()
    side2 = p["side2"].lower()

    profit1 = (price_now1 - entry1) * qty1 if side1 == "buy" else (entry1 - price_now1) * qty1
    profit2 = (entry2 - price_now2) * qty2 if side2 == "sell" else (price_now2 - entry2) * qty2

    total = profit1 + profit2

    # ===== 保有日数 =====

    entry_date = datetime.strptime(p["entry_date"], "%Y-%m-%d").date()
    days = (today - entry_date).days

    # ===== メッセージ =====

    msg = (
        f"📊 {pair_name}\n\n"
        f"Zscore {z:.2f}\n"
        f"{z_comment(z)}\n\n"
        f"Half-life {hl:.1f}日\n"
        f"保有日数 {days}日\n"
        f"{half_life_comment(days, hl)}\n\n"
        f"{s1} {side1.upper()} {qty1}\n"
        f"{s2} {side2.upper()} {qty2}\n\n"
        f"現在損益 {int(total):,}円"
    )

    if abs(z) < EXIT_Z:
        msg += "\n\n⚠ EXITシグナル"

    # ===== ボタン =====

    keyboard = {
        "inline_keyboard": [[
            {
                "text": "EXIT",
                "callback_data": f"exit_pair|{pair_name}"
            }
        ]]
    }

    send(msg, keyboard)
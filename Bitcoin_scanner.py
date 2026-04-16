import ccxt
import pandas as pd
import numpy as np
import requests
import json

# ===== Telegram =====
TOKEN = "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

def send(msg, keyboard=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    requests.post(url, data=data)


# ===== 取引所 =====
exchange = ccxt.binance()

symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "MATIC/USDT"
]


# ===== RSI =====
def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ===== ADX =====
def adx(df, period=14):
    high=df['high']
    low=df['low']
    close=df['close']

    plus_dm = high.diff()
    minus_dm = low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0

    tr = pd.concat([
        high-low,
        abs(high-close.shift()),
        abs(low-close.shift())
    ],axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = abs(100 * (minus_dm.rolling(period).mean() / atr))

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100

    return dx.rolling(period).mean()


# ===== BTC基準 =====
btc = exchange.fetch_ohlcv("BTC/USDT",'1d',limit=200)
btc_df = pd.DataFrame(btc,columns=['t','o','h','l','c','v'])
btc_return = btc_df["c"].iloc[-1]/btc_df["c"].iloc[-60]-1


results = []

for symbol in symbols:

    try:
        ohlcv = exchange.fetch_ohlcv(symbol,'1d',limit=200)

        df = pd.DataFrame(
            ohlcv,
            columns=['time','open','high','low','close','volume']
        )

        close = df["close"]
        volume = df["volume"]

        price = float(close.iloc[-1])

        ma50 = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]

        rsi_val = rsi(close).iloc[-1]
        adx_val = adx(df).iloc[-1]

        coin_return = close.iloc[-1]/close.iloc[-60]-1
        rs = coin_return - btc_return

        avg_vol = volume.iloc[-20:-1].mean()
        if volume.iloc[-1] < avg_vol * 0.7:
            continue

        # ===== レジーム =====
        if price > ma200 and adx_val > 25:
            regime = "TREND"
        else:
            regime = "RANGE"

        signal = None

        if regime == "TREND":
            if price < ma50 and 40 < rsi_val < 55 and rs > 0:
                signal = "押し目"

        if regime == "RANGE":
            if rsi_val < 30:
                signal = "逆張り"

        if signal:

            # ===== スコア =====
            score = (
                rs*100 +
                adx_val +
                (50 - abs(50 - rsi_val))
            )

            results.append({
                "symbol": symbol,
                "price": price,
                "rsi": rsi_val,
                "adx": adx_val,
                "rs": rs,
                "score": score,
                "signal": signal
            })

    except:
        continue


# ===== ソート =====
results.sort(key=lambda x: x["score"], reverse=True)


# ===== 通知 =====
if not results:
    send("シグナルなし")
    exit()

for r in results[:5]:

    msg = (
        f"🚀 {r['symbol']}\n"
        f"{r['signal']}\n"
        f"Score:{r['score']:.1f}\n"
        f"RS:{r['rs']*100:.1f}%\n"
        f"RSI:{r['rsi']:.1f}\n"
        f"ADX:{r['adx']:.1f}\n"
        f"価格:{r['price']:.2f}"
    )

    keyboard = {
        "inline_keyboard": [[
            {
                "text": "ENTRY",
                "callback_data": f"entry_crypto|{r['symbol']}|{r['price']}"
            }
        ]]
    }

    send(msg, keyboard)
import yfinance as yf
import requests
import math
import pandas as pd
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


# ===== 資金管理 =====
MAX_LOSS = 20000
MAX_PER_TRADE = 1000000

# ===== 監視銘柄 =====
stocks={

"8001.T":"伊藤忠商事",
"8058.T":"三菱商事",
"8031.T":"三井物産",
"8002.T":"丸紅",
"8053.T":"住友商事",

"7203.T":"トヨタ",
"7267.T":"ホンダ",
"7270.T":"SUBARU",
"7269.T":"スズキ",
"7261.T":"マツダ",

"8306.T":"三菱UFJ",
"8316.T":"三井住友FG",
"8411.T":"みずほFG",

"9433.T":"KDDI",

"6501.T":"日立",
"6752.T":"パナソニック",
"6758.T":"ソニー",
"7751.T":"キヤノン",
"6702.T":"富士通",
"6701.T":"NEC",

"6857.T":"アドバンテスト",
"7735.T":"SCREEN",
"6146.T":"ディスコ",

"5401.T":"日本製鉄",
"5411.T":"JFE",

"6301.T":"コマツ",
"6326.T":"クボタ",
"6367.T":"ダイキン",

"4502.T":"武田薬品",
"4568.T":"第一三共",
"4503.T":"アステラス",

"8766.T":"東京海上",

"8591.T":"オリックス",
"6178.T":"日本郵政",

"3382.T":"セブン&アイ",
"6098.T":"リクルート",

"9101.T":"日本郵船",
"9104.T":"商船三井",
"9107.T":"川崎汽船",

"6920.T":"レーザーテック",
"6963.T":"ローム",
"6723.T":"ルネサス",
"6594.T":"ニデック",
"6981.T":"村田製作所",
"6971.T":"京セラ",
"6954.T":"ファナック",
"6645.T":"オムロン",
"6724.T":"セイコーエプソン",

"9984.T":"ソフトバンクグループ",
"4689.T":"LINEヤフー",
"4755.T":"楽天グループ",

"7974.T":"任天堂",
"7832.T":"バンダイナムコ",
"9766.T":"コナミ",
"3659.T":"ネクソン",

"6902.T":"デンソー",
"7201.T":"日産自動車",
"7272.T":"ヤマハ発動機",

"6273.T":"SMC",
"6383.T":"ダイフク",

"3402.T":"東レ",
"4188.T":"三菱ケミカル",

"1801.T":"大成建設",
"1925.T":"大和ハウス",

"2914.T":"日本たばこ産業",
"2802.T":"味の素",

"8750.T":"第一生命",
"8308.T":"りそな"
}

# ===== 日経チェック =====
nikkei = yf.download("^N225", period="1mo", interval="1d", progress=False)
nikkei_close = nikkei["Close"].iloc[-1].item()
nikkei_ma25 = nikkei["Close"].rolling(25).mean().iloc[-1].item()

if nikkei_close < nikkei_ma25:
    send("📉 日経弱いためエントリー見送り")
    exit()

# ===== データ取得 =====
tickers = list(stocks.keys())

data = yf.download(
    tickers,
    period="3mo",
    interval="1d",
    group_by="ticker",
    threads=True,
    progress=False
)

results = []

for code, name in stocks.items():
    try:
        df = data[code].dropna()

        if len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        high = df["High"]

        price = float(close.iloc[-1])
        open_price = float(df["Open"].iloc[-1])

        ma5 = float(close.rolling(5).mean().iloc[-1])
        ma25 = float(close.rolling(25).mean().iloc[-1])

        avg_vol = float(volume.rolling(20).mean().iloc[-1])
        today_vol = float(volume.iloc[-1])

        high20 = float(high.rolling(20).max().iloc[-2])

        if price < ma25:
            continue

        if ma5 < ma25:
            continue

        if price <= high20:
            continue

        if today_vol < avg_vol * 1.3:
            continue

        if price <= open_price:
            continue

        if price > open_price * 1.05:
            continue

        rank = "B"

        if today_vol > avg_vol * 1.5:
            rank = "A"

        if today_vol > avg_vol * 2:
            rank = "S"

        stop = price * 0.97
        take = price * 1.05

        risk = price - stop

        qty = math.floor(MAX_LOSS / risk)
        qty = min(qty, math.floor(MAX_PER_TRADE / price))
        qty = (qty // 100) * 100

        if qty < 100:
            continue

        results.append({
            "rank": rank,
            "name": name,
            "code": code,
            "price": round(price, 1),
            "qty": qty,
            "stop": round(stop, 1),
            "take": round(take, 1)
        })

    except:
        continue

# ===== フィルター（B除外）=====
results = [r for r in results if r["rank"] != "B"]

# ===== ソート =====
rank_order = {"S": 0, "A": 1, "B": 2}
results.sort(key=lambda x: rank_order[x["rank"]])

# ===== 通知（ボタン付き）=====
if not results:
    send("📉 引け候補なし")
else:
    send("📈 引け候補（タップでエントリー）")

    for r in results[:7]:

        msg = (
            f"【{r['rank']}】{r['name']} ({r['code']})"
            f"\n価格：{r['price']}"
            f"\n株数：{r['qty']}"
            f"\n損切：{r['stop']}"
            f"\n利確：{r['take']}"
        )

        keyboard = {
            "inline_keyboard": [[
                {
                    "text": "ENTRY",
                    "callback_data": f"entry_stock|{r['code']}|{r['price']}|{r['qty']}"
                }
            ]]
        }

        send(msg, keyboard)
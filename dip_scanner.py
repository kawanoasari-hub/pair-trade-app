import yfinance as yf
import requests
import pandas as pd
import math
import json

# ===== Telegram =====
TOKEN="8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID="7919205087"

def send(msg):
    url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url,data={"chat_id":CHAT_ID,"text":msg})

# ===== 設定 =====
MAX_LOSS=20000
MAX_PER_TRADE=1000000
WATCHLIST_FILE="watchlist.json"

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

results=[]
watchlist=[]

for code,name in stocks.items():

    try:
        df=yf.download(code,period="6mo",interval="1d",progress=False)
        if len(df)<120:
            continue

        close=df["Close"]
        high=df["High"]
        low=df["Low"]
        open_=df["Open"]

        price=close.iloc[-1].item()

        ma25=close.rolling(25).mean().iloc[-1].item()
        ma25_prev=close.rolling(25).mean().iloc[-5].item()

        ma50=close.rolling(50).mean().iloc[-1].item()
        ma75=close.rolling(75).mean().iloc[-1].item()
        ma200=close.rolling(200).mean().iloc[-1].item()

        # ===== トレンド =====
        if price < ma200:
            continue

        if ma25 < ma25_prev:
            continue

        # ===== 押し目ゾーン =====
        zone=None

        if abs(price-ma50)/ma50 < 0.015:
            zone="50"
            base_ma=ma50

        elif abs(price-ma75)/ma75 < 0.02:
            zone="75"
            base_ma=ma75

        else:
            continue

        # ===== しっかり下げたか =====
        drop = (base_ma - price) / base_ma
        if drop < 0.02:
            continue

        # ===== 戻したか（超重要） =====
        if price < base_ma:
            continue

        # ===== RSI =====
        delta=close.diff()
        gain=(delta.where(delta>0,0)).rolling(14).mean()
        loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rs=gain/loss
        rsi=(100-(100/(1+rs))).iloc[-1]

        # ===== ローソク足（下ヒゲ） =====
        today_close=close.iloc[-1].item()
        today_open=open_.iloc[-1].item()
        today_low=low.iloc[-1].item()

        body=abs(today_close - today_open)
        lower_wick=min(today_close,today_open)-today_low

        # ===== ランク =====
        priority=None

        if rsi < 40 and lower_wick > body:
            priority="S"

        elif rsi < 45:
            priority="A"

        else:
            continue  # ← Bは完全排除

        # ===== 資金管理 =====
        stop=base_ma*0.97
        risk=price-stop
        take=price+risk*2

        qty=math.floor(MAX_LOSS/risk)
        qty=min(qty,math.floor(MAX_PER_TRADE/price))
        qty=(qty//100)*100

        if qty<100:
            continue

        results.append({
            "priority":priority,
            "name":name,
            "code":code,
            "price":round(price,1),
            "zone":zone,
            "qty":qty,
            "stop":round(stop,1),
            "take":round(take,1)
        })

        # ===== watchlist（ブレイク用）=====
        watchlist.append({
            "code":code,
            "name":name,
            "prev_high":high.iloc[-1].item()
        })

    except:
        continue

# ===== 保存 =====
with open(WATCHLIST_FILE,"w") as f:
    json.dump(watchlist,f,indent=2)

# ===== 通知 =====
results.sort(key=lambda x: x["priority"])

if not results:
    send("📉 押し目なし（厳選モード）")

else:
    msg="📉 押し目（S/Aのみ）\n"

    for r in results[:5]:
        msg+=(
        f"\n【{r['priority']}】{r['name']} ({r['code']})"
        f"\n押し目：{r['zone']}MA"
        f"\n価格：{r['price']}"
        f"\n株数：{r['qty']}"
        f"\n損切：{r['stop']}"
        f"\n利確：{r['take']}\n"
        )

    send(msg)
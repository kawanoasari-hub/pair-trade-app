import yfinance as yf
import json
import requests
from datetime import datetime
import time

# ===== Telegram =====
TOKEN = "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

def send(msg,keyboard=None):

    url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data={
        "chat_id":CHAT_ID,
        "text":msg
    }

    if keyboard:
        data["reply_markup"]=json.dumps(keyboard)

    requests.post(url,data=data)


# ===== データ取得 =====
def get_data(code):

    for i in range(3):

        try:

            df=yf.download(
                code,
                period="6mo",
                interval="1d",
                auto_adjust=True,
                progress=False
            )

            if not df.empty:
                return df

        except:
            pass

        time.sleep(1)

    return None


# ===== 保有銘柄読み込み =====
with open("positions.json","r",encoding="utf-8") as f:
    positions=json.load(f)

positions=[p for p in positions if p["status"]=="open"]

if not positions:

    send("📊 保有銘柄なし")

    exit()


today=datetime.now().date()

send("📊 保有銘柄監視")

for p in positions:

    code=p["code"]
    name=p.get("name",code)
    entry=p["entry_price"]

    entry_date=datetime.strptime(p["entry_date"],"%Y-%m-%d").date()

    days=(today-entry_date).days

    df=get_data(code)

    if df is None:
        continue

    close=df["Close"]

    # ===== 数値化 =====
    price=float(close.iloc[-1].item())

    ma5=close.rolling(5).mean().iloc[-1].item()
    ma25=close.rolling(25).mean().iloc[-1].item()
    ma75=close.rolling(75).mean().iloc[-1].item()

    pnl=(price/entry-1)*100

    action="保有"

    if price < ma75:

        action="❌ 押し目失敗（75日線割れ）"

    elif price > ma25:

        action="◎ 上昇トレンド"

    elif price > ma5:

        action="○ 反発中"


    msg=(
        f"【{name} ({code})】"
        f"\n現在値：{round(price,1)}円（{pnl:+.1f}%）"
        f"\n保有日数：{days}"
        f"\n判断：{action}"
    )


    keyboard={
        "inline_keyboard":[
            [
                {
                    "text":"EXIT",
                    "callback_data":f"exit_stock|{code}"
                }
            ]
        ]
    }

    send(msg,keyboard)
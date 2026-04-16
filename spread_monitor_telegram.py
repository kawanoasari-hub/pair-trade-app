import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import requests
import json
import os
from statsmodels.tsa.stattools import coint

# ===== Telegram =====

TOKEN= "8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID = "7919205087"

def send(msg,keyboard=None):

    url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload={
        "chat_id":CHAT_ID,
        "text":msg
    }

    if keyboard:
        payload["reply_markup"]=keyboard

    requests.post(url,json=payload)


# ===== ポジションファイル =====

PAIR_FILE="positions_pair.json"

def load_pairs():

    if not os.path.exists(PAIR_FILE):
        return []

    with open(PAIR_FILE,"r") as f:
        return json.load(f)


positions=load_pairs()


# ===== 設定 =====

WINDOW=60
ENTRY_Z=1.5
EXIT_Z=0.5
MAX_NOTIFY=3


# ===== セクター =====

sector_map = {
"7203.T":"auto","7267.T":"auto","7269.T":"auto","7270.T":"auto","7211.T":"auto","7201.T":"auto",
"6501.T":"electronics","6503.T":"electronics","6506.T":"electronics","6752.T":"electronics",
"6758.T":"electronics","6762.T":"electronics","6857.T":"electronics","6902.T":"electronics",
"6954.T":"electronics","6971.T":"electronics",
"8035.T":"semiconductor","7735.T":"semiconductor","6920.T":"semiconductor",
"6963.T":"semiconductor","6723.T":"semiconductor","6146.T":"semiconductor",
"9432.T":"telecom","9433.T":"telecom","9434.T":"telecom",
"4689.T":"it","4704.T":"it","4755.T":"it","9766.T":"it","4324.T":"it",
"8001.T":"trading","8002.T":"trading","8015.T":"trading",
"8031.T":"trading","8053.T":"trading","8058.T":"trading",
"8306.T":"bank","8316.T":"bank","8411.T":"bank",
"8331.T":"bank","8334.T":"bank","8354.T":"bank",
"8630.T":"insurance","8725.T":"insurance","8766.T":"insurance",
"5401.T":"steel","5411.T":"steel","5444.T":"steel",
"5711.T":"nonferrous","5713.T":"nonferrous","5802.T":"nonferrous",
"4004.T":"chemicals","4005.T":"chemicals","4063.T":"chemicals","4188.T":"chemicals",
"4204.T":"chemicals","4452.T":"chemicals","3402.T":"chemicals","3407.T":"chemicals",
"4502.T":"pharma","4503.T":"pharma","4519.T":"pharma",
"4523.T":"pharma","4568.T":"pharma","4578.T":"pharma",
"6301.T":"machinery","6302.T":"machinery","6305.T":"machinery",
"6326.T":"machinery","6367.T":"machinery","6471.T":"machinery","6472.T":"machinery",
"1801.T":"construction","1802.T":"construction","1803.T":"construction",
"1812.T":"construction","1925.T":"construction","1928.T":"construction",
"9101.T":"shipping","9104.T":"shipping","9107.T":"shipping",
"1605.T":"energy","5020.T":"energy","5019.T":"energy","5021.T":"energy",
"3382.T":"retail","3092.T":"retail","8233.T":"retail","8252.T":"retail",
"2502.T":"food","2503.T":"food","2802.T":"food","2871.T":"food","2897.T":"food",
"8801.T":"real_estate","8802.T":"real_estate","8830.T":"real_estate","3289.T":"real_estate",
"9064.T":"logistics","9069.T":"logistics","9142.T":"logistics",
"5201.T":"glass","5202.T":"glass","5214.T":"glass",
"7731.T":"precision","7741.T":"precision","7762.T":"precision",
"4901.T":"other","4911.T":"other","5332.T":"other","5333.T":"other",
"6479.T":"other","6586.T":"other",
"1306.T":"etf","1321.T":"etf","1570.T":"etf",
"9020.T":"railway","9021.T":"railway","9022.T":"railway","9005.T":"railway",
"9501.T":"electric","9502.T":"electric","9503.T":"electric",
"9531.T":"gas","9532.T":"gas",
"8951.T":"reit","8952.T":"reit","8960.T":"reit"
}


# ===== ペア候補 =====

pairs=pd.read_csv("pair_candidates.csv")

tickers=list(set(pairs.stock1.tolist()+pairs.stock2.tolist()))

data=yf.download(
    tickers,
    period="6mo",
    auto_adjust=True,
    progress=False
)["Close"].dropna()


# ===== half life =====

def calc_half_life(spread):

    lag=spread.shift(1).bfill()
    delta=spread-lag

    model=sm.OLS(delta,sm.add_constant(lag)).fit()

    hl=-np.log(2)/model.params.iloc[1]

    if hl<0:
        hl=100

    return hl


# ===== hurst =====

def hurst(ts):

    lags=range(2,20)
    tau=[]

    for lag in lags:

        diff=np.subtract(ts[lag:],ts[:-lag])
        std=np.std(diff)

        if std==0:
            std=1e-8

        tau.append(std)

    poly=np.polyfit(np.log(lags),np.log(tau),1)

    return poly[0]*2


results=[]


# ===== メイン =====

for _,row in pairs.iterrows():

    s1=row.stock1
    s2=row.stock2

    pair_name=f"{s1}_{s2}"

    if any(p.get("pair")==pair_name and p.get("status")=="open" for p in positions):
        continue

    try:
        price1=data[s1].tail(WINDOW)
        price2=data[s2].tail(WINDOW)
    except:
        continue

    if len(price1)<WINDOW:
        continue

    log1=np.log(price1)
    log2=np.log(price2)

    model=sm.OLS(log1,sm.add_constant(log2)).fit()
    beta=model.params.iloc[1]

    spread=log1-beta*log2

    mean=spread.mean()
    std=spread.std()

    if std==0:
        continue

    z=(spread.iloc[-1]-mean)/std
    z_prev=(spread.iloc[-2]-mean)/std

    if abs(z) > abs(z_prev):
        continue

    if abs(z)<ENTRY_Z:
        continue

    recent_spread = spread.tail(10)
    if recent_spread.std() > spread.std()*1.5:
        continue

    betas=[]
    for i in range(20):
        sub1=log1[i:]
        sub2=log2[i:]
        if len(sub1)<30:
            continue
        m=sm.OLS(sub1,sm.add_constant(sub2)).fit()
        betas.append(m.params.iloc[1])

    if len(betas)<5 or np.std(betas)>0.1:
        continue

    vol=spread.std()
    half=calc_half_life(spread)
    corr=price1.corr(price2)
    h=hurst(spread)

    if h>0.6:
        continue

    try:
        score,pvalue,_=coint(log1,log2)
    except:
        continue

    quality=0
    quality+=-np.log10(pvalue+1e-6)*15
    quality+=(1/(half+1))*40
    quality+=(1/(vol+0.001))*2
    quality+=abs(corr)*20

    if sector_map.get(s1)==sector_map.get(s2):
        quality*=1.3

    entry_score=quality*abs(z)

    side1="BUY" if z<0 else "SELL"
    side2="SELL" if z<0 else "BUY"

    price_now1=price1.iloc[-1]
    price_now2=price2.iloc[-1]

    # ===== ロット計算 =====
    if price_now1 > price_now2:
        high_price, low_price = price_now1, price_now2
        high_stock = s1
    else:
        high_price, low_price = price_now2, price_now1
        high_stock = s2

    shares_high = 100

    target_low = shares_high * (high_price / low_price) * abs(beta)

    candidates = list(range(100, 1000, 100))

    shares_low = min(candidates, key=lambda x: abs(x - target_low))

    if s1 == high_stock:
        qty1, qty2 = shares_high, shares_low
    else:
        qty1, qty2 = shares_low, shares_high

    # ===== 資金制約（追加🔥） =====
    MAX_SINGLE = 1_500_000
    MAX_CAPITAL = 2_000_000

    value1 = price_now1 * qty1
    value2 = price_now2 * qty2

    if value1 > MAX_SINGLE or value2 > MAX_SINGLE:
        continue

    if value1 + value2 > MAX_CAPITAL:
        continue

    # ===== 資金＆期待利益 =====
    capital = price_now1*qty1 + price_now2*qty2

    z_move = abs(z) - EXIT_Z
    spread_move = z_move * std

    position_value = (
        price_now1*qty1 +
        abs(beta)*price_now2*qty2
    )

    expected_profit = spread_move * position_value
    expected_return=(expected_profit/capital)*100

    results.append({
        "pair":pair_name,
        "s1":s1,
        "s2":s2,
        "z":z,
        "beta":beta,
        "corr":corr,
        "half":half,
        "vol":vol,
        "hurst":h,
        "quality":quality,
        "score":entry_score,
        "profit":expected_profit,
        "ret":expected_return,
        "side1":side1,
        "side2":side2,
        "qty1":qty1,
        "qty2":qty2,
        "capital":capital
    })


# ===== ランキング =====

if len(results)==0:
    send("ENTRY候補なし")
    exit()

df=pd.DataFrame(results)
df=df.sort_values("score",ascending=False)

top=df.head(MAX_NOTIFY)


# ===== 通知 =====

rank=1

for _,r in top.iterrows():

    msg=(

    f"📊 ペアトレード ENTRYランキング\n\n"

    f"{rank}️⃣ {r['pair']}\n"
    f"Zscore {r['z']:.2f}\n"
    f"β {r['beta']:.2f}\n"
    f"corr {r['corr']:.2f}\n"
    f"half-life {r['half']:.1f}\n"
    f"hurst {r['hurst']:.2f}\n"
    f"vol {r['vol']:.3f}\n\n"

    f"{r['s1']} {r['side1']} {r['qty1']}株\n"
    f"{r['s2']} {r['side2']} {r['qty2']}株\n\n"

    f"必要資金 約{int(r['capital']):,}円\n"
    f"想定利益 約{int(r['profit']):,}円\n"
    f"期待リターン {r['ret']:.2f}%\n\n"

    f"quality {r['quality']:.1f}\n"
    f"entry score {r['score']:.1f}\n"

    )

    keyboard={
        "inline_keyboard":[[
            {
            "text":"ENTRY",
            "callback_data":f"entry|{r['s1']}|{r['s2']}|{r['beta']}|{r['z']}"
            }
        ]]
    }

    send(msg,keyboard)

    rank+=1
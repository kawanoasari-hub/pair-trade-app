import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import itertools
import json
import math

# ===== 設定 =====
LOOKBACK = 120
MIN_CORR = 0.6
MAX_HALF_LIFE = 20
MIN_HALF_LIFE = 2
MAX_PRICE = 10000
MIN_PRICE = 300

OUTPUT_FILE = "pair_candidates.csv"

# ===== 銘柄リスト =====
tickers = [

# ===== 自動車 =====
"7203.T","7267.T","7269.T","7270.T","7211.T","7201.T",

# ===== 電機 =====
"6501.T","6503.T","6506.T","6752.T","6758.T","6762.T","6857.T","6902.T","6954.T","6971.T",

# ===== 半導体 =====
"8035.T","7735.T","6920.T","6963.T","6723.T","6146.T",

# ===== 通信 =====
"9432.T","9433.T","9434.T",

# ===== IT =====
"4689.T","4704.T","4755.T","9766.T","4324.T",

# ===== 商社 =====
"8001.T","8002.T","8015.T","8031.T","8053.T","8058.T",

# ===== 銀行 =====
"8306.T","8316.T","8411.T","8331.T","8334.T","8354.T",

# ===== 保険 =====
"8630.T","8725.T","8766.T",

# ===== 鉄鋼 =====
"5401.T","5411.T","5444.T",

# ===== 非鉄 =====
"5711.T","5713.T","5802.T",

# ===== 化学 =====
"4004.T","4005.T","4063.T","4188.T","4204.T","4452.T","3402.T","3407.T",

# ===== 医薬 =====
"4502.T","4503.T","4519.T","4523.T","4568.T","4578.T",

# ===== 機械 =====
"6301.T","6302.T","6305.T","6326.T","6367.T","6471.T","6472.T",

# ===== 建設 =====
"1801.T","1802.T","1803.T","1812.T","1925.T","1928.T",

# ===== 海運 =====
"9101.T","9104.T","9107.T",

# ===== エネルギー =====
"1605.T","5020.T","5019.T","5021.T",

# ===== 小売 =====
"3382.T","3092.T","8233.T","8252.T",

# ===== 食品 =====
"2502.T","2503.T","2802.T","2871.T","2897.T",

# ===== 不動産 =====
"8801.T","8802.T","8830.T","3289.T",

# ===== 物流 =====
"9064.T","9069.T","9142.T",

# ===== ガラス =====
"5201.T","5202.T","5214.T",

# ===== 精密 =====
"7731.T","7741.T","7762.T",

# ===== その他 =====
"4901.T","4911.T","5332.T","5333.T","6479.T","6586.T",


# =========================
# 🔥 ここから追加
# =========================

# ===== ETF（最重要）=====
"1306.T","1321.T","1570.T",

# ===== 鉄道（安定ペア）=====
"9020.T","9021.T","9022.T","9005.T",

# ===== 電力（超安定）=====
"9501.T","9502.T","9503.T",

# ===== ガス =====
"9531.T","9532.T",

# ===== REIT（分散用）=====
"8951.T","8952.T","8960.T"

]

print("Downloading price data...")

data = yf.download(
    tickers,
    period="1y",
    auto_adjust=True,
    progress=False
)["Close"]

data = data.dropna(axis=1)

tickers = list(data.columns)

print("Total tickers:", len(tickers))

results = []

# ===== half life =====
def calc_half_life(spread):

    spread_lag = spread.shift(1).bfill()
    delta = spread - spread_lag

    model = sm.OLS(delta, sm.add_constant(spread_lag)).fit()

    beta = model.params.iloc[1]

    if beta >= 0:
        return 999

    hl = -np.log(2) / beta

    return hl


# ===== ペア探索 =====
pairs = list(itertools.combinations(tickers,2))

print("Checking pairs:", len(pairs))

for s1, s2 in pairs:

    try:

        price1 = data[s1].dropna()
        price2 = data[s2].dropna()

        df = pd.concat([price1,price2],axis=1).dropna()

        if len(df) < LOOKBACK:
            continue

        price1 = df[s1].tail(LOOKBACK)
        price2 = df[s2].tail(LOOKBACK)

        # 価格フィルター
        if price1.iloc[-1] > MAX_PRICE or price2.iloc[-1] > MAX_PRICE:
            continue

        if price1.iloc[-1] < MIN_PRICE or price2.iloc[-1] < MIN_PRICE:
            continue

        # 相関
        corr = price1.corr(price2)

        if corr < MIN_CORR:
            continue

        log1 = np.log(price1)
        log2 = np.log(price2)

        # cointegration
        score, pvalue, _ = coint(log1, log2)

        if pvalue > 0.05:
            continue

        # hedge ratio
        model = sm.OLS(log1, sm.add_constant(log2)).fit()
        beta = model.params.iloc[1]

        spread = log1 - beta*log2

        # half life
        hl = calc_half_life(spread)

        if hl < MIN_HALF_LIFE or hl > MAX_HALF_LIFE:
            continue

        # volatility
        vol = spread.std()

        # Zscore
        z = (spread.iloc[-1] - spread.mean()) / spread.std()

        # rolling correlation
        roll_corr = price1.tail(60).corr(price2.tail(60))

        if roll_corr < 0.5:
            continue

        # 資金チェック
        capital = (price1.iloc[-1] + price2.iloc[-1]) * 100

        if capital > 2000000:
            continue

        # スコア
        score = (
            abs(z)*40
            + (1/hl)*30
            + corr*20
            + (1/vol)*10
        )

        results.append({
            "stock1":s1,
            "stock2":s2,
            "corr":round(corr,3),
            "pvalue":round(pvalue,4),
            "beta":round(beta,3),
            "half_life":round(hl,2),
            "vol":round(vol,4),
            "zscore":round(z,2),
            "score":round(score,2),
            "capital":int(capital)
        })

    except:
        continue


df = pd.DataFrame(results)

if len(df)==0:
    print("No pairs found")
    exit()

df = df.sort_values("score",ascending=False)

df.to_csv(OUTPUT_FILE,index=False)

print("Saved:",OUTPUT_FILE)

print(df.head(10))
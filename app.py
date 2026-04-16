import streamlit as st
import json
import os
import yfinance as yf

# ======================
# 🔐 パスワード保護
# ======================
PASSWORD = os.getenv("APP_PASSWORD", "Epidote2357")  # Renderで上書き可能

pw = st.text_input("パスワードを入力", type="password")

if pw != PASSWORD:
    st.warning("パスワードが違います")
    st.stop()

# ======================
# 画面設定
# ======================
st.set_page_config(page_title="ペアトレBot", layout="wide")

st.title("📊 ペアトレード管理アプリ")

PAIR_FILE = "positions_pair.json"

# ======================
# JSON読み込み
# ======================
def load_pairs():
    if not os.path.exists(PAIR_FILE):
        return []
    with open(PAIR_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

pairs = load_pairs()

open_pairs = [p for p in pairs if p["status"] == "open"]

# ======================
# 表示
# ======================
if len(open_pairs) == 0:
    st.info("ポジションなし")
    st.stop()

for p in open_pairs:

    s1 = p["stock1"]
    s2 = p["stock2"]

    col1, col2, col3 = st.columns(3)

    # 株価取得
    try:
        price1 = yf.Ticker(s1).fast_info["lastPrice"]
        price2 = yf.Ticker(s2).fast_info["lastPrice"]
    except:
        price1, price2 = None, None

    # 損益計算
    if price1 and price2:

        side1 = p["side1"].lower()
        side2 = p["side2"].lower()

        pnl1 = (price1 - p["entry_price1"]) * p["qty1"] if side1 == "buy" else (p["entry_price1"] - price1) * p["qty1"]
        pnl2 = (p["entry_price2"] - price2) * p["qty2"] if side2 == "sell" else (price2 - p["entry_price2"]) * p["qty2"]

        total = pnl1 + pnl2

    else:
        total = 0

    # 表示
    with col1:
        st.subheader(f"{s1} / {s2}")
        st.write(f"{p['side1']} {p['qty1']}株")
        st.write(f"{p['side2']} {p['qty2']}株")

    with col2:
        st.metric("損益", f"{int(total):,} 円")

    with col3:
        if st.button("EXIT", key=f"{s1}_{s2}"):
            st.warning("※ 実際の決済処理は別途実装してください")
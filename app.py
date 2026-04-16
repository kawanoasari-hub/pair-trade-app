import streamlit as st
import json
import os

PAIR_FILE = "positions_pair.json"

def load_pairs():
    if not os.path.exists(PAIR_FILE):
        return []
    with open(PAIR_FILE, "r") as f:
        return json.load(f)

st.set_page_config(
    page_title="ペアトレBot",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ペアトレBot")

pairs = load_pairs()

if len(pairs) == 0:
    st.write("ポジションなし")
else:
    for p in pairs:
        if p["status"] == "open":
            st.subheader(p["pair"])

            st.write(f"stock1: {p['stock1']} ({p['side1']})")
            st.write(f"stock2: {p['stock2']} ({p['side2']})")

            if st.button(f"EXIT {p['pair']}"):
                st.write("EXIT処理（あとで接続）")
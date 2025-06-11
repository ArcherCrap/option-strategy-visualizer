from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import io

# ---- Option and Stock Classes ----

class Option:
    def __init__(self, position, option_type, strike, premium):
        self.position = position
        self.option_type = option_type
        self.strike = float(strike)
        self.premium = float(premium)

    def payoff(self, S):
        intrinsic = np.maximum(S - self.strike, 0) if self.option_type == "call" else np.maximum(self.strike - S, 0)
        return intrinsic - self.premium if self.position == "long" else -intrinsic + self.premium

    def label(self):
        return f"{self.position.title()} {self.option_type.title()} (K={self.strike}, P={self.premium})"


class Stock:
    def __init__(self, position, entry_price):
        self.position = position
        self.entry_price = float(entry_price)

    def payoff(self, S):
        return S - self.entry_price if self.position == "buy" else self.entry_price - S

    def label(self):
        return f"{self.position.title()} Stock (Entry={self.entry_price})"


# ---- Plotting Function ----

def plot_strategy(options, stocks, s_min, s_max):
    S = np.linspace(s_min, s_max, 1001)
    net = np.zeros_like(S)

    fig, ax = plt.subplots()
    for leg in options + stocks:
        payoff = leg.payoff(S)
        net += payoff
        ax.plot(S, payoff, label=leg.label())

    ax.plot(S, net, 'k--', linewidth=2.5, label="Net Payoff")
    ax.axhline(0, color="black", linewidth=0.8, linestyle='--')
    ax.set_title("Payoff at Expiry")
    ax.set_xlabel("Underlying Price ($S$)")
    ax.set_ylabel("Profit / Loss")
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend()
    st.pyplot(fig)
    return S, net, fig


# ---- Streamlit App ----

st.set_page_config(layout="wide", page_title="Option Strategy Visualizer")
st.title("📊 Option Strategy Visualizer")

# Sidebar: strategy config load/save
st.sidebar.header("💾 Save / Load Strategy")
strategy_file = st.sidebar.text_input("File name (CSV):", "my_strategy.csv")

if st.sidebar.button("💾 Save"):
    data = []
    for i, opt in enumerate(st.session_state.get("options", [])):
        data.append(["option", opt.position, opt.option_type, opt.strike, opt.premium])
    for stk in st.session_state.get("stocks", []):
        data.append(["stock", stk.position, "", stk.entry_price, 0])
    df = pd.DataFrame(data, columns=["type", "position", "option_type", "strike_or_entry", "premium"])
    df.to_csv(strategy_file, index=False)
    st.sidebar.success("Saved!")

if st.sidebar.button("📂 Load"):
    try:
        df = pd.read_csv(strategy_file)
        st.session_state["options"] = []
        st.session_state["stocks"] = []
        for _, row in df.iterrows():
            if row["type"] == "option":
                st.session_state["options"].append(
                    Option(row["position"], row["option_type"], row["strike_or_entry"], row["premium"]))
            else:
                st.session_state["stocks"].append(
                    Stock(row["position"], row["strike_or_entry"]))
        st.sidebar.success("Loaded!")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")

# Defaults
if "options" not in st.session_state:
    st.session_state.options = []
if "stocks" not in st.session_state:
    st.session_state.stocks = []

# Add/remove legs
st.sidebar.header("➕ Add Legs")
add_type = st.sidebar.selectbox("Add...", ["Option", "Stock"])
if add_type == "Option":
    pos = st.sidebar.selectbox("Position", ["long", "short"], key="add_pos")
    typ = st.sidebar.selectbox("Type", ["call", "put"], key="add_typ")
    k = st.sidebar.number_input("Strike", min_value=0.0, step=1.0, key="add_strike")
    p = st.sidebar.number_input("Premium", min_value=0.0, step=0.1, key="add_premium")
    if st.sidebar.button("Add Option"):
        st.session_state.options.append(Option(pos, typ, k, p))
elif add_type == "Stock":
    pos = st.sidebar.selectbox("Position", ["buy", "sell"], key="stock_pos")
    ep = st.sidebar.number_input("Entry Price", min_value=0.0, step=1.0, key="stock_entry")
    if st.sidebar.button("Add Stock"):
        st.session_state.stocks.append(Stock(pos, ep))

# Remove leg
st.sidebar.header("🗑 Remove Leg")
all_labels = [o.label() for o in st.session_state.options] + [s.label() for s in st.session_state.stocks]
remove_idx = st.sidebar.selectbox("Select to remove", options=list(range(len(all_labels))),
                                  format_func=lambda i: all_labels[i])
if st.sidebar.button("Remove"):
    if remove_idx < len(st.session_state.options):
        del st.session_state.options[remove_idx]
    else:
        del st.session_state.stocks[remove_idx - len(st.session_state.options)]

# Plot range
st.sidebar.header("⚙️ Plot Settings")
s_min = st.sidebar.number_input("Price Min", value=0.0)
s_max = st.sidebar.number_input("Price Max", value=200.0)

# Plot
st.subheader("📈 Strategy Payoff")

# --- draw chart & collect data -------------------------------------------
# plot_strategy now returns (S, net, fig)
S, net, fig = plot_strategy(
    st.session_state.options,
    st.session_state.stocks,
    s_min,
    s_max,
)

# ------------------------------------------------------------------------
# 📤 EXPORT SECTION
# ------------------------------------------------------------------------
st.subheader("📤 Export")

# --- PNG download -------------------------------------------------------
import io
png_buf = io.BytesIO()
fig.savefig(png_buf, format="png", bbox_inches="tight")
png_buf.seek(0)
st.download_button(
    label="⬇️ Download PNG",
    data=png_buf,
    file_name="payoff.png",
    mime="image/png",
)

# --- CSV download -------------------------------------------------------
df_export = pd.DataFrame({"Spot": S, "Net_Payoff": net})
csv_bytes = df_export.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download CSV",
    data=csv_bytes,
    file_name="payoff_data.csv",
    mime="text/csv",
)

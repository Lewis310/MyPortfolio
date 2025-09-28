# streamlit_portfolio_av.py
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="Stock Portfolio + Projection")

API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]

# ---- Helpers ----
@st.cache_data(ttl=3600)
def fetch_daily_prices(symbol: str):
    """Fetch daily adjusted close from Alpha Vantage"""
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "apikey": API_KEY,
        "outputsize": "compact"
    }
    r = requests.get(url, params=params)
    data = r.json()
    if "Time Series (Daily)" not in data:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index", dtype=float)
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns={"5. adjusted close": "Adj Close"})
    return df[["Adj Close"]].sort_index()

def annualized_return(series: pd.Series):
    s = series.dropna()
    if len(s) < 2:
        return np.nan
    logrets = np.log(s / s.shift(1)).dropna()
    return np.exp(logrets.mean() * 252) - 1

def get_current_price(symbol: str):
    df = fetch_daily_prices(symbol)
    if df.empty:
        return np.nan
    return float(df["Adj Close"].iloc[-1])

# ---- UI ----
st.title("📊 Portfolio Tracker (Alpha Vantage API)")

# Default holdings
default_portfolio = pd.DataFrame([
    {"Ticker": "NDQ.AX", "Units": 10, "Purchase Price": 20.0},
    {"Ticker": "CBA.AX", "Units": 5,  "Purchase Price": 90.0},
    {"Ticker": "IVV",    "Units": 8,  "Purchase Price": 350.0},
])

st.markdown("### Portfolio holdings")
edited = st.experimental_data_editor(default_portfolio, num_rows="dynamic", key="portfolio_editor")
edited["Units"] = edited["Units"].astype(int)

# Fetch prices
tickers = edited["Ticker"].tolist()
price_data = {t: fetch_daily_prices(t) for t in tickers}
current_prices = {t: get_current_price(t) for t in tickers}

# Portfolio calculations
holdings = edited.copy()
holdings["Current Price"] = holdings["Ticker"].map(current_prices)
holdings["Current Value"] = holdings["Units"] * holdings["Current Price"]
holdings["Cost Basis"] = holdings["Units"] * holdings["Purchase Price"]
holdings["P/L ($)"] = holdings["Current Value"] - holdings["Cost Basis"]
holdings["P/L (%)"] = (holdings["P/L ($)"] / holdings["Cost Basis"]) * 100

st.dataframe(holdings, height=250)

# ---- Portfolio historical + projection ----
combined = pd.concat(
    [df.rename(columns={"Adj Close": t}) for t, df in price_data.items() if not df.empty],
    axis=1
).fillna(method="ffill")

# Weighted value series
value_series = pd.Series(0, index=combined.index, dtype=float)
for t in tickers:
    units = holdings.loc[holdings["Ticker"] == t, "Units"].values[0]
    if t in combined.columns:
        value_series += combined[t] * units

# Expected return
ann_returns = {t: annualized_return(combined[t]) for t in tickers if t in combined}
weights = {t: (holdings.loc[holdings["Ticker"] == t, "Current Value"].values[0]) for t in tickers}
total_val = sum(weights.values())
port_return = sum((weights[t]/total_val)*ann_returns.get(t,0) for t in tickers if total_val > 0)

# Projection
last_val = value_series.iloc[-1]
proj_dates = pd.date_range(value_series.index[-1], value_series.index[-1] + pd.Timedelta(days=365), freq="D")
daily_factor = (1 + port_return) ** (1/365) if port_return else 1
proj_vals = last_val * (daily_factor ** np.arange(len(proj_dates)))

# Combine into one DataFrame
proj_series = pd.Series(proj_vals, index=proj_dates, name="Expected")
hist_series = pd.Series(value_series, name="Historical")
chart_df = pd.concat([hist_series, proj_series], axis=1)

st.markdown("### Portfolio Value (Historical + 1yr Projection)")
st.line_chart(chart_df)


# streamlit_portfolio.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="Stock Portfolio + 1yr Projection")

# ---- Helpers ----
@st.cache_data(ttl=60)  # cache for a minute to avoid too many yfinance calls in quick succession
def fetch_history(tickers, period="2y", interval="1d"):
    data = yf.download(tickers=tickers, period=period, interval=interval, group_by='ticker', auto_adjust=True, threads=True)
    # Make uniform: return dict ticker -> df with Date index and 'Close' column
    out = {}
    if len(tickers) == 1:
        df = data.copy()
        df = df.rename(columns={"Close": "Adj Close"}) if "Close" in df.columns else df
        out[tickers[0]] = df[["Adj Close"]].rename(columns={"Adj Close": "Adj Close"})
        return out
    for t in tickers:
        try:
            dfi = data[t].copy()
            # yfinance sometimes names adjusted close 'Adj Close' or auto_adjust did it already as 'Close'
            if 'Adj Close' in dfi.columns:
                out[t] = dfi[['Adj Close']].rename(columns={'Adj Close': 'Adj Close'})
            elif 'Close' in dfi.columns:
                out[t] = dfi[['Close']].rename(columns={'Close': 'Adj Close'})
            else:
                out[t] = pd.DataFrame(columns=['Adj Close'])
        except Exception:
            out[t] = pd.DataFrame(columns=['Adj Close'])
    return out

@st.cache_data(ttl=30)
def fetch_current_prices(tickers):
    # use yf.Tickers for efficient retrieval
    tk = yf.Tickers(" ".join(tickers))
    prices = {}
    for t in tickers:
        try:
            info = tk.tickers[t].history(period="1d", interval="1d", auto_adjust=True)
            if not info.empty:
                prices[t] = float(info['Close'].iloc[-1])
            else:
                # fallback to fast info
                ticker = yf.Ticker(t)
                prices[t] = float(ticker.info.get('regularMarketPrice', np.nan))
        except Exception:
            try:
                ticker = yf.Ticker(t)
                prices[t] = float(ticker.info.get('regularMarketPrice', np.nan))
            except Exception:
                prices[t] = np.nan
    return prices

def annualized_return_from_series(price_series):
    # compute log returns and annualize (assumes daily frequency ~252 trading days)
    s = price_series.dropna()
    if len(s) < 2:
        return np.nan
    logrets = np.log(s / s.shift(1)).dropna()
    mean_daily = logrets.mean()
    ann = np.exp(mean_daily * 252) - 1
    return ann

# ---- UI ----
st.title("📈 Portfolio: current & 1-year expected projection (Streamlit)")

col1, col2 = st.columns([2, 1])

with col2:
    st.markdown("**Controls**")
    history_years = st.slider("History window (years)", 1, 5, 2)
    history_days = int(history_years * 365)
    period = f"{history_years}y"
    refresh = st.button("Refresh data")

# Default portfolio table
default_portfolio = pd.DataFrame([
    {"Ticker": "NDQ.AX", "Units": 10, "Purchase Price": 20.0},
    {"Ticker": "CBA.AX", "Units": 5,  "Purchase Price": 90.0},
    {"Ticker": "IVV",    "Units": 8,  "Purchase Price": 350.0},
])

st.markdown("### Portfolio holdings (edit units as integers and purchase prices)")
edited = st.experimental_data_editor(default_portfolio, num_rows="dynamic", key="portfolio_editor")

# Validate types: ensure Units integer
edited['Units'] = edited['Units'].fillna(0).astype(int, errors='ignore')
edited['Purchase Price'] = edited['Purchase Price'].astype(float, errors='ignore').fillna(0.0)
tickers = edited['Ticker'].unique().tolist()

# Fetch data
with st.spinner("Fetching prices & history..."):
    history_dict = fetch_history(tickers, period=period, interval="1d")
    current_prices = fetch_current_prices(tickers)

# Build holdings table with current prices
holdings = edited.copy()
holdings['Current Price'] = holdings['Ticker'].map(current_prices)
holdings['Current Value'] = holdings['Units'] * holdings['Current Price']
holdings['Cost Basis'] = holdings['Units'] * holdings['Purchase Price']
holdings['P/L ($)'] = holdings['Current Value'] - holdings['Cost Basis']
holdings['P/L (%)'] = np.where(holdings['Cost Basis'] > 0,
                                (holdings['Current Value'] / holdings['Cost Basis'] - 1) * 100,
                                np.nan)

total_current_value = holdings['Current Value'].sum()
total_cost = holdings['Cost Basis'].sum()
total_pl = holdings['P/L ($)'].sum()
total_pl_pct = (total_current_value / total_cost - 1) * 100 if total_cost else np.nan

st.markdown("### Portfolio summary")
st.metric("Total current value (AUD / USD depending on ticker)", f"{total_current_value:,.2f}",
          delta=f"{total_pl:,.2f} ({total_pl_pct:.2f}%)")

st.dataframe(holdings.style.format({"Current Price":"{:.2f}", "Current Value":"{:.2f}", "Purchase Price":"{:.2f}", "P/L ($)":"{:.2f}", "P/L (%)":"{:.2f}%"}),
             height=250)

# --- Historical portfolio value ---
st.markdown("### Historical portfolio value and 1-year expected projection")

# Build historical portfolio time series (aligned on dates)
# Create a DataFrame with index = union of all dates
price_frames = []
for t in tickers:
    df = history_dict.get(t, pd.DataFrame())
    if df is None or df.empty:
        continue
    df = df.rename(columns={'Adj Close': t})
    price_frames.append(df[t])

if price_frames:
    prices_df = pd.concat(price_frames, axis=1).sort_index()
    # forward/backfill missing values conservatively
    prices_df = prices_df.fillna(method='ffill').fillna(method='bfill')
    # Calculate portfolio daily value
    units_map = holdings.set_index('Ticker')['Units'].to_dict()
    value_series = pd.Series(0.0, index=prices_df.index)
    for t in prices_df.columns:
        value_series += prices_df[t] * units_map.get(t, 0)
    value_series = value_series.dropna()
else:
    value_series = pd.Series(dtype=float)

# Compute annualized returns per ticker (based on price history)
ann_returns = {}
for t in prices_df.columns:
    ann_returns[t] = annualized_return_from_series(prices_df[t])

# Portfolio expected annual return: value-weighted average of tickers' ann returns (weights by current market value)
weights = {}
for t in prices_df.columns:
    cur_price = current_prices.get(t, np.nan)
    units = units_map.get(t, 0)
    weights[t] = (cur_price * units) if (not np.isnan(cur_price) and units) else 0.0
w_total = sum(weights.values()) if sum(weights.values()) != 0 else 1.0
for t in weights:
    weights[t] = weights[t] / w_total

# compute portfolio annualized expected return
port_ann_return = 0.0
for t in prices_df.columns:
    r = ann_returns.get(t, np.nan)
    if np.isnan(r):
        r = 0.0
    port_ann_return += weights.get(t, 0.0) * r

# Project forward: create a straight-line projection over one year using compound growth
last_date = value_series.index[-1] if not value_series.empty else pd.Timestamp.today()
proj_end_date = last_date + pd.Timedelta(days=365)
proj_index = pd.date_range(start=last_date, end=proj_end_date, freq='D')

# create projected series: assume continuous compound at port_ann_return
if not value_series.empty:
    last_val = float(value_series.iloc[-1])
    days = (proj_index - last_date).days.values
    # continuous compounding using daily factor derived from annual return
    daily_factor = (1 + port_ann_return) ** (1 / 365) if (1 + port_ann_return) > 0 else 1.0
    proj_values = last_val * (daily_factor ** days)
    # combine historical and projection for plotting (keep historical as is)
    hist_index = value_series.index
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_index, y=value_series.values, mode='lines', name='Historical portfolio value'))
    fig.add_trace(go.Scatter(x=proj_index, y=proj_values, mode='lines', name=f'Expected (1yr) — ann return {port_ann_return*100:.2f}%'))
    fig.update_layout(title="Portfolio value (historical) + 1 year expected projection",
                      xaxis_title="Date", yaxis_title="Portfolio value (currency of ticker prices)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough historical price data to build portfolio chart. Check tickers / network.")

# --- Technology stock watchlist (scroll table) ---
st.markdown("### Tech company watchlist (scrollable)")
default_tech = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "ASML", "TSM", "SAP"]
tech_text = st.text_area("Edit tech tickers (comma separated)", value=", ".join(default_tech), height=50)
tech_list = [t.strip().upper() for t in tech_text.split(",") if t.strip()]

tech_prices = fetch_current_prices(tech_list)
tech_df = pd.DataFrame({
    "Ticker": tech_list,
    "Current Price": [tech_prices.get(t, np.nan) for t in tech_list]
})
# Display as scrollable table
st.dataframe(tech_df.style.format({"Current Price":"{:.2f}"}), height=300)

# --- Allow user to add a custom holding quickly ---
st.markdown("### Quick add a holding")
with st.form("quick_add"):
    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        new_ticker = st.text_input("Ticker (e.g., AAPL or NDQ.AX)", "")
    with c2:
        new_units = st.number_input("Units (integer)", min_value=0, value=0, step=1)
    with c3:
        new_price = st.number_input("Purchase Price (per unit)", min_value=0.0, value=0.0, step=0.01)
    submitted = st.form_submit_button("Add to portfolio (adds a new row in the editor above)")
    if submitted and new_ticker:
        # append new row to the data editor by writing to session state: we'll update the editor's underlying DataFrame
        df = st.session_state.get("portfolio_editor", default_portfolio)
        if isinstance(df, pd.DataFrame):
            df2 = df.append({"Ticker": new_ticker.upper(), "Units": int(new_units), "Purchase Price": float(new_price)}, ignore_index=True)
            st.session_state["portfolio_editor"] = df2
            st.success(f"Added {new_ticker.upper()} — refresh the editor above if you don't see it.")

st.markdown("---")
st.markdown("#### Notes / assumptions")
st.markdown("""
- Prices and history are fetched via `yfinance` (no API key); tickers must match Yahoo Finance format (`.AX` for ASX).
- *Expected 1-year projection* is a **statistical projection**: annualized return estimated from historical daily returns (value-weighted across holdings). It's **not a guarantee**.
- All amounts shown are in the native quote currency for each ticker (mixing USD/AUD may appear in totals). If you want currency normalization (e.g., convert all to AUD), we can add FX conversion.
- Units must be integer; purchase prices are per-unit.
""")

st.markdown("### Export / Save")
if st.button("Download holdings CSV"):
    csv = holdings.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name="holdings.csv", mime="text/csv")

st.caption("Built with Streamlit + yfinance — tweak the tickers and layout as needed.")

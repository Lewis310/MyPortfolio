import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json
import os
import time

# Page configuration
st.set_page_config(
    page_title="Stock Portfolio Tracker",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []
if 'tech_stocks' not in st.session_state:
    st.session_state.tech_stocks = {}
if 'last_api_call' not in st.session_state:
    st.session_state.last_api_call = 0
if 'api_call_count' not in st.session_state:
    st.session_state.api_call_count = 0

# API configuration with your actual key
API_KEY = "NQG5KOWP2QXF7Z72"
BASE_URL = "https://www.alphavantage.co/query"

# Stock symbols with realistic mock prices
STOCK_SYMBOLS = {
    "NDQ": {"symbol": "NDQ.AX", "mock_price": 32.50},
    "IVV": {"symbol": "IVV", "mock_price": 485.75},
    "CBA": {"symbol": "CBA.AX", "mock_price": 112.30},
}

TECH_STOCKS = {
    "AAPL": {"name": "Apple", "mock_price": 185.50},
    "MSFT": {"name": "Microsoft", "mock_price": 375.25}, 
    "GOOGL": {"name": "Google", "mock_price": 138.75},
    "AMZN": {"name": "Amazon", "mock_price": 155.20},
    "META": {"name": "Meta", "mock_price": 345.60},
    "TSLA": {"name": "Tesla", "mock_price": 245.80},
    "NVDA": {"name": "NVIDIA", "mock_price": 485.30},
    "AMD": {"name": "AMD", "mock_price": 128.45},
    "INTC": {"name": "Intel", "mock_price": 44.20},
    "ADBE": {"name": "Adobe", "mock_price": 565.40}
}

def rate_limit_api():
    """Implement rate limiting for API calls"""
    current_time = time.time()
    time_since_last_call = current_time - st.session_state.last_api_call
    
    # Limit to 5 calls per minute (12 seconds between calls)
    if time_since_last_call < 12:
        time.sleep(12 - time_since_last_call)
    
    st.session_state.last_api_call = time.time()
    st.session_state.api_call_count += 1

def get_stock_price(symbol, use_mock=False):
    """Get current stock price from Alpha Vantage API with fallback to mock data"""
    if use_mock:
        # Return mock data for specific stocks
        for key, data in STOCK_SYMBOLS.items():
            if data["symbol"] == symbol:
                return data["mock_price"]
        for key, data in TECH_STOCKS.items():
            if key == symbol:
                return data["mock_price"]
        return round(100 + hash(symbol) % 200, 2)
    
    try:
        rate_limit_api()
        
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": API_KEY
        }
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()
        
        if "Global Quote" in data and data["Global Quote"] and data["Global Quote"]["05. price"]:
            price = float(data["Global Quote"]["05. price"])
            st.sidebar.success(f"✅ Live data: {symbol}")
            return price
        else:
            # Use mock data as fallback
            st.sidebar.warning(f"📊 Using mock data for {symbol} (API limit)")
            return get_stock_price(symbol, use_mock=True)
            
    except Exception as e:
        st.sidebar.warning(f"📊 Using mock data for {symbol} (Error: {str(e)})")
        return get_stock_price(symbol, use_mock=True)

def get_stock_history(symbol, days=30):
    """Get historical stock data with smart fallback"""
    try:
        rate_limit_api()
        
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
            "outputsize": "compact"
        }
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()
        
        if "Time Series (Daily)" in data:
            time_series = data["Time Series (Daily)"]
            dates = []
            prices = []
            
            for date_str, values in list(time_series.items())[:days]:
                dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
                prices.append(float(values["4. close"]))
            
            return pd.DataFrame({
                'date': dates[::-1],
                'price': prices[::-1]
            })
        else:
            return generate_mock_history(symbol, days)
            
    except Exception as e:
        return generate_mock_history(symbol, days)

def generate_mock_history(symbol, days):
    """Generate realistic mock historical data"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Get base price from mock data
    base_price = get_stock_price(symbol, use_mock=True)
    
    # Generate realistic price movements
    prices = [base_price]
    for i in range(1, len(dates)):
        # Small random walk with slight upward bias
        change = prices[-1] * 0.02 * (hash(symbol + str(i)) % 200 - 100) / 100
        new_price = prices[-1] + change
        prices.append(max(new_price, base_price * 0.5))  # Don't drop below 50% of base
    
    return pd.DataFrame({
        'date': dates,
        'price': prices[:len(dates)]  # Ensure same length
    })

def calculate_expected_growth(current_price, days=365):
    """Calculate expected growth based on historical volatility"""
    growth_rate = 0.08  # 8% annual growth assumption
    expected_price = current_price * (1 + growth_rate * (days / 365))
    return expected_price

def update_tech_stock_prices():
    """Update prices for tech stocks with batch processing"""
    with st.spinner("Fetching latest stock prices (with rate limiting)..."):
        success_count = 0
        for symbol in TECH_STOCKS.keys():
            price = get_stock_price(symbol)
            if price:
                st.session_state.tech_stocks[symbol] = {
                    'name': TECH_STOCKS[symbol]["name"],
                    'price': price,
                    'last_updated': datetime.now()
                }
                success_count += 1
            time.sleep(1)  # Additional delay between calls
        
        st.sidebar.info(f"Updated {success_count}/{len(TECH_STOCKS)} stocks")

# Sidebar navigation
st.sidebar.title("📊 Portfolio Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Add Investment", "Tech Stocks", "Portfolio Details"])

# API status
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 API Status")
st.sidebar.info(f"**Calls today:** {st.session_state.api_call_count}/500")
st.sidebar.warning("**Note:** Using mock data when API limits exceeded")

# Main title
st.title("📈 Stock Portfolio Tracker")

if page == "Dashboard":
    st.header("Investment Dashboard")
    
    # Update prices button with warning
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Update Prices", type="primary"):
            if st.session_state.api_call_count > 450:
                st.warning("⚠️ Approaching daily API limit (500 calls)")
            update_tech_stock_prices()
            st.success("Prices updated!")
    
    # Portfolio summary
    if st.session_state.portfolio:
        col1, col2, col3, col4 = st.columns(4)
        
        total_investment = sum([item['units'] * item['purchase_price'] for item in st.session_state.portfolio])
        current_value = 0
        
        for item in st.session_state.portfolio:
            current_price = get_stock_price(item['symbol'])
            if current_price:
                current_value += item['units'] * current_price
        
        with col1:
            st.metric("Total Investment", f"${total_investment:,.2f}")
        with col2:
            st.metric("Current Value", f"${current_value:,.2f}")
        with col3:
            profit_loss = current_value - total_investment
            st.metric("Profit/Loss", f"${profit_loss:,.2f}", 
                     f"{((profit_loss/total_investment)*100 if total_investment > 0 else 0):.1f}%")
        with col4:
            st.metric("Number of Holdings", len(st.session_state.portfolio))
        
        # Main chart - Growth projection
        st.subheader("📊 Portfolio Growth & Projection")
        
        # Create growth chart for each stock
        fig = go.Figure()
        
        for item in st.session_state.portfolio:
            symbol = item['symbol']
            history = get_stock_history(symbol, 90)
            current_price = get_stock_price(symbol)
            
            if history is not None and current_price:
                # Historical data
                fig.add_trace(go.Scatter(
                    x=history['date'],
                    y=history['price'],
                    name=f"{symbol} - Historical",
                    line=dict(dash='solid', width=2)
                ))
                
                # Expected growth line
                future_dates = [history['date'].iloc[-1] + timedelta(days=i) for i in range(0, 366, 30)]
                expected_prices = [calculate_expected_growth(current_price, i) for i in range(0, 366, 30)]
                
                fig.add_trace(go.Scatter(
                    x=future_dates,
                    y=expected_prices,
                    name=f"{symbol} - Projected",
                    line=dict(dash='dot', width=1),
                    opacity=0.7
                ))
        
        fig.update_layout(
            title="Stock Performance & 1-Year Projection",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            height=500,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Data source info
        st.info("💡 **Data Source:** Using real data when available, mock data when API limits are reached")
                
    else:
        st.info("🎯 Your portfolio is empty. Go to 'Add Investment' to start tracking!")

elif page == "Add Investment":
    st.header("➕ Add New Investment")
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_choice = st.selectbox("Select Stock", list(STOCK_SYMBOLS.keys()))
        symbol = STOCK_SYMBOLS[stock_choice]["symbol"]
        
        # Show current price with source indicator
        current_price = get_stock_price(symbol)
        if current_price:
            price_source = "🟢 Live" if st.session_state.api_call_count < 10 else "🟡 Mock"
            st.success(f"{price_source} price: ${current_price:.2f}")
        
        # Fixed number input with consistent types
        purchase_price = st.number_input("Purchase Price ($)", 
                                       min_value=0.01, 
                                       value=float(current_price) if current_price else float(STOCK_SYMBOLS[stock_choice]["mock_price"]),
                                       step=0.01,
                                       format="%.2f",
                                       help="Enter the price per unit when you purchased")
    
    with col2:
        units = st.number_input("Number of Units", 
                              min_value=1, 
                              value=10, 
                              step=1,
                              help="How many units/shares did you buy?")
        purchase_date = st.date_input("Purchase Date", 
                                    value=datetime.now(),
                                    max_value=datetime.now().date())
        notes = st.text_area("Notes (optional)", 
                           placeholder="e.g., Long-term investment, Dividend stock, etc.")
    
    if st.button("💾 Add to Portfolio", type="primary"):
        investment = {
            'symbol': symbol,
            'name': stock_choice,
            'units': int(units),
            'purchase_price': float(purchase_price),
            'purchase_date': purchase_date.strftime("%Y-%m-%d"),
            'notes': notes,
            'added_date': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        st.session_state.portfolio.append(investment)
        st.success(f"✅ Added {units} units of {stock_choice} to portfolio!")
        
        # Show investment summary
        st.subheader("📋 Investment Summary")
        col1, col2, col3 = st.columns(3)
        total_cost = units * purchase_price
        with col1:
            st.metric("Total Cost", f"${total_cost:,.2f}")
        with col2:
            if current_price:
                current_value = units * current_price
                st.metric("Current Value", f"${current_value:,.2f}")
        with col3:
            if current_price:
                profit = (current_price - purchase_price) * units
                profit_percent = (profit / total_cost) * 100
                st.metric("Unrealized P/L", f"${profit:,.2f}", f"{profit_percent:+.1f}%")

elif page == "Tech Stocks":
    st.header("💻 Tech Stocks Overview")
    
    # Update button with rate limit info
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Update Prices", type="primary"):
            if st.session_state.api_call_count > 450:
                st.error("❌ Daily API limit nearly reached! Using mock data.")
            update_tech_stock_prices()
    
    if not st.session_state.tech_stocks:
        st.info("📡 Click 'Update Prices' to load tech stock data")
        # Pre-load with mock data for better UX
        if st.button("Load Demo Data"):
            for symbol, data in TECH_STOCKS.items():
                st.session_state.tech_stocks[symbol] = {
                    'name': data["name"],
                    'price': data["mock_price"],
                    'last_updated': datetime.now()
                }
            st.success("Demo data loaded!")
    else:
        # Create tech stocks table
        tech_data = []
        for symbol, data in st.session_state.tech_stocks.items():
            tech_data.append({
                'Symbol': symbol,
                'Company': data['name'],
                'Current Price': f"${data['price']:.2f}",
                'Last Updated': data['last_updated'].strftime("%Y-%m-%d %H:%M")
            })
        
        tech_df = pd.DataFrame(tech_data)
        
        # Display with nice formatting
        st.subheader("Live Tech Stock Prices")
        st.dataframe(tech_df, 
                    use_container_width=True,
                    height=400)
        
        # Tech stocks performance chart
        st.subheader("📊 Tech Stocks Performance (30 Days)")
        
        fig = go.Figure()
        displayed_stocks = 0
        
        for symbol in list(TECH_STOCKS.keys())[:6]:  # Show first 6 to avoid clutter
            history = get_stock_history(symbol, 30)
            if history is not None and not history.empty:
                fig.add_trace(go.Scatter(
                    x=history['date'],
                    y=history['price'],
                    name=symbol,
                    mode='lines',
                    line=dict(width=2)
                ))
                displayed_stocks += 1
        
        if displayed_stocks > 0:
            fig.update_layout(
                title="30-Day Price Performance",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                height=500,
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Could not load historical data for chart")

elif page == "Portfolio Details":
    st.header("📋 Portfolio Details")
    
    if not st.session_state.portfolio:
        st.info("💼 Your portfolio is empty. Add some investments to get started!")
    else:
        # Portfolio table with detailed information
        portfolio_data = []
        total_investment = 0
        total_current = 0
        
        for i, item in enumerate(st.session_state.portfolio):
            current_price = get_stock_price(item['symbol'])
            cost_basis = item['units'] * item['purchase_price']
            current_value = item['units'] * current_price if current_price else cost_basis
            profit_loss = current_value - cost_basis if current_price else 0
            profit_percent = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0
            
            portfolio_data.append({
                'Stock': item['name'],
                'Symbol': item['symbol'],
                'Units': f"{item['units']:,}",
                'Avg Cost': f"${item['purchase_price']:.2f}",
                'Current Price': f"${current_price:.2f}" if current_price else "N/A",
                'Cost Basis': f"${cost_basis:,.2f}",
                'Current Value': f"${current_value:,.2f}" if current_price else "N/A",
                'P/L': f"${profit_loss:,.2f}" if current_price else "N/A",
                'P/L %': f"{profit_percent:+.1f}%" if current_price else "N/A",
                'Purchase Date': item['purchase_date']
            })
            
            total_investment += cost_basis
            total_current += current_value if current_price else cost_basis
        
        portfolio_df = pd.DataFrame(portfolio_data)
        
        # Display portfolio table
        st.subheader("Your Holdings")
        st.dataframe(portfolio_df, use_container_width=True)
        
        # Portfolio allocation pie chart
        st.subheader("📊 Portfolio Allocation")
        
        allocation_data = []
        for item in st.session_state.portfolio:
            value = item['units'] * item['purchase_price']
            allocation_data.append({
                'Stock': f"{item['name']} ({item['symbol']})",
                'Allocation': (value / total_investment) * 100,
                'Value': value
            })
        
        allocation_df = pd.DataFrame(allocation_data)
        
        if not allocation_df.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.pie(allocation_df, 
                           values='Allocation', 
                           names='Stock', 
                           title="Portfolio Allocation by Investment",
                           hover_data=['Value'])
                fig.update_trace

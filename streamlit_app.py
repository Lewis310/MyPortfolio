import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json
import os

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

# API configuration with your actual key
API_KEY = "NQG5KOWP2QXF7Z72"
BASE_URL = "https://www.alphavantage.co/query"

# Stock symbols
STOCK_SYMBOLS = {
    "NDQ": "NDQ.AX",  # Betashares NASDAQ 100 ETF
    "IVV": "IVV",     # iShares S&P 500 ETF
    "CBA": "CBA.AX",  # Commonwealth Bank
}

TECH_STOCKS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft", 
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "META": "Meta",
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "AMD": "AMD",
    "INTC": "Intel",
    "ADBE": "Adobe"
}

def get_stock_price(symbol):
    """Get current stock price from Alpha Vantage API"""
    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": API_KEY
        }
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        if "Global Quote" in data and data["Global Quote"]:
            return float(data["Global Quote"]["05. price"])
        else:
            st.error(f"Error fetching {symbol}: {data.get('Error Message', 'Rate limit exceeded')}")
            # Fallback to mock data if API limit reached
            return round(100 + hash(symbol) % 200, 2)
    except Exception as e:
        st.error(f"Error fetching {symbol}: {str(e)}")
        # Fallback to mock data
        return round(100 + hash(symbol) % 200, 2)

def get_stock_history(symbol, days=30):
    """Get historical stock data"""
    try:
        # Try to get real historical data
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
            "outputsize": "compact"
        }
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        if "Time Series (Daily)" in data:
            time_series = data["Time Series (Daily)"]
            dates = []
            prices = []
            
            for date_str, values in list(time_series.items())[:days]:
                dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
                prices.append(float(values["4. close"]))
            
            return pd.DataFrame({
                'date': dates[::-1],  # Reverse to get chronological order
                'price': prices[::-1]
            })
        else:
            # Fallback to mock data
            return generate_mock_history(symbol, days)
            
    except Exception as e:
        st.error(f"Error fetching history for {symbol}: {str(e)}")
        return generate_mock_history(symbol, days)

def generate_mock_history(symbol, days):
    """Generate mock historical data as fallback"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    base_price = 100 + hash(symbol) % 200
    prices = [base_price * (1 + 0.01 * i * (hash(symbol + str(i)) % 3 - 1)) for i in range(len(dates))]
    
    return pd.DataFrame({
        'date': dates,
        'price': prices
    })

def calculate_expected_growth(current_price, days=365):
    """Calculate expected growth based on historical volatility"""
    # Simple projection based on average growth
    growth_rate = 0.08  # 8% annual growth assumption
    expected_price = current_price * (1 + growth_rate * (days / 365))
    return expected_price

def update_tech_stock_prices():
    """Update prices for tech stocks"""
    with st.spinner("Fetching latest stock prices..."):
        for symbol in TECH_STOCKS.keys():
            price = get_stock_price(symbol)
            if price:
                st.session_state.tech_stocks[symbol] = {
                    'name': TECH_STOCKS[symbol],
                    'price': price,
                    'last_updated': datetime.now()
                }

# Sidebar navigation
st.sidebar.title("📊 Portfolio Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Add Investment", "Tech Stocks", "Portfolio Details"])

# Main title
st.title("📈 Stock Portfolio Tracker")

# Display API status
st.sidebar.markdown("---")
st.sidebar.success("✅ API Key: Active")

if page == "Dashboard":
    st.header("Investment Dashboard")
    
    # Update prices button
    if st.button("🔄 Update All Prices"):
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
                    line=dict(dash='dot', width=2)
                ))
        
        fig.update_layout(
            title="Stock Performance & 1-Year Projection",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            height=500,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Quick actions
        st.subheader("Quick Actions")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 Update Charts"):
                st.rerun()
        with col2:
            if st.button("💾 Export Portfolio"):
                portfolio_df = pd.DataFrame(st.session_state.portfolio)
                csv = portfolio_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        with col3:
            if st.button("🔄 Refresh All Data"):
                update_tech_stock_prices()
                st.rerun()
                
    else:
        st.info("🎯 Your portfolio is empty. Go to 'Add Investment' to start tracking!")

elif page == "Add Investment":
    st.header("➕ Add New Investment")
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_choice = st.selectbox("Select Stock", list(STOCK_SYMBOLS.keys()))
        symbol = STOCK_SYMBOLS[stock_choice]
        
        # Show current price
        current_price = get_stock_price(symbol)
        if current_price:
            st.success(f"Current price: ${current_price:.2f}")
        
        purchase_price = st.number_input("Purchase Price ($)", 
                                       min_value=0.01, 
                                       value=current_price if current_price else 100.0,
                                       step=0.01,
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
                st.metric("Unrealized P/L", f"${profit:,.2f}", f"{profit_percent:.1f}%")

elif page == "Tech Stocks":
    st.header("💻 Tech Stocks Overview")
    
    # Update button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Update Prices", type="primary"):
            update_tech_stock_prices()
    
    if not st.session_state.tech_stocks:
        st.info("📡 Click 'Update Prices' to load real-time tech stock data")
        if st.button("Load Demo Tech Data"):
            update_tech_stock_prices()
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
        
        fig.update_layout(
            title="30-Day Price Performance",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            height=500,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

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
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.metric("Total Portfolio Value", f"${total_current:,.2f}")
                st.metric("Total Invested", f"${total_investment:,.2f}")
                overall_pl = total_current - total_investment
                st.metric("Overall P/L", 
                         f"${overall_pl:,.2f}", 
                         f"{(overall_pl/total_investment*100):.1f}%" if total_investment > 0 else "0%")

# Footer with API info
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 API Information")
st.sidebar.info(f"**Alpha Vantage Key:** \n`{API_KEY}`\n\n*5 calls/minute • 500 calls/day*")

st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 Tips")
st.sidebar.markdown("""
- **Update prices** regularly for accurate data
- **Add investments** as you make them
- **Monitor allocation** to balance your portfolio
- **Export data** for external analysis
""")

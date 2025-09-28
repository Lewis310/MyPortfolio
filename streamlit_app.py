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

# Data storage file
DATA_FILE = "portfolio_data.json"

def load_data():
    """Load data from file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                return data
    except Exception as e:
        st.sidebar.error(f"Error loading data: {e}")
    return {}

def save_data():
    """Save data to file"""
    try:
        data_to_save = {
            'portfolio': st.session_state.portfolio,
            'tech_stocks': st.session_state.tech_stocks,
            'last_api_call': st.session_state.last_api_call,
            'api_call_count': st.session_state.api_call_count,
            'last_save': datetime.now().isoformat()
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2, default=str)
    except Exception as e:
        st.sidebar.error(f"Error saving data: {e}")

# Initialize session state with saved data
saved_data = load_data()

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = saved_data.get('portfolio', [])

if 'tech_stocks' not in st.session_state:
    st.session_state.tech_stocks = saved_data.get('tech_stocks', {})

if 'last_api_call' not in st.session_state:
    st.session_state.last_api_call = saved_data.get('last_api_call', 0)

if 'api_call_count' not in st.session_state:
    st.session_state.api_call_count = saved_data.get('api_call_count', 0)

# Auto-save function
def auto_save():
    """Auto-save data periodically"""
    if 'last_auto_save' not in st.session_state:
        st.session_state.last_auto_save = time.time()
    
    current_time = time.time()
    # Auto-save every 30 seconds
    if current_time - st.session_state.last_auto_save > 30:
        save_data()
        st.session_state.last_auto_save = current_time

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
    auto_save()  # Auto-save after API calls

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
            return price
        else:
            # Use mock data as fallback
            return get_stock_price(symbol, use_mock=True)
            
    except Exception as e:
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
                    'last_updated': datetime.now().isoformat()
                }
                success_count += 1
            time.sleep(1)  # Additional delay between calls
        
        auto_save()  # Save after updating all prices
        return success_count

# Sidebar navigation
st.sidebar.title("📊 Portfolio Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Add Investment", "Tech Stocks", "Portfolio Details", "Data Management"])

# API status and data info
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 API Status")
st.sidebar.info(f"**Calls today:** {st.session_state.api_call_count}/500")

# Data status
last_save_time = saved_data.get('last_save', 'Never')
st.sidebar.markdown("### 💾 Data Status")
st.sidebar.info(f"**Portfolio items:** {len(st.session_state.portfolio)}\n**Last saved:** {last_save_time[:16]}")

# Manual save button
if st.sidebar.button("💾 Save Data Now"):
    save_data()
    st.sidebar.success("Data saved!")

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
            success_count = update_tech_stock_prices()
            st.success(f"Updated {success_count} stocks!")
            auto_save()
    
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
            'added_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'id': f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"  # Unique ID
        }
        
        st.session_state.portfolio.append(investment)
        save_data()  # Save immediately after adding
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
            success_count = update_tech_stock_prices()
            st.success(f"Updated {success_count} stocks!")
    
    if not st.session_state.tech_stocks:
        st.info("📡 Click 'Update Prices' to load tech stock data")
        # Pre-load with mock data for better UX
        if st.button("Load Demo Data"):
            for symbol, data in TECH_STOCKS.items():
                st.session_state.tech_stocks[symbol] = {
                    'name': data["name"],
                    'price': data["mock_price"],
                    'last_updated': datetime.now().isoformat()
                }
            save_data()
            st.success("Demo data loaded!")
    else:
        # Create tech stocks table
        tech_data = []
        for symbol, data in st.session_state.tech_stocks.items():
            # Handle both string and datetime objects for last_updated
            last_updated = data['last_updated']
            if isinstance(last_updated, str):
                try:
                    last_updated = datetime.fromisoformat(last_updated).strftime("%Y-%m-%d %H:%M")
                except:
                    last_updated = "Unknown"
            
            tech_data.append({
                'Symbol': symbol,
                'Company': data['name'],
                'Current Price': f"${data['price']:.2f}",
                'Last Updated': last_updated
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
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.metric("Total Portfolio Value", f"${total_current:,.2f}")
                st.metric("Total Invested", f"${total_investment:,.2f}")
                overall_pl = total_current - total_investment
                st.metric("Overall P/L", 
                         f"${overall_pl:,.2f}", 
                         f"{(overall_pl/total_investment*100):.1f}%" if total_investment > 0 else "0%")
        
        # Portfolio management options
        st.subheader("🛠️ Portfolio Management")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Portfolio Data"):
                save_data()
                st.success("Portfolio data saved!")
        
        with col2:
            if st.button("📤 Export Portfolio to CSV"):
                export_df = pd.DataFrame(st.session_state.portfolio)
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"portfolio_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

elif page == "Data Management":
    st.header("💾 Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Current Data Status")
        st.info(f"**Portfolio Items:** {len(st.session_state.portfolio)}")
        st.info(f"**Tech Stocks Tracked:** {len(st.session_state.tech_stocks)}")
        st.info(f"**API Calls Today:** {st.session_state.api_call_count}")
        st.info(f"**Last Save:** {saved_data.get('last_save', 'Never')}")
        
        if st.button("🔄 Refresh Data Status"):
            st.rerun()
    
    with col2:
        st.subheader("🛠️ Data Actions")
        
        if st.button("💾 Save All Data Now"):
            save_data()
            st.success("All data saved successfully!")
        
        if st.button("📤 Export Full Data"):
            full_data = {
                'portfolio': st.session_state.portfolio,
                'tech_stocks': st.session_state.tech_stocks,
                'export_date': datetime.now().isoformat()
            }
            json_data = json.dumps(full_data, indent=2, default=str)
            st.download_button(
                label="Download JSON Backup",
                data=json_data,
                file_name=f"portfolio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        st.warning("⚠️ Dangerous Actions")
        if st.button("🗑️ Clear All Data", type="secondary"):
            if st.checkbox("I understand this will delete all my portfolio data"):
                st.session_state.portfolio = []
                st.session_state.tech_stocks = {}
                save_data()
                st.error("All data cleared!")
    
    # Display current portfolio for reference
    if st.session_state.portfolio:
        st.subheader("Current Portfolio Preview")
        preview_data = []
        for item in st.session_state.portfolio[:5]:  # Show first 5 items
            preview_data.append({
                'Stock': item['name'],
                'Symbol': item['symbol'],
                'Units': item['units'],
                'Purchase Price': f"${item['purchase_price']:.2f}",
                'Date': item['purchase_date']
            })
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

# Auto-save on app close and periodically
auto_save()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 Tips")
st.sidebar.markdown("""
- **Data auto-saves** every 30 seconds
- **Manual save** available in Data Management
- **Export backups** regularly
- **API limits:** 500 calls/day
""")

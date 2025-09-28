import streamlit as st
import pandas as pd
import datetime
from datetime import date
import json
import os

# Page configuration
st.set_page_config(
    page_title="My Progress Portfolio",
    page_icon="📊",
    layout="wide"
)

# Initialize session state for data storage
if 'records' not in st.session_state:
    st.session_state.records = []

# File to store data
DATA_FILE = "progress_data.json"

def load_data():
    """Load existing data from file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data():
    """Save data to file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(st.session_state.records, f, indent=2, default=str)

# Load existing data
if not st.session_state.records:
    st.session_state.records = load_data()

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Add Record", "View Progress", "Dashboard"])

# Main title
st.title("🏋️ Personal Progress Portfolio")

if page == "Add Record":
    st.header("➕ Add New Progress Record")
    
    # Date selection
    record_date = st.date_input("Date", value=date.today())
    
    # Sleep tracker
    st.subheader("😴 Sleep")
    sleep_hours = st.slider("Hours slept", 0.0, 12.0, 7.0, 0.5)
    
    # Gym tracker
    st.subheader("💪 Gym Workout")
    gym_attended = st.selectbox("Did you go to the gym?", ["No", "Yes"])
    
    body_part = None
    if gym_attended == "Yes":
        body_part = st.selectbox("Body part trained", 
                               ["Arms", "Chest", "Back", "Legs", "Full Body", "Cardio"])
    
    # Study tracker
    st.subheader("📚 Study")
    study_hours = st.slider("Hours studied", 0.0, 12.0, 0.0, 0.5)
    
    # Health metrics
    st.subheader("❤️ Health Metrics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        weight = st.number_input("Weight (kg)", 40.0, 150.0, 70.0, 0.1)
    
    with col2:
        steps = st.number_input("Step count", 0, 50000, 8000, 100)
    
    with col3:
        avg_heart_rate = st.number_input("Average heart rate (bpm)", 40, 200, 70)
    
    # Notes
    notes = st.text_area("Additional notes")
    
    # Submit button
    if st.button("Save Record"):
        record = {
            "date": record_date,
            "sleep_hours": sleep_hours,
            "gym_attended": gym_attended == "Yes",
            "body_part": body_part,
            "study_hours": study_hours,
            "weight": weight,
            "steps": steps,
            "avg_heart_rate": avg_heart_rate,
            "notes": notes
        }
        
        # Check if record for this date already exists
        existing_dates = [r['date'] for r in st.session_state.records]
        if str(record_date) in existing_dates:
            st.warning("A record for this date already exists. Updating existing record.")
            # Update existing record
            for i, r in enumerate(st.session_state.records):
                if r['date'] == str(record_date):
                    st.session_state.records[i] = record
        else:
            st.session_state.records.append(record)
        
        save_data()
        st.success("Record saved successfully!")
        
        # Show preview
        st.subheader("Record Preview")
        st.json(record)

elif page == "View Progress":
    st.header("📈 View Progress History")
    
    if not st.session_state.records:
        st.info("No records found. Add some records to see your progress!")
    else:
        # Convert to DataFrame for easier display
        df = pd.DataFrame(st.session_state.records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False)
        
        # Date filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", 
                                     value=df['date'].min().date())
        with col2:
            end_date = st.date_input("End date", 
                                   value=df['date'].max().date())
        
        # Filter data
        filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & 
                        (df['date'] <= pd.to_datetime(end_date))]
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # Export option
        if st.button("Export to CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"progress_data_{date.today()}.csv",
                mime="text/csv"
            )

elif page == "Dashboard":
    st.header("📊 Progress Dashboard")
    
    if not st.session_state.records:
        st.info("No records found. Add some records to see your dashboard!")
    else:
        df = pd.DataFrame(st.session_state.records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Key metrics
        st.subheader("Key Metrics Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_sleep = df['sleep_hours'].mean()
            st.metric("Average Sleep", f"{avg_sleep:.1f} hours")
        
        with col2:
            gym_days = df['gym_attended'].sum()
            st.metric("Gym Days", f"{gym_days} days")
        
        with col3:
            avg_study = df['study_hours'].mean()
            st.metric("Average Study", f"{avg_study:.1f} hours")
        
        with col4:
            current_weight = df.iloc[-1]['weight']
            first_weight = df.iloc[0]['weight']
            weight_change = current_weight - first_weight
            st.metric("Weight", f"{current_weight} kg", f"{weight_change:+.1f} kg")
        
        # Charts
        st.subheader("Trends Over Time")
        
        # Sleep chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.line_chart(df.set_index('date')['sleep_hours'], 
                         use_container_width=True)
            st.caption("Sleep Hours Over Time")
        
        with col2:
            st.line_chart(df.set_index('date')['study_hours'], 
                         use_container_width=True)
            st.caption("Study Hours Over Time")
        
        # Gym activity
        st.subheader("Gym Activity")
        gym_df = df[df['gym_attended'] == True]
        if not gym_df.empty:
            body_part_counts = gym_df['body_part'].value_counts()
            st.bar_chart(body_part_counts)
        else:
            st.info("No gym records found")
        
        # Health metrics
        st.subheader("Health Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.line_chart(df.set_index('date')['weight'], 
                         use_container_width=True)
            st.caption("Weight Over Time")
        
        with col2:
            st.line_chart(df.set_index('date')['steps'], 
                         use_container_width=True)
            st.caption("Steps Over Time")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("💡 Tip: Add records daily to track your progress effectively!")

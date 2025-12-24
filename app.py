import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")
st.title("⛽ My Fuel Tracker")

# 1. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Refresh Button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# 3. Load Data
try:
    df = conn.read(worksheet="logs", ttl=0)
    
    if df is not None and not df.empty:
        # Convert to simple date (removes any timing/timestamp issues)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        
        # Ensure numbers are numbers
        for col in ['Odometer', 'Liters', 'Price_Per_L']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Clean up empty rows and sort by Odometer
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

except Exception as e:
    st.error(f"Error loading data: {e}")
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# --- SUMMARY SECTION ---
if not df.empty:
    st.subheader("Summary")
    
    # KM & Fuel Stats
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    
    # 30 Day Calculation (Simple Date comparison)
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    recent_df = df[df['Date'] >= thirty_days_ago]
    cost_30d = (recent_df['Liters'] * recent_df['Price_Per_L']).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("30d Cost", f"Rs. {cost_30d:,.0f}")
    c2.metric("Total KM", f"{total_km:,.0f}")
    c3.metric("Total L", f"{total_liters:,.1f}")

    # KPL Logic
    if len(df) > 1:
        # Distance of the most recent trip
        dist_since_last = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_k

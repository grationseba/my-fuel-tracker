import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Set page config
st.set_page_config(page_title="Fuel Tracker", page_icon="⛽", layout="wide")

# REPLACE THIS LINK with your actual car photo link
CAR_IMAGE_URL = "https://drive.google.com/file/d/1xEvLQ1ZR_tdWVXSxGbohEV4xkPlcASK1/view?usp=sharing" 

# Custom CSS for Background and Grid
st.markdown(f"""
    <style>
    /* 1. Background Styling */
    .stApp {{
        background-image: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{CAR_IMAGE_URL}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    .block-container {{ 
        padding-top: 0.5rem !important; 
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important; 
    }}
    header, footer, #MainMenu {{visibility: hidden;}}
    
    /* 2. Grid styling with slight glass effect for readability */
    .summary-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        width: 100%;
        margin-bottom: 15px;
        background: rgba(0, 0, 0, 0.4); /* Glass effect */
        padding: 10px;
        border-radius: 10px;
    }}
    .stat-item {{
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 5px;
    }}
    .stat-label {{
        font-size: 0.7rem;
        color: #ccc;
        text-transform: uppercase;
        display: block;
    }}
    .stat-value {{
        font-size: 1.1rem;
        font-weight: bold;
        color: #fff;
    }}
    
    /* Make the form semi-transparent to see the car */
    div[data-testid="stForm"] {{
        background: rgba(0, 0, 0, 0.5) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# 1. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Load Data
try:
    df = conn.read(worksheet="logs", ttl=0)
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        for col in ['Odometer', 'Liters', 'Price_Per_L']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])
except:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# --- DATA CALCULATIONS ---
today = datetime.now().date()
thirty_days_ago = today - timedelta(days=31)

if not df.empty:
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    total_cost = (df['Liters'] * df['Price_Per_L']).sum()
    recent_df = df[df['Date'] >= thirty_days_ago]
    cost_30d = (recent_df['Liters'] * recent_df['Price_Per_L']).sum()

    last_trip_dist = 0
    last_kpl = 0
    avg_kpl = 0
    if len(df) > 1:
        last_trip_dist = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = last_trip_dist / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        fuel_consumed = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_consumed if fuel_consumed > 0 else 0

    # --- RAW TEXT GRID ---
    st.markdown(f"""
    <div class="summary-grid">
        <div class="stat-item">
            <span class="stat-label">Last 30 Days Cost</span>
            <span class="stat-value">Rs. {cost_30d:,.0f}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Total KM</span>
            <span class="stat-value">{total_km:,.0f} km</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Trip Distance</span>
            <span class="stat-value">{last_trip_dist} km</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Avg KPL</span>
            <span class="stat-value">{avg_kpl:.1f}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Last KPL</span>
            <span class="stat-value">{last_kpl:.1f}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Total Liters</span>
            <span class="stat-value">{total_liters:,.0f} L</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 3. Form & History
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

with st.form("fuel_form", clear_on_submit=True):
    date_input = st.date_input("Date", value=today)
    fuel_type = st.selectbox("Type", ["92 Octane", "95 Octane"])
    last_odo = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer", min_value=last_odo, value=last_odo)
    liters = st.number_input("Liters", min_value=0.0)
    price = st.number_input("Price", value=294.0 if fuel_type == "92 Octane" else 335.0)
    
    if st.form_submit_button("Save Entry"):
        if liters > 0:
            new_data = pd.DataFrame([{"Date": date_input, "Odometer": odo, "Liters": liters, "Price_Per_L": price, "Fuel_Type": fuel_type}])
            conn.update(worksheet="logs", data=pd.concat([df, new_data], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

if not df.empty:
    history_view = df[df['Date'] >= thirty_days_ago].copy()
    if not history_view.empty:
        history_view['Date'] = history_view['Date'].apply(lambda x: x.strftime('%m-%d'))
        st.dataframe(history_view.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters"]], use_container_width=True, hide_index=True)

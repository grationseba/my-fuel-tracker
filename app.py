import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Set page to wide and hide the top padding
st.set_page_config(page_title="Fuel Tracker", page_icon="⛽", layout="wide")

# Custom CSS for Mobile Optimization
st.markdown("""
    <style>
    /* Remove top padding and hide headers */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Make metrics smaller and side-by-side on mobile */
    [data-testid="column"] {
        width: 33% !important;
        flex: 1 1 33% !important;
        min-width: 33% !important;
    }
    
    [data-testid="stMetric"] {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 5px !important;
        border-radius: 8px;
        text-align: center;
    }
    
    /* Shrink metric text size for mobile */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; }

    .main-container {
        background-color: #111;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #222;
        margin-bottom: 10px;
    }
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
except Exception as e:
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

    # --- THREE BOX SUMMARY (COMPACT) ---
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("30d Cost", f"{cost_30d:,.0f}")
        st.metric("Tot KM", f"{total_km:,.0f}")
    with c2:
        st.metric("Trip KM", f"{last_trip_dist}")
        st.metric("Avg KPL", f"{avg_kpl:.1f}")
    with c3:
        st.metric("Last KPL", f"{last_kpl:.1f}")
        st.metric("Tot L", f"{total_liters:,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)

# 3. Refresh Button (Compact)
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    date_input = st.date_input("Date", value=today)
    fuel_type = st.selectbox("Type", ["92 Octane", "95 Octane"])
    default_p = 294.0 if fuel_type == "92 Octane" else 335.0
    
    last_odo_val = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer", min_value=last_odo_val, value=last_odo_val)
    liters = st.number_input("Liters", min_value=0.0, max_value=40.0, value=0.0)
    price = st.number_input("Price", min_value=0.0, value=default_p)
    
    if st.form_submit_button("Save Entry"):
        if liters > 0:
            new_data = pd.DataFrame([{"Date": date_input, "Odometer": odo, "Liters": liters, "Price_Per_L": price, "Fuel_Type": fuel_type}])
            conn.update(worksheet="logs", data=pd.concat([df, new_data], ignore_index=True))
            st.cache_data.clear()
            st.success(f"Saved! Trip: {odo - last_odo_val} KM")
            st.rerun()

# --- HISTORY ---
if not df.empty:
    st.write("---")
    history_view = df[df['Date'] >= thirty_days_ago].copy()
    if not history_view.empty:
        history_view['Date'] = history_view['Date'].apply(lambda x: x.strftime('%m-%d'))
        view = history_view.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters"]]
        st.dataframe(view, use_container_width=True, hide_index=True)

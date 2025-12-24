import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="wide") # 'wide' helps the 3 boxes fit better

# Custom CSS for the "Box" look
st.markdown("""
    <style>
    .metric-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #e9ecef;
        text-align: center;
        min-height: 220px;
    }
    .metric-title {
        font-weight: bold;
        color: #555;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⛽ My Fuel Tracker")

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
    st.error(f"Error loading data: {e}")
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# --- DATA CALCULATIONS ---
today = datetime.now().date()
thirty_days_ago = today - timedelta(days=31)

if not df.empty:
    # Basic Stats
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    total_cost = (df['Liters'] * df['Price_Per_L']).sum()
    
    # 30 Day Cost
    recent_df = df[df['Date'] >= thirty_days_ago]
    cost_30d = (recent_df['Liters'] * recent_df['Price_Per_L']).sum()

    # KPL and Trip Stats
    last_trip_dist = 0
    last_kpl = 0
    avg_kpl = 0
    
    if len(df) > 1:
        last_trip_dist = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = last_trip_dist / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        fuel_after_start = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_after_start if fuel_after_start > 0 else 0

    # --- THREE BOX SUMMARY SECTION ---
    st.subheader("📊 Summary")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="metric-box"><p class="metric-title">Cost & Distance</p>', unsafe_allow_html=True)
        st.metric("30 Days Cost", f"Rs. {cost_30d:,.0f}")
        st.metric("Total Cost", f"Rs. {total_cost:,.0f}")
        st.metric("Total KM", f"{total_km:,.0f} km")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-box" style="border-color: #007bff;"><p class="metric-title">Last Trip Info</p>', unsafe_allow_html=True)
        st.write("## ") # Spacing
        st.metric("Trip Distance", f"{last_trip_dist} KM", delta="since last fill", delta_color="normal")
        st.write("---")
        st.caption("Distance calculated from your latest entry.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-box"><p class="metric-title">Efficiency</p>', unsafe_allow_html=True)
        st.metric("Total Liters", f"{total_liters:,.1f} L")
        st.metric("Last Fill KPL", f"{last_kpl:.2f}")
        st.metric("Avg KPL", f"{avg_kpl:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    st.markdown("### Add New Entry")
    date_input = st.date_input("Date", value=today)
    fuel_type = st.selectbox("Petrol Type", ["92 Octane", "95 Octane"])
    
    # Auto-price
    default_p = 294.0 if fuel_type == "92 Octane" else 335.0
    
    last_odo_val = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer Reading", min_value=last_odo_val, value=last_odo_val)
    liters = st.number_input("Liters Added", min_value=0.0, max_value=40.0, value=0.0)
    price = st.number_input("Price (Rs.)", min_value=0.0, value=default_p)
    
    submit = st.form_submit_button("Save Entry")
    
    if submit:
        if liters <= 0:
            st.warning("Please enter liters.")
        else:
            new_data = pd.DataFrame([{"Date": date_input, "Odometer": odo, "Liters": liters, "Price_Per_L": price, "Fuel_Type": fuel_type}])
            final_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="logs", data=final_df)
            
            st.cache_data.clear()
            st.success(f"Entry Saved! Trip: {odo - last_odo_val} KM")
            st.rerun()

# --- HISTORY ---
if not df.empty:
    st.subheader("History (Last 30 Days)")
    history_view = df[df['Date'] >= thirty_days_ago].copy()
    if not history_view.empty:
        history_view['Date'] = history_view['Date'].apply(lambda x: x.strftime('%Y-%m-%d'))
        view = history_view.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters", "Fuel_Type"]]
        st.dataframe(view, use_container_width=True)

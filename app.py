import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="wide")

# 1. Custom CSS to create high-quality boxes that CONTAIN the metrics
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .main-container {
        background-color: #111;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #222;
        margin-bottom: 25px;
    }
    .box-label {
        color: #888;
        font-size: 0.8rem;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 10px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⛽ My Fuel Tracker")

# 2. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Load Data
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

    last_trip_dist = 0
    last_kpl = 0
    avg_kpl = 0
    
    if len(df) > 1:
        last_trip_dist = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = last_trip_dist / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        fuel_after_start = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_after_start if fuel_after_start > 0 else 0

    # --- THREE BOX SUMMARY SECTION ---
    st.subheader("Summary")
    
    # Grouping everything inside one main container for the "Summary" area
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<p class="box-label">Cost & Distance</p>', unsafe_allow_html=True)
        st.metric("30 Days Cost", f"Rs. {cost_30d:,.0f}")
        st.metric("Total Cost", f"Rs. {total_cost:,.0f}")
        st.metric("Total KM", f"{total_km:,.0f} km")

    with col2:
        st.markdown('<p class="box-label">Last Trip Info</p>', unsafe_allow_html=True)
        # Empty space to vertically center the Trip Distance
        st.write("## ")
        st.write("## ")
        st.metric("Trip Distance", f"{last_trip_dist} KM", delta="since last fill")
        st.write("## ")
        st.caption("Distance traveled since your previous fill-up.")

    with col3:
        st.markdown('<p class="box-label">Efficiency</p>', unsafe_allow_html=True)
        st.metric("Total Liters", f"{total_liters:,.1f} L")
        st.metric("Last Fill KPL", f"{last_kpl:.2f}")
        st.metric("Avg KPL", f"{avg_kpl:.2f}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    st.markdown("### Add New Entry")
    date_input = st.date_input("Date", value=today)
    fuel_type = st.selectbox("Petrol Type", ["92 Octane", "95 Octane"])
    
    # Auto-price based on petrol type
    default_p = 294.0 if fuel_type == "92 Octane" else 335.0
    
    last_odo_val = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer Reading", min_value=last_odo_val, value=last_odo_val)
    liters = st.number_input("Liters Added", min_value=0.0, max_value=40.0, value=0.0)
    price = st.number_input("Price (Rs.)", min_value=0.0, value=default_p)
    
    submit = st.form_submit_button("Save Entry")
    
    if submit:
        if liters <= 0:
            st.warning("Please enter liters added.")
        else:
            new_data = pd.DataFrame([{
                "Date": date_input, 
                "Odometer": odo, 
                "Liters": liters, 
                "Price_Per_L": price, 
                "Fuel_Type": fuel_type
            }])
            final_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="logs", data=final_df)
            
            st.cache_data.clear()
            st.success(f"Saved! You covered {odo - last_odo_val} KM in this trip.")
            st.rerun()

# --- HISTORY ---
if not df.empty:
    st.subheader("History (Last 30 Days)")
    history_view = df[df['Date'] >= thirty_days_ago].copy()
    if not history_view.empty:
        history_view['Date'] = history_view['Date'].apply(lambda x: x.strftime('%Y-%m-%d'))
        view = history_view.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters", "Fuel_Type"]]
        st.dataframe(view, use_container_width=True)

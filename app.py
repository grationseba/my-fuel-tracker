import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")

# Custom CSS for the "Box" look
st.markdown("""
    <style>
    .metric-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #d1d5db;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

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
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    total_cost = (df['Liters'] * df['Price_Per_L']).sum()
    
    recent_df = df[df['Date'] >= thirty_days_ago]
    cost_30d = (recent_df['Liters'] * recent_df['Price_Per_L']).sum()

    # --- SUMMARY UI ---
    st.subheader("📊 Summary")
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("30 Days Cost", f"Rs. {cost_30d:,.0f}")
        st.metric("Total Cost", f"Rs. {total_cost:,.0f}")
        st.metric("Total KM", f"{total_km:,.0f} km")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("Total Liters", f"{total_liters:,.1f} L")
        
        if len(df) > 1:
            dist_last = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
            last_kpl = dist_last / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
            fuel_after_start = df['Liters'].iloc[1:].sum()
            avg_kpl = total_km / fuel_after_start if fuel_after_start > 0 else 0
            
            st.metric("Last fill KPL", f"{last_kpl:.2f}")
            st.metric("Avg KPL", f"{avg_kpl:.2f}")
        else:
            st.write("Add more logs for KPL stats")
        st.markdown('</div>', unsafe_allow_html=True)
    st.divider()

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    date_input = st.date_input("Date", value=today)
    fuel_type = st.selectbox("Petrol Type", ["92 Octane", "95 Octane"])
    default_p = 294.0 if fuel_type == "92 Octane" else 335.0
    
    last_odo_val = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer Reading", min_value=last_odo_val, value=last_odo_val)
    liters = st.number_input("Liters Added", min_value=0.0, max_value=35.0, value=0.0)
    price = st.number_input("Price (Rs.)", min_value=0.0, value=default_p)
    
    submit = st.form_submit_button("Save Entry")
    
    if submit:
        if liters <= 0:
            st.warning("Please enter liters.")
        else:
            # Calculate distance since last fill for the success message
            dist_since_last = odo - last_odo_val if not df.empty else 0
            
            new_data = pd.DataFrame([{"Date": date_input, "Odometer": odo, "Liters": liters, "Price_Per_L": price, "Fuel_Type": fuel_type}])
            final_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="logs", data=final_df)
            
            st.cache_data.clear()
            # Middle Success Message with Last Fill KM
            st.balloons()
            st.success(f"✅ Saved! You traveled {dist_since_last} KM since your last fill-up.")
            st.rerun()

# --- HISTORY ---
if not df.empty:
    st.subheader("History (Last 30 Days)")
    history_view = df[df['Date'] >= thirty_days_ago].copy()
    if not history_view.empty:
        history_view['Date'] = history_view['Date'].apply(lambda x: x.strftime('%Y-%m-%d'))
        view = history_view.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters", "Fuel_Type"]]
        st.dataframe(view, use_container_width=True)

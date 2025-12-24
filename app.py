import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")
st.title("⛽ My Fuel Tracker")

# 1. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Manual Refresh Button at the top
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# 3. Load Data with No Caching
try:
    # Explicitly fetching from 'logs' tab with 0 cache time
    df = conn.read(worksheet="logs", ttl=0)
    
    if df is not None and not df.empty:
        # Convert columns to make sure math doesn't break
        df['Date'] = pd.to_datetime(df['Date'])
        df['Odometer'] = pd.to_numeric(df['Odometer'], errors='coerce')
        df['Liters'] = pd.to_numeric(df['Liters'], errors='coerce')
        df['Price_Per_L'] = pd.to_numeric(df['Price_Per_L'], errors='coerce')
        
        # Remove any empty rows that might be in the Google Sheet
        df = df.dropna(subset=['Odometer', 'Liters'])
        df = df.sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

except Exception as e:
    st.error(f"Error loading data: {e}")
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# --- SUMMARY SECTION ---
if not df.empty and len(df) > 0:
    st.subheader("Summary")
    
    # KM Math
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    
    # 30 Day Math
    last_30d_cutoff = datetime.now() - timedelta(days=30)
    recent_df = df[df['Date'] > last_30d_cutoff]
    cost_30d = (recent_df['Liters'] * recent_df['Price_Per_L']).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("30d Cost", f"Rs. {cost_30d:,.0f}")
    c2.metric("Total KM", f"{total_km:,.0f}")
    c3.metric("Total L", f"{total_liters:,.1f}")

    # KPL Math (Needs at least 2 logs)
    if len(df) > 1:
        # Most recent trip
        dist_since_last = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = dist_since_last / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        
        # Overall average
        fuel_after_start = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_after_start if fuel_after_start > 0 else 0
        
        c4, c5 = st.columns(2)
        c4.metric("Last Fill KPL", f"{last_kpl:.2f}")
        c5.metric("Avg KPL", f"{avg_kpl:.2f}")
    
    st.divider()

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    date = st.date_input("Date", value=datetime.now())
    fuel_type = st.selectbox("Petrol Type", ["92 Octane", "95 Octane"])
    
    # Automatic Price setting
    default_p = 294.0 if fuel_type == "92 Octane" else 335.0
    
    last_odo = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer Reading", min_value=last_odo, value=last_odo)
    
    liters = st.number_input("Liters Added", min_value=0.0, max_value=35.0, value=0.0)
    price = st.number_input("Price (Rs.)", min_value=0.0, value=default_p)
    
    if st.form_submit_button("Save Entry"):
        if liters <= 0:
            st.warning("Please enter the amount of liters.")
        else:
            new_data = pd.DataFrame([{
                "Date": date.strftime('%Y-%m-%d'),
                "Odometer": odo,
                "Liters": liters,
                "Price_Per_L": price,
                "Fuel_Type": fuel_type
            }])
            
            # Combine and Save
            final_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="logs", data=final_df)
            
            # Force App Refresh
            st.cache_data.clear()
            st.success("Saved!")
            st.rerun()

# --- HISTORY ---
if not df.empty:
    st.subheader("Recent History")
    # Clean view of your logs
    view = df.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters", "Fuel_Type"]]
    st.dataframe(view, use_container_width=True)

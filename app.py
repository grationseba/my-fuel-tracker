import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")
st.title("⛽ My Fuel Tracker")

# 1. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Load Data - 'ttl=0' tells Streamlit NOT to cache the data
try:
    df = conn.read(worksheet="logs", ttl=0)
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        for col in ['Odometer', 'Liters', 'Price_Per_L']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])
except Exception:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# --- SUMMARY SECTION ---
if not df.empty:
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    
    last_30d_cutoff = datetime.now() - timedelta(days=30)
    cost_30d = (df[df['Date'] > last_30d_cutoff]['Liters'] * df[df['Date'] > last_30d_cutoff]['Price_Per_L']).sum()
    
    st.subheader("Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("30d Cost", f"Rs. {cost_30d:,.0f}")
    c2.metric("Total KM", f"{total_km:,.0f}")
    c3.metric("Total L", f"{total_liters:,.1f}")

    if len(df) > 1:
        recent_dist = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = recent_dist / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        
        fuel_consumed_for_dist = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_consumed_for_dist if fuel_consumed_for_dist > 0 else 0
        
        c4, c5 = st.columns(2)
        c4.metric("Last Fill KPL", f"{last_kpl:.2f}")
        c5.metric("Avg KPL", f"{avg_kpl:.2f}")
    
    st.divider()

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    date = st.date_input("Date", value=datetime.now())
    fuel_type = st.selectbox("Petrol Type", ["92 Octane", "95 Octane"])
    
    default_price = 294.0 if fuel_type == "92 Octane" else 335.0
    
    last_odo = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer Reading", min_value=last_odo, value=last_odo)
    
    liters = st.number_input("Liters Added", min_value=0.0, max_value=35.0, value=0.0)
    price = st.number_input("Price per Liter (Rs.)", min_value=0.0, value=default_price)
    
    submit = st.form_submit_button("Save Entry")
    
    if submit:
        if liters <= 0:
            st.error("Please enter liters.")
        elif not df.empty and odo <= last_odo:
            st.error("Odometer must be higher than last entry.")
        else:
            new_row = pd.DataFrame([{
                "Date": date.strftime('%Y-%m-%d'), 
                "Odometer": odo, 
                "Liters": liters, 
                "Price_Per_L": price, 
                "Fuel_Type": fuel_type
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            # Save data
            conn.update(worksheet="logs", data=updated_df)
            
            # --- THE CACHE BUSTER ---
            st.cache_data.clear() # Clears internal memory
            st.success("Saved! Refreshing...")
            st.rerun() # Forces the app to restart from the top with fresh data

# --- HISTORY ---
if not df.empty:
    st.subheader("Recent History")
    display_df = df.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters", "Fuel_Type"]]
    st.dataframe(display_df, use_container_width=True)

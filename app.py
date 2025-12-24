import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")
st.title("⛽ My Fuel Tracker")

# Create connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. Load data
df = conn.read(ttl="0")
# Ensure Date is actually a datetime object
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])

# --- SUMMARY SECTION ---
if not df.empty and len(df) > 1:
    df = df.sort_values("Odometer")
    
    # Calculations
    last_30_days = df[df['Date'] > (datetime.now() - timedelta(days=30))]
    total_spent_30d = (last_30_days['Liters'] * last_30_days['Price_Per_L']).sum()
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    
    # KPL Math
    df['Distance'] = df['Odometer'].diff()
    # KPL = Distance / Liters (Efficiency of the previous tank)
    df['KPL'] = df['Distance'] / df['Liters']
    
    last_kpl = df['KPL'].iloc[-1]
    avg_kpl = df['Distance'].sum() / df['Liters'].iloc[1:].sum()

    st.subheader("Summary")
    c1, c2 = st.columns(2)
    c1.metric("Cost (Last 30d)", f"Rs. {total_spent_30d:,.2f}")
    c2.metric("Total Distance", f"{total_km} KM")
    
    c3, c4 = st.columns(2)
    c3.metric("Total Liters", f"{total_liters:.2f} L")
    c4.metric("Last Fill-up KPL", f"{last_kpl:.2f}")
    
    st.metric("Overall Average KPL", f"{avg_kpl:.2f}")
    st.divider()

# --- INPUT FORM ---
with st.expander("➕ Add New Fill-up"):
    with st.form("fuel_form", clear_on_submit=True):
        date = st.date_input("Date", value=datetime.now())
        odo = st.number_input("Odometer Reading", min_value=0)
        
        # Set default to your tank size: 35.0
        liters = st.number_input("Liters Added", min_value=0.0, max_value=35.0, value=35.0)
        
        # Set default price to 294
        price = st.number_input("Price per Liter (Rs.)", min_value=0.0, value=294.0)
        
        full = st.checkbox("Full Tank?", value=True)
        
        if st.form_submit_button("Save to Log"):
            new_row = pd.DataFrame([{
                "Date": date.strftime('%Y-%m-%d'),
                "Odometer": odo,
                "Liters": liters,
                "Price_Per_L": price,
                "Full_Tank": full
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Record saved!")
            st.rerun()

# --- HISTORY ---
st.subheader("Recent Logs")
st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)

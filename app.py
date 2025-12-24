import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")
st.title("⛽ My Fuel Tracker")

# 1. Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Load Data - Using a Try/Except block to handle the 400 error
try:
    # Adding 'header=0' tells it the first row is the labels
    df = conn.read(worksheet="logs", ttl="0")
    
    if df is not None and not df.empty:
        # Standardize columns to avoid math errors
        df.columns = ["Date", "Odometer", "Liters", "Price_Per_L", "Full_Tank"]
        df['Date'] = pd.to_datetime(df['Date'])
        df['Odometer'] = pd.to_numeric(df['Odometer'], errors='coerce')
        df['Liters'] = pd.to_numeric(df['Liters'], errors='coerce')
        df['Price_Per_L'] = pd.to_numeric(df['Price_Per_L'], errors='coerce')
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Full_Tank"])

except Exception as e:
    # If it fails to read, we show a helpful message and start with an empty table
    st.warning("First run or Sheet empty. Add your first log below!")
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Full_Tank"])

# --- SUMMARY SECTION ---
if not df.empty and len(df) >= 1:
    df = df.sort_values("Odometer")
    
    # Simple Calculations
    last_30_days = df[df['Date'] > (datetime.now() - timedelta(days=30))]
    cost_30d = (last_30_days['Liters'] * last_30_days['Price_Per_L']).sum()
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()

    st.subheader("Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("30d Cost", f"Rs. {cost_30d:,.0f}")
    c2.metric("Total KM", f"{total_km:,.0f}")
    c3.metric("Total L", f"{total_liters:,.1f}")

    if len(df) > 1:
        dist_since_last = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = dist_since_last / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        avg_kpl = total_km / df['Liters'].iloc[1:].sum() if df['Liters'].iloc[1:].sum() > 0 else 0
        
        c4, c5 = st.columns(2)
        c4.metric("Last KPL", f"{last_kpl:.2f}")
        c5.metric("Avg KPL", f"{avg_kpl:.2f}")
    st.divider()

# --- INPUT FORM ---
with st.expander("➕ Add New Fill-up", expanded=df.empty):
    with st.form("fuel_form", clear_on_submit=True):
        date = st.date_input("Date", value=datetime.now())
        
        last_odo = int(df['Odometer'].max()) if not df.empty else 0
        odo = st.number_input("Odometer Reading", min_value=last_odo, value=last_odo)
        
        liters = st.number_input("Liters Added", min_value=0.0, max_value=35.0, value=35.0)
        price = st.number_input("Price per Liter (Rs.)", min_value=0.0, value=294.0)
        full = st.checkbox("Full Tank?", value=True)
        
        if st.form_submit_button("Save to Google Sheets"):
            new_entry = pd.DataFrame([{
                "Date": date.strftime('%Y-%m-%d'),
                "Odometer": odo,
                "Liters": liters,
                "Price_Per_L": price,
                "Full_Tank": str(full)
            }])
            
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            
            try:
                # Force writing to the 'logs' worksheet
                conn.update(worksheet="logs", data=updated_df)
                st.success("Log Saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Save Failed: {e}")

# --- TABLE ---
if not df.empty:
    st.subheader("History")
    st.dataframe(df.sort_values("Odometer", ascending=False), use_container_width=True)

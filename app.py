import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")
st.title("⛽ My Fuel Tracker")

# 1. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Load Data
try:
    df = conn.read(worksheet="logs", ttl="0")
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        for col in ['Odometer', 'Liters', 'Price_Per_L']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Full_Tank"])
except Exception:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Full_Tank"])

# --- SUMMARY SECTION ---
if not df.empty and len(df) >= 1:
    df = df.sort_values("Odometer")
    last_30d_cutoff = datetime.now() - timedelta(days=30)
    last_30d = df[df['Date'] > last_30d_cutoff]
    
    st.subheader("Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("30d Cost", f"Rs. {(last_30d['Liters'] * last_30d['Price_Per_L']).sum():,.0f}")
    c2.metric("Total KM", f"{(df['Odometer'].max() - df['Odometer'].min()):,.0f}")
    c3.metric("Total L", f"{df['Liters'].sum():,.1f}")

    if len(df) > 1:
        last_dist = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = last_dist / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        avg_kpl = (df['Odometer'].max() - df['Odometer'].min()) / df['Liters'].iloc[1:].sum()
        
        c4, c5 = st.columns(2)
        c4.metric("Last Fill KPL", f"{last_kpl:.2f}")
        c5.metric("Avg KPL", f"{avg_kpl:.2f}")
    st.divider()

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    date = st.date_input("Date", value=datetime.now())
    
    # Odometer starts at your last reading
    last_odo = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer Reading", min_value=last_odo, value=last_odo)
    
    # Liters now starts at 0, but max is 35
    liters = st.number_input("Liters Added", min_value=0.0, max_value=35.0, value=0.0, help="Max tank capacity is 35L")
    
    price = st.number_input("Price per Liter (Rs.)", min_value=0.0, value=294.0)
    
    if st.form_submit_button("Save Entry"):
        if liters == 0:
            st.error("Please enter the amount of liters added.")
        else:
            new_row = pd.DataFrame([{
                "Date": date.strftime('%Y-%m-%d'), 
                "Odometer": odo, 
                "Liters": liters, 
                "Price_Per_L": price, 
                "Full_Tank": "Yes"
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="logs", data=updated_df)
            st.success("Entry Saved!")
            st.rerun()

# --- HISTORY TABLE ---
if not df.empty:
    st.subheader("Recent History")
    # We display only the columns you care about to keep it simple
    display_df = df.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters", "Price_Per_L"]]
    st.dataframe(display_df, use_container_width=True)

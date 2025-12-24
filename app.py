import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="My Fuel Tracker", layout="centered")
st.title("⛽ My Fuel Tracker")

# Create connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. Load existing data
# Note: 'url' will be set in your Streamlit dashboard settings later
df = conn.read(ttl="0") # ttl="0" means don't cache, always get fresh data

# 2. Input Form
with st.expander("➕ Add New Fill-up"):
    with st.form("fuel_form", clear_on_submit=True):
        date = st.date_input("Date")
        odo = st.number_input("Odometer Reading", min_value=0)
        liters = st.number_input("Liters Added", min_value=0.0)
        price = st.number_input("Price per Liter", min_value=0.0)
        full = st.checkbox("Full Tank?", value=True)
        
        if st.form_submit_button("Save to Google Sheets"):
            # Create new row
            new_row = pd.DataFrame([{
                "Date": date.strftime('%Y-%m-%d'),
                "Odometer": odo,
                "Liters": liters,
                "Price_Per_L": price,
                "Full_Tank": full
            }])
            
            # Combine and update
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Data synced to Google Sheets!")
            st.rerun()

# 3. Stats Logic
if not df.empty and len(df) > 1:
    df = df.sort_values("Odometer")
    total_dist = df['Odometer'].max() - df['Odometer'].min()
    total_fuel = df['Liters'].iloc[1:].sum() # Fuel used after first fill
    
    if total_dist > 0:
        avg_eff = (total_fuel / total_dist) * 100
        st.metric("Avg L/100km", f"{avg_eff:.2f}")

st.dataframe(df.tail(10), use_container_width=True)

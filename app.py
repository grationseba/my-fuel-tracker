import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Fuel Tracker", layout="centered")
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
        # Simple date only
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        
        # Numeric conversion
        for col in ['Odometer', 'Liters', 'Price_Per_L']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Clean and sort
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

except Exception as e:
    st.error(f"Error loading data: {e}")
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# --- SUMMARY SECTION ---
if not df.empty:
    st.subheader("Summary")
    
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    
    # 30 Day Calculation
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    recent_df = df[df['Date'] >= thirty_days_ago]
    cost_30d = (recent_df['Liters'] * recent_df['Price_Per_L']).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("30d Cost", f"Rs. {cost_30d:,.0f}")
    c2.metric("Total KM", f"{total_km:,.0f}")
    c3.metric("Total L", f"{total_liters:,.1f}")

    if len(df) > 1:
        # Math for last fill up
        dist_since_last = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = dist_since_last / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        
        # Average KPL (Total Distance / Fuel since first fill)
        fuel_after_first = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_after_first if fuel_after_first > 0 else 0
        
        c4, c5 = st.columns(2)
        c4.metric("Last Fill KPL", f"{last_kpl:.2f}")
        c5.metric("Avg KPL", f"{avg_kpl:.2f}")
    
    st.divider()

# --- INPUT FORM ---
with st.form("fuel_form", clear_on_submit=True):
    date = st.date_input("Date", value=datetime.now().date())
    fuel_type = st.selectbox("Petrol Type", ["92 Octane", "95 Octane"])
    
    default_p = 294.0 if fuel_type == "92 Octane" else 335.0
    
    last_odo = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer Reading", min_value=last_odo, value=last_odo)
    
    liters = st.number_input("Liters Added", min_value=0.0, max_value=35.0, value=0.0)
    price = st.number_input("Price (Rs.)", min_value=0.0, value=default_p)
    
    submit = st.form_submit_button("Save Entry")
    
    if submit:
        if liters <= 0:
            st.warning("Please enter the amount of liters.")
        else:
            new_data = pd.DataFrame([{
                "Date": date,
                "Odometer": odo,
                "Liters": liters,
                "Price_Per_L": price,
                "Fuel_Type": fuel_type
            }])
            
            final_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="logs", data=final_df)
            
            st.cache_data.clear()
            st.success("Saved!")
            st.rerun()

# --- HISTORY ---
if not df.empty:
    st.subheader("Recent History")
    view = df.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters", "Fuel_Type"]]
    st.dataframe(view, use_container_width=True)

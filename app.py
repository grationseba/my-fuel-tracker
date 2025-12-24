import streamlit as st
import pandas as pd
import os

# App Title
st.set_page_config(page_title="My Fuel Tracker", layout="centered")
st.title("⛽ Fuel Tracker")

# 1. Load Data
FILE = "fuel_log.csv"
if os.path.exists(FILE):
    df = pd.read_csv(FILE)
else:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Full_Tank"])

# 2. Input Form
with st.expander("➕ Add New Fill-up", expanded=True):
    with st.form("fuel_form", clear_on_submit=True):
        date = st.date_input("Date")
        odo = st.number_input("Odometer Reading", min_value=0, step=1)
        liters = st.number_input("Liters Added", min_value=0.0, step=0.1)
        price = st.number_input("Price per Liter", min_value=0.0, step=0.01)
        full = st.checkbox("Full Tank?", value=True)
        
        if st.form_submit_button("Save"):
            new_data = pd.DataFrame([[date, odo, liters, price, full]], columns=df.columns)
            df = pd.concat([df, new_data], ignore_index=True)
            df.to_csv(FILE, index=False)
            st.success("Saved!")

# 3. Calculations
if len(df) > 1:
    # Sort by odometer to ensure math is correct
    df = df.sort_values("Odometer")
    
    # Calculate Distance and Consumption
    df['Distance'] = df['Odometer'].diff()
    df['Total_Cost'] = df['Liters'] * df['Price_Per_L']
    
    # Simple Metrics
    avg_efficiency = (df['Liters'].sum() / df['Distance'].sum()) * 100
    total_spent = df['Total_Cost'].sum()

    col1, col2 = st.columns(2)
    col1.metric("Avg L/100km", f"{avg_efficiency:.2f}")
    col2.metric("Total Spent", f"${total_spent:.2f}")

# 4. History Table
st.subheader("Recent History")
st.dataframe(df.tail(5), use_container_width=True)

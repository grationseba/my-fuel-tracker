import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import base64

# 1. Page Configuration
st.set_page_config(page_title="Fuel Tracker", page_icon="⛽", layout="wide")

# 2. Function to load the local image from your GitHub folder
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

# Try to load 'subject.png' from the root folder
bin_str = get_base64('subject.png')
if bin_str:
    bg_style = f"background-image: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url('data:image/png;base64,{bin_str}');"
else:
    bg_style = "background-color: #111;"

# 3. Custom CSS (Fixed Syntax Error with double braces)
st.markdown(f"""
    <style>
    .stApp {{
        {bg_style}
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .block-container {{ 
        padding-top: 0.5rem !important; 
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important; 
    }}
    header, footer, #MainMenu {{visibility: hidden;}}
    
    .summary-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        width: 100%;
        margin-bottom: 10px;
        background: rgba(0, 0, 0, 0.6); 
        padding: 10px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }}
    .stat-item {{ border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; }}
    .stat-label {{ font-size: 0.65rem; color: #aaa; text-transform: uppercase; display: block; }}
    .stat-value {{ font-size: 1.1rem; font-weight: bold; color: #fff; }}
    
    div[data-testid="stForm"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border-radius: 10px !important;
    }}
    label, .stMarkdown p {{ color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

# 4. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 5. Load Prices from Google Sheet (Tab: 'prices')
try:
    price_df = conn.read(worksheet="prices", ttl=0)
    prices = dict(zip(price_df['Fuel_Type'], price_df['Price']))
except:
    # Fallback if the tab is missing
    prices = {"92 Octane": 294.0, "95 Octane": 335.0}

# 6. Load Logs Data
try:
    df = conn.read(worksheet="logs", ttl=0)
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df[['Odometer', 'Liters', 'Price_Per_L']] = df[['Odometer', 'Liters', 'Price_Per_L']].apply(pd.to_numeric, errors='coerce')
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])
except:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# 7. Calculations
today = datetime.now().date()
thirty_days_ago = today - timedelta(days=31)

if not df.empty:
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    cost_30d = (df[df['Date'] >= thirty_days_ago]['Liters'] * df[df['Date'] >= thirty_days_ago]['Price_Per_L']).sum()
    
    last_trip = 0
    avg_kpl = 0
    last_kpl = 0
    if len(df) > 1:
        last_trip = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = last_trip / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        fuel_since_start = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_since_start if fuel_since_start > 0 else 0

    # 8. Summary Grid (4 Rows)
    st.markdown(f"""
    <div class="summary-grid">
        <div class="stat-item"><span class="stat-label">30 Day Cost</span><span class="stat-value">Rs. {cost_30d:,.0f}</span></div>
        <div class="stat-item"><span class="stat-label">Total KM</span><span class="stat-value">{total_km:,.0f}</span></div>
        <div class="stat-item"><span class="stat-label">Trip Dist</span><span class="stat-value">{last_trip} km</span></div>
        <div class="stat-item"><span class="stat-label">Avg KPL</span><span class="stat-value">{avg_kpl:.1f}</span></div>
        <div class="stat-item"><span class="stat-label">Last KPL</span><span class="stat-value">{last_kpl:.1f}</span></div>
        <div class="stat-item"><span class="stat-label">Total Liters</span><span class="stat-value">{total_liters:,.1f}</span></div>
        <div class="stat-item"><span class="stat-label">92 Price</span><span class="stat-value">Rs. {prices.get('92 Octane', 294)}</span></div>
        <div class="stat-item"><span class="stat-label">95 Price</span><span class="stat-value">Rs. {prices.get('95 Octane', 335)}</span></div>
    </div>
    """, unsafe_allow_html=True)

# 9. Refresh Button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# 10. Form
with st.form("fuel_form", clear_on_submit=True):
    date_in = st.date_input("Date", value=today)
    f_type = st.selectbox("Type", ["92 Octane", "95 Octane"])
    last_odo_val = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer", min_value=last_odo_val, value=last_odo_val)
    lts = st.number_input("Liters", min_value=0.0, step=0.1)
    
    if st.form_submit_button("Save Entry"):
        if lts > 0:
            # Look up price from our prices dictionary
            current_p = prices.get(f_type, 294.0 if f_type == "92 Octane" else 335.0)
            new_data = pd.DataFrame([{"Date": date_in, "Odometer": odo, "Liters": lts, "Price_Per_L": current_p, "Fuel_Type": f_type}])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="logs", data=updated_df)
            st.cache_data.clear()
            st.success("Saved!")
            st.rerun()

# 11. History Table
if not df.empty:
    st.write("---")
    hist = df[df['Date'] >= thirty_days_ago].sort_values("Odometer", ascending=False)
    st.dataframe(hist[["Date", "Odometer", "Liters"]], use_container_width=True, hide_index=True)

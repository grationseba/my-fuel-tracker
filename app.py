import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. Page Configuration
st.set_page_config(page_title="Fuel Tracker", page_icon="⛽", layout="wide")

# --- PASTE YOUR GITHUB RAW LINK HERE ---
CAR_IMAGE_URL = "https://github.com/grationseba/my-fuel-tracker/blob/main/Subject.png" 

# 2. Custom CSS
st.markdown(f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{CAR_IMAGE_URL}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    /* ... keep the rest of your CSS exactly the same ... */
    </style>
    """, unsafe_allow_html=True)
    
# 3. CSS for Grid and Transparency
st.markdown(f"""
    <style>
    .stApp {{ {bg_style} background-size: cover; background-position: center; background-attachment: fixed; }}
    .block-container {{ padding: 0.5rem !important; }}
    header, footer, #MainMenu {{visibility: hidden;}}
    .summary-grid {{
        display: grid; grid-template-columns: 1fr 1fr; gap: 8px; width: 100%; margin-bottom: 10px;
        background: rgba(0, 0, 0, 0.6); padding: 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);
    }}
    .stat-item {{ border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; }}
    .stat-label {{ font-size: 0.65rem; color: #aaa; text-transform: uppercase; display: block; }}
    .stat-value {{ font-size: 1.1rem; font-weight: bold; color: #fff; }}
    div[data-testid="stForm"] {{ background: rgba(0, 0, 0, 0.7) !important; border-radius: 10px !important; }}
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
    # Fallback if the 'prices' sheet is missing or errors
    prices = {"92 Octane": 294.0, "95 Octane": 335.0}

# 6. Load Logs Data
try:
    df = conn.read(worksheet="logs", ttl=0)
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df[['Odometer', 'Liters', 'Price_Per_L']] = df[['Odometer', 'Liters', 'Price_Per_L']].apply(pd.to_numeric, errors='coerce')
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
except:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# 7. Calculations
today = datetime.now().date()
thirty_days_ago = today - timedelta(days=31)

if not df.empty:
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    cost_30d = (df[df['Date'] >= thirty_days_ago]['Liters'] * df[df['Date'] >= thirty_days_ago]['Price_Per_L']).sum()
    last_trip = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2] if len(df) > 1 else 0
    avg_kpl = total_km / df['Liters'].iloc[1:].sum() if len(df) > 1 and df['Liters'].iloc[1:].sum() > 0 else 0
    last_kpl = last_trip / df['Liters'].iloc[-1] if len(df) > 0 and df['Liters'].iloc[-1] > 0 else 0

    # 8. Summary Grid
    st.markdown(f"""
    <div class="summary-grid">
        <div class="stat-item"><span class="stat-label">30 Day Cost</span><span class="stat-value">Rs. {cost_30d:,.0f}</span></div>
        <div class="stat-item"><span class="stat-label">Total KM</span><span class="stat-value">{total_km:,.0f}</span></div>
        <div class="stat-item"><span class="stat-label">Trip</span><span class="stat-value">{last_trip} km</span></div>
        <div class="stat-item"><span class="stat-label">Avg KPL</span><span class="stat-value">{avg_kpl:.1f}</span></div>
        <div class="stat-item"><span class="stat-label">Last KPL</span><span class="stat-value">{last_kpl:.1f}</span></div>
        <div class="stat-item"><span class="stat-label">Total L</span><span class="stat-value">{total_liters:,.1f}</span></div>
        <div class="stat-item"><span class="stat-label">92 Price</span><span class="stat-value">Rs. {prices['92 Octane']}</span></div>
        <div class="stat-item"><span class="stat-label">95 Price</span><span class="stat-value">Rs. {prices['95 Octane']}</span></div>
    </div>
    """, unsafe_allow_html=True)

# 9. Form
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

with st.form("fuel_form", clear_on_submit=True):
    date_in = st.date_input("Date", value=today)
    f_type = st.selectbox("Type", ["92 Octane", "95 Octane"])
    odo = st.number_input("Odometer", value=int(df['Odometer'].max()) if not df.empty else 0)
    lts = st.number_input("Liters", min_value=0.0, step=0.1)
    
    if st.form_submit_button("Save Entry"):
        if lts > 0:
            new_row = pd.DataFrame([{"Date": date_in, "Odometer": odo, "Liters": lts, "Price_Per_L": prices[f_type], "Fuel_Type": f_type}])
            conn.update(worksheet="logs", data=pd.concat([df, new_row], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

# 10. History
if not df.empty:
    st.write("---")
    hist = df[df['Date'] >= thirty_days_ago].sort_values("Odometer", ascending=False)
    st.dataframe(hist[["Date", "Odometer", "Liters"]], use_container_width=True, hide_index=True)

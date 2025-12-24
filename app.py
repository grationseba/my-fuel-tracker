import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import base64

# 1. Page Configuration
st.set_page_config(page_title="Fuel Tracker", page_icon="⛽", layout="wide")

# --- PRICES (Update these two numbers if the govt changes prices) ---
PRICE_92 = 294.0
PRICE_95 = 335.0

# 2. Function to load the local image
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

# Try to load 'subject.png'
bin_str = get_base64('subject.png')
if bin_str:
    bg_image_style = f'background-image: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("data:image/png;base64,{bin_str}");'
else:
    bg_image_style = 'background-color: #111;'

# 3. Custom CSS
st.markdown(f"""
    <style>
    .stApp {{
        {bg_image_style}
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .block-container {{ padding-top: 0.5rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }}
    header, footer, #MainMenu {{visibility: hidden;}}
    
    .summary-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        width: 100%;
        margin-bottom: 15px;
        background: rgba(0, 0, 0, 0.6); 
        padding: 12px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }}
    .stat-item {{ border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; }}
    .stat-label {{ font-size: 0.65rem; color: #aaa; text-transform: uppercase; display: block; }}
    .stat-value {{ font-size: 1.1rem; font-weight: bold; color: #fff; }}
    
    div[data-testid="stForm"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border-radius: 10px !important;
    }}
    label, .stMarkdown p {{ color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

# 4. Connection & Data Loading
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df = conn.read(worksheet="logs", ttl=0)
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        for col in ['Odometer', 'Liters', 'Price_Per_L']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])
except:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# 5. Calculations
today = datetime.now().date()
thirty_days_ago = today - timedelta(days=31)

if not df.empty:
    total_km = df['Odometer'].max() - df['Odometer'].min()
    total_liters = df['Liters'].sum()
    recent_df = df[df['Date'] >= thirty_days_ago]
    cost_30d = (recent_df['Liters'] * recent_df['Price_Per_L']).sum()
    
    last_trip_dist = 0
    last_kpl = 0
    avg_kpl = 0
    if len(df) > 1:
        last_trip_dist = df['Odometer'].iloc[-1] - df['Odometer'].iloc[-2]
        last_kpl = last_trip_dist / df['Liters'].iloc[-1] if df['Liters'].iloc[-1] > 0 else 0
        avg_kpl = total_km / df['Liters'].iloc[1:].sum() if df['Liters'].iloc[1:].sum() > 0 else 0

    # 6. Summary Grid (4 Rows)
    st.markdown(f"""
    <div class="summary-grid">
        <div class="stat-item"><span class="stat-label">Last 30 Days Cost</span><span class="stat-value">Rs. {cost_30d:,.0f}</span></div>
        <div class="stat-item"><span class="stat-label">Total KM</span><span class="stat-value">{total_km:,.0f}</span></div>
        <div class="stat-item"><span class="stat-label">Trip Distance</span><span class="stat-value">{last_trip_dist} km</span></div>
        <div class="stat-item"><span class="stat-label">Avg KPL</span><span class="stat-value">{avg_kpl:.1f}</span></div>
        <div class="stat-item"><span class="stat-label">Last KPL</span><span class="stat-value">{last_kpl:.1f}</span></div>
        <div class="stat-item"><span class="stat-label">Total Liters</span><span class="stat-value">{total_liters:,.1f} L</span></div>
        <div class="stat-item"><span class="stat-label">92 Price</span><span class="stat-value">Rs. {PRICE_92}</span></div>
        <div class="stat-item"><span class="stat-label">95 Price</span><span class="stat-value">Rs. {PRICE_95}</span></div>
    </div>
    """, unsafe_allow_html=True)

# 7. Form
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

with st.form("fuel_form", clear_on_submit=True):
    date_input = st.date_input("Date", value=today)
    fuel_type = st.selectbox("Type", ["92 Octane", "95 Octane"])
    last_odo = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer", min_value=last_odo, value=last_odo)
    liters = st.number_input("Liters", min_value=0.0, step=0.1)
    
    if st.form_submit_button("Save Entry"):
        if liters > 0:
            # Automatic price selection
            current_price = PRICE_92 if fuel_type == "92 Octane" else PRICE_95
            new_row = pd.DataFrame([{"Date": date_input, "Odometer": odo, "Liters": liters, "Price_Per_L": current_price, "Fuel_Type": fuel_type}])
            conn.update(worksheet="logs", data=pd.concat([df, new_row], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

# 8. History
if not df.empty:
    st.write("---")
    hist = df[df['Date'] >= thirty_days_ago].sort_values("Odometer", ascending=False)
    st.dataframe(hist[["Date", "Odometer", "Liters"]], use_container_width=True, hide_index=True)

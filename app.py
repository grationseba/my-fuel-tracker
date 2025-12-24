import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import base64

# 1. Page Configuration
st.set_page_config(page_title="Fuel Tracker", page_icon="⛽", layout="wide")

# 2. Function to load the local image and convert to Base64
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Try to load the image 'subject.png' from your GitHub folder
try:
    bin_str = get_base64('subject.png')
    bg_image_style = f'background-image: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("data:image/png;base64,{bin_str}");'
except Exception:
    # If the image isn't found, use a dark grey background
    bg_image_style = 'background-color: #111;'

# 3. Custom CSS for Background, Mobile Grid, and Transparency
st.markdown(f"""
    <style>
    /* Background Styling */
    .stApp {{
        {bg_image_style}
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    /* Remove padding and headers */
    .block-container {{ 
        padding-top: 0.5rem !important; 
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important; 
    }}
    header, footer, #MainMenu {{visibility: hidden;}}
    
    /* Summary Grid - 2 Columns */
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
    .stat-label {{ font-size: 0.7rem; color: #aaa; text-transform: uppercase; display: block; }}
    .stat-value {{ font-size: 1.15rem; font-weight: bold; color: #fff; }}
    
    /* Input Form Glass Effect */
    div[data-testid="stForm"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
    }}
    
    /* Force text colors to be visible on image */
    label, .stMarkdown p, .stSelectbox label, .stNumberInput label {{
        color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# 4. Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 5. Load Data
try:
    df = conn.read(worksheet="logs", ttl=0)
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        for col in ['Odometer', 'Liters', 'Price_Per_L']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['Odometer', 'Liters']).sort_values("Odometer")
    else:
        df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])
except Exception:
    df = pd.DataFrame(columns=["Date", "Odometer", "Liters", "Price_Per_L", "Fuel_Type"])

# 6. Calculations
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
        fuel_consumed = df['Liters'].iloc[1:].sum()
        avg_kpl = total_km / fuel_consumed if fuel_consumed > 0 else 0

    # 7. Display Summary Grid
    st.markdown(f"""
    <div class="summary-grid">
        <div class="stat-item">
            <span class="stat-label">Last 30 Days Cost</span>
            <span class="stat-value">Rs. {cost_30d:,.0f}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Total KM</span>
            <span class="stat-value">{total_km:,.0f} km</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Trip Distance</span>
            <span class="stat-value">{last_trip_dist} km</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Avg KPL</span>
            <span class="stat-value">{avg_kpl:.1f}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Last KPL</span>
            <span class="stat-value">{last_kpl:.1f}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Total Liters</span>
            <span class="stat-value">{total_liters:,.0f} L</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 8. Action Buttons
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# 9. Input Form
with st.form("fuel_form", clear_on_submit=True):
    date_input = st.date_input("Date", value=today)
    fuel_type = st.selectbox("Type", ["92 Octane", "95 Octane"])
    last_odo_val = int(df['Odometer'].max()) if not df.empty else 0
    odo = st.number_input("Odometer", min_value=last_odo_val, value=last_odo_val)
    liters = st.number_input("Liters", min_value=0.0)
    price = st.number_input("Price", value=294.0 if fuel_type == "92 Octane" else 335.0)
    
    if st.form_submit_button("Save Entry"):
        if liters > 0:
            new_data = pd.DataFrame([{"Date": date_input, "Odometer": odo, "Liters": liters, "Price_Per_L": price, "Fuel_Type": fuel_type}])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="logs", data=updated_df)
            st.cache_data.clear()
            st.success("Entry Saved!")
            st.rerun()

# 10. History Table
if not df.empty:
    st.write("---")
    history_view = df[df['Date'] >= thirty_days_ago].copy()
    if not history_view.empty:
        history_view['Date'] = history_view['Date'].apply(lambda x: x.strftime('%m-%d'))
        st.dataframe(
            history_view.sort_values("Odometer", ascending=False)[["Date", "Odometer", "Liters"]], 
            use_container_width=True, 
            hide_index=True
        )

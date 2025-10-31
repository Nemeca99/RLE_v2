#!/usr/bin/env python3
"""
RLE SCADA Dashboard - Cloud Version
Pulls live data from GitHub for Streamlit Cloud deployment
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
import requests
import time
import io

# Page config
st.set_page_config(
    page_title="RLE LIVE Monitor (Cloud)",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# GitHub config - update these!
GITHUB_USER = "Nemeca99"
GITHUB_REPO = "RLE"
GITHUB_BRANCH = "live-data"
CSV_PATH = "lab/sessions/live/latest.csv"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{CSV_PATH}"

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    .metric-card {
        background: #0f3460;
        border: 2px solid #00d4ff;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .big-number {
        font-size: 72px;
        font-weight: bold;
        text-align: center;
        margin: 20px 0;
    }
    .status-green { color: #00ff88; }
    .status-yellow { color: #ffaa00; }
    .status-red { color: #ff4444; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=10)  # Cache for 10 seconds
def fetch_from_github():
    """Fetch latest CSV from GitHub"""
    try:
        response = requests.get(GITHUB_RAW_URL, timeout=5)
        if response.status_code == 200:
            return pd.read_csv(io.StringIO(response.text))
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def get_rle_color(rle):
    """Get color based on RLE value"""
    if pd.isna(rle):
        return '#666666', 'status-gray', '❓ NO DATA'
    if rle >= 0.8:
        return '#00ff88', 'status-green', '✅ EXCELLENT'
    elif rle >= 0.5:
        return '#ffaa00', 'status-yellow', '⚠️ WARNING'
    else:
        return '#ff4444', 'status-red', '🔴 COLLAPSE'

def create_gauge(value, title, min_val=0, max_val=1):
    """Create gauge widget"""
    if pd.isna(value):
        value = 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': get_rle_color(value)[0]},
            'steps': [
                {'range': [0, 0.5], 'color': '#0f3460'},
                {'range': [0.5, 0.8], 'color': '#16213e'},
                {'range': [0.8, 1.0], 'color': '#0f3460'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 0.9
            }
        }
    ))
    fig.update_layout(height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def main():
    # Title
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #00d4ff;'>🔥 RLE LIVE Monitor (Cloud)</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #7fdbda;'>Real-Time Thermal Efficiency - Pulling from GitHub</p>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        st.markdown(f"**GitHub:** `{GITHUB_USER}/{GITHUB_REPO}`")
        st.markdown(f"**Branch:** `{GITHUB_BRANCH}`")
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (10s)", value=True)
        refresh_interval = st.slider("Interval (seconds)", 5, 60, 10)
        
        # Device selection
        st.markdown("---")
        st.markdown("### 📡 Device Selection")
        device = st.radio("Show Device", ['cpu', 'gpu', 'both'], index=0)
        
        # Warning thresholds
        st.markdown("---")
        st.markdown("### 🚨 Alert Thresholds")
        rle_warning = st.slider("RLE Warning", 0.0, 1.0, 0.5, 0.1)
        temp_warning = st.slider("Temp Warning (°C)", 40.0, 100.0, 70.0, 5.0)
    
    # Fetch data
    df = fetch_from_github()
    
    if df.empty:
        st.error(f"⚠️ No data available from GitHub. Make sure:")
        st.markdown(f"""
        1. Monitor is running locally with `push_to_github.py`
        2. GitHub branch `{GITHUB_BRANCH}` exists
        3. File exists at: `{CSV_PATH}`
        """)
        if auto_refresh:
            time.sleep(refresh_interval)
            st.cache_data.clear()
            st.rerun()
        return
    
    # Filter device
    if device != 'both':
        df_filtered = df[df['device'] == device].copy()
    else:
        df_filtered = df.copy()
    
    if len(df_filtered) == 0:
        st.error(f"No data found for device: {device}")
        return
    
    # Get latest values
    latest = df_filtered.iloc[-1]
    rle_val = latest.get('rle_norm', latest.get('rle_smoothed', latest.get('rle_raw', 0)))
    temp_val = latest.get('temp_c', 0)
    power_val = latest.get('power_w', 0)
    util_val = latest.get('util_pct', 0)
    t_sustain = latest.get('t_sustain_s', 0)
    collapse = latest.get('collapse', 0)
    
    # File info
    last_update = datetime.now()  # GitHub fetch time
    sample_count = len(df_filtered)
    
    # Top bar: Big RLE display
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        rle_color, color_class, status_text = get_rle_color(rle_val)
        rle_display = f"{rle_val:.4f}" if not pd.isna(rle_val) else "N/A"
        st.markdown(f"""
        <div class='metric-card'>
            <p style='text-align: center; color: #7fdbda; font-size: 24px; margin: 0;'>CURRENT EFFICIENCY</p>
            <p class='big-number {color_class}' style='color: {rle_color};'>{rle_display}</p>
            <p style='text-align: center; color: #00d4ff; font-size: 20px; margin: 0;'>{status_text}</p>
            <p style='text-align: center; color: #888; font-size: 12px; margin: 5px 0 0 0;'>
                GitHub: {GITHUB_BRANCH} | {sample_count} samples | Updated: {last_update.strftime('%H:%M:%S')}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown("### 📊 Live Gauge")
        st.plotly_chart(create_gauge(rle_val, "RLE (normalized)", 0, 1), width='stretch')
        
        st.markdown("### 🔢 System Status")
        st.metric("Temperature", f"{temp_val:.1f}°C" if not pd.isna(temp_val) else "N/A")
        st.metric("Power", f"{power_val:.1f}W" if not pd.isna(power_val) else "N/A")
        st.metric("Utilization", f"{util_val:.1f}%" if not pd.isna(util_val) else "N/A")
        
        collapse_status = "🔴 COLLAPSE" if collapse else "🟢 STABLE"
        st.markdown(f"### ⚠️ Status: {collapse_status}")
    
    with col2:
        st.markdown("### 📈 Time Series")
        
        # Show last 30 minutes
        if 'timestamp' in df_filtered.columns:
            df_filtered['timestamp_dt'] = pd.to_datetime(df_filtered['timestamp'])
            window_minutes = 30
            cutoff = df_filtered['timestamp_dt'].max() - timedelta(minutes=window_minutes)
            df_window = df_filtered[df_filtered['timestamp_dt'] >= cutoff]
        else:
            df_window = df_filtered
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=("RLE Efficiency", "Temperature & Power", "Utilization"),
            row_heights=[0.4, 0.3, 0.3]
        )
        
        # RLE trace
        rle_series = (
            df_window['rle_norm'] if 'rle_norm' in df_window.columns else
            df_window.get('rle_smoothed', df_window.get('rle_raw', 0))
        )
        if 'timestamp_dt' in df_window.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_window['timestamp_dt'],
                    y=rle_series,
                    mode='lines',
                    name='RLE',
                    line=dict(color='#00d4ff', width=2)
                ),
                row=1, col=1
            )
        
        # Temperature trace
        if 'temp_c' in df_window.columns and not df_window['temp_c'].isna().all():
            if 'timestamp_dt' in df_window.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_window['timestamp_dt'],
                        y=df_window['temp_c'],
                        mode='lines',
                        name='Temperature',
                        line=dict(color='#ff4444', width=2)
                    ),
                    row=2, col=1
                )
        
        # Power trace
        if 'power_w' in df_window.columns and not df_window['power_w'].isna().all():
            if 'timestamp_dt' in df_window.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_window['timestamp_dt'],
                        y=df_window['power_w'],
                        mode='lines',
                        name='Power',
                        line=dict(color='#00ff88', width=2)
                    ),
                    row=2, col=1
                )
        
        # Utilization trace
        if 'util_pct' in df_window.columns and not df_window['util_pct'].isna().all():
            if 'timestamp_dt' in df_window.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_window['timestamp_dt'],
                        y=df_window['util_pct'],
                        mode='lines',
                        name='Utilization',
                        line=dict(color='#ffaa00', width=2)
                    ),
                    row=3, col=1
                )
        
        fig.update_layout(
            height=800,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15, 52, 96, 0.5)',
            font=dict(color='#7fdbda'),
            showlegend=False
        )
        
        st.plotly_chart(fig, width='stretch', theme=None)
    
    with col3:
        st.markdown("### 📉 Statistics")
        
        numeric_cols = (['rle_norm'] if 'rle_norm' in df_filtered.columns else ['rle_smoothed']) + ['temp_c', 'power_w', 'util_pct']
        available_cols = [col for col in numeric_cols if col in df_filtered.columns]
        if available_cols:
            stats_df = df_filtered[available_cols].describe()
            st.dataframe(stats_df, width='stretch')
        
        # Collapse count
        if 'collapse' in df_filtered.columns:
            collapse_count = df_filtered['collapse'].sum()
            total_samples = len(df_filtered)
            collapse_pct = 100.0 * collapse_count / total_samples if total_samples > 0 else 0
            st.metric("Collapse Events", f"{collapse_count}/{total_samples} ({collapse_pct:.1f}%)")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.cache_data.clear()
        st.rerun()

if __name__ == '__main__':
    main()


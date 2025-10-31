"""
Real-time RLE monitor visualization with Streamlit
Tail-follows the latest CSV log file
"""

import streamlit as st
import pandas as pd
import time
import glob
from pathlib import Path
import numpy as np

# Page config
st.set_page_config(
    page_title="RLE Real-time Monitor",
    page_icon="📊",
    layout="wide"
)

st.title("📊 RLE Real-time Hardware Monitor")

# Find latest CSV
@st.cache_data(ttl=1)
def get_latest_csv():
    sessions = Path("../sessions/recent")
    csvs = sorted(sessions.glob("rle_*.csv"), reverse=True)
    return csvs[0] if csvs else None

# Load and tail data
def load_data(csv_path, tail_lines=500):
    """Load last N lines from CSV"""
    if not csv_path or not csv_path.exists():
        return pd.DataFrame()
    
    try:
        # Read last N lines
        with open(csv_path, 'rb') as f:
            # Try to skip to end
            try:
                f.seek(-50000, 2)  # 50KB from end
            except:
                f.seek(0)
            
            lines = f.read().decode('utf-8', errors='ignore').splitlines()
            if len(lines) > tail_lines:
                lines = lines[-tail_lines:]
        
        from io import StringIO
        df = pd.read_csv(StringIO('\n'.join(lines)))
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        return df
    except Exception as e:
        return pd.DataFrame()

# Main loop
latest_csv = get_latest_csv()

if latest_csv:
    st.sidebar.write(f"📁 File: `{latest_csv.name}`")
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider("Interval (s)", 1, 10, 2)
    
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
    
    # Load data
    df = load_data(latest_csv)
    
    if len(df) > 0:
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Samples", len(df))
        
        with col2:
            if 'power_w' in df.columns:
                st.metric("Power", f"{df['power_w'].max():.0f}W")
        
        with col3:
            if 'temp_c' in df.columns:
                st.metric("Temp", f"{df['temp_c'].max():.1f}°C")
        
        with col4:
            if 'rle_smoothed' in df.columns:
                st.metric("RLE", f"{df['rle_smoothed'].max():.3f}")
        
        # Main charts
        st.subheader("Power & Temperature")
        
        if 'power_w' in df.columns and 'temp_c' in df.columns:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=("Power Consumption", "Temperature"),
                vertical_spacing=0.1
            )
            
            # Power
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['power_w'],
                    mode='lines',
                    name='Power (W)',
                    line=dict(color='#FF6B6B', width=2)
                ),
                row=1, col=1
            )
            
            # Temp
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['temp_c'],
                    mode='lines',
                    name='Temp (°C)',
                    line=dict(color='#4ECDC4', width=2)
                ),
                row=2, col=1
            )
            
            fig.update_layout(height=500, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        
        # RLE chart
        st.subheader("RLE Efficiency")
        
        if 'rle_smoothed' in df.columns:
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['rle_smoothed'],
                mode='lines',
                name='Smoothed RLE',
                line=dict(color='#95E1D3', width=2)
            ))
            
            # Add rolling peak if available
            if 'rolling_peak' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['rolling_peak'],
                    mode='lines',
                    name='Rolling Peak',
                    line=dict(color='#FFD700', width=1, dash='dash')
                ))
            
            # Mark collapses
            if 'collapse' in df.columns and df['collapse'].sum() > 0:
                collapsed_idx = df[df['collapse'] == 1].index
                collapsed_values = df.loc[collapsed_idx, 'rle_smoothed']
                fig.add_trace(go.Scatter(
                    x=collapsed_idx,
                    y=collapsed_values,
                    mode='markers',
                    name='Collapse',
                    marker=dict(size=8, color='red', symbol='x')
                ))
            
            fig.update_layout(
                height=300,
                xaxis_title="Sample",
                yaxis_title="RLE",
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Split components if available
        if 'E_th' in df.columns and 'E_pw' in df.columns:
            st.subheader("Efficiency Components")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.line_chart(df[['E_th']])
            
            with col2:
                st.line_chart(df[['E_pw']])
        
        # Raw data table (last 20 rows)
        with st.expander("📋 Raw Data (last 20 rows)"):
            st.dataframe(df.tail(20))
    
    else:
        st.warning("Waiting for data...")
        st.info("Start the monitor with: `python start_monitor.py`")

else:
    st.error("No session data found in `sessions/recent/`")
    st.info("Run the monitor first:\n```bash\ncd lab\npython start_monitor.py --mode gpu\n```")


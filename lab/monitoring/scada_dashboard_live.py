#!/usr/bin/env python3
"""
Live SCADA-style RLE Dashboard
Launches monitor in background and displays real-time updates
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
import json
import subprocess
import threading
import time
import os

# Page config
st.set_page_config(
    page_title="RLE Live Monitor",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
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
    .status-green { color: #00ff88; }
    .status-yellow { color: #ffaa00; }
    .status-red { color: #ff4444; }
    .big-number {
        font-size: 72px;
        font-weight: bold;
        text-align: center;
        margin: 20px 0;
    }
    .led-indicator {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 10px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=1)  # 1 second cache for live data
def load_latest_csv(file_path):
    """Load latest CSV data"""
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
            return df
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
    # Title bar
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #00d4ff;'>🔥 RLE LIVE Monitor</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #7fdbda;'>Real-Time Thermal Efficiency Control Center</p>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        
        # Mode selection
        mode = st.radio("Monitoring Mode", ['cpu', 'gpu', 'both'], index=1)
        sample_hz = st.slider("Sample Rate (Hz)", 1, 5, 1)
        
        # Device selection for display
        st.markdown("---")
        st.markdown("### 📡 Display Device")
        device = st.radio("Show Device", ['cpu', 'gpu', 'both'], index=0)
        
        # Auto-refresh
        st.markdown("---")
        st.markdown("### ⚙️ Display Settings")
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
        smoothing_window = st.slider("Smoothing Window", 1, 20, 5)
        
        # Warning thresholds
        st.markdown("---")
        st.markdown("### 🚨 Alert Thresholds")
        rle_warning = st.slider("RLE Warning", 0.0, 1.0, 0.5, 0.1)
        temp_warning = st.slider("Temp Warning (°C)", 40.0, 100.0, 70.0, 5.0)
        
        # HWiNFO path
        st.markdown("---")
        st.markdown("### 🌡️ HWiNFO Integration")
        script_dir = Path(__file__).parent.resolve()
        root_dir = script_dir.parent.parent
        default_hwinfo = str(root_dir / "sessions" / "hwinfo" / "10_30_2025_702pm.CSV")
        hwinfo_path = st.text_input("HWiNFO CSV Path (optional)", value=default_hwinfo)
        
        # Monitor control
        st.markdown("---")
        st.markdown("### ▶️ Monitor Control")
        if st.button("▶️ START Monitor"):
            try:
                # Launch monitor in background - resolve to absolute paths
                script_dir = Path(__file__).parent.resolve()  # monitoring/
                lab_dir = script_dir.parent  # lab/
                root_dir = lab_dir.parent  # RLE/
                monitor_script = (lab_dir / "start_monitor.py").resolve()
                venv_python = (root_dir / "venv" / "Scripts" / "python.exe").resolve()
                
                # Debug info
                st.info(f"Lab dir: {lab_dir}\nMonitor: {monitor_script}\nPython: {venv_python}")
                
                # Check if files exist
                if not venv_python.exists():
                    st.error(f"Python not found: {venv_python}")
                elif not monitor_script.exists():
                    st.error(f"Monitor script not found: {monitor_script}")
                else:
                    # Build command with optional HWiNFO path
                    cmd = f'"{str(venv_python)}" "{str(monitor_script)}" --mode {mode} --sample-hz {sample_hz}'
                    if hwinfo_path and Path(hwinfo_path).exists():
                        cmd += f' --hwinfo-csv "{hwinfo_path}"'
                    
                    process = subprocess.Popen(
                        cmd, 
                        shell=True, 
                        cwd=str(lab_dir),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    st.success(f"Monitor started in {mode} mode (PID: {process.pid})")
            except Exception as e:
                st.error(f"Failed to start monitor: {e}")
                st.exception(e)
        
        if st.button("⏹️ STOP Monitor"):
            try:
                subprocess.run("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq start_monitor*\"", shell=True, capture_output=True)
                st.warning("Monitor stopped")
            except Exception as e:
                st.error(f"Failed to stop monitor: {e}")
    
    # Find latest CSV - resolve to absolute paths
    script_dir = Path(__file__).parent.resolve()  # monitoring/
    lab_dir = script_dir.parent  # lab/
    sessions_dir = (lab_dir / "sessions" / "recent").resolve()
    # Get files matching the monitor's naming pattern (rle_YYYYMMDD_HH.csv)
    csv_files = sorted([f for f in sessions_dir.glob("rle_*.csv") 
                       if f.name.startswith("rle_") and len(f.name.split("_")) == 3], 
                      key=lambda x: x.stat().st_mtime, reverse=True) if sessions_dir.exists() else []
    
    if len(csv_files) == 0:
        st.error(f"No session data found in {sessions_dir}. Click 'START Monitor' to begin.")
        return
    
    latest_csv = csv_files[0]
    
    # Load data
    df = load_latest_csv(latest_csv)
    
    if len(df) == 0:
        st.warning(f"No data in {latest_csv.name} yet. Waiting for monitor...")
        if auto_refresh:
            time.sleep(2)
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
    
    # Get latest values (prefer normalized RLE if available)
    latest = df_filtered.iloc[-1]
    rle_val = latest.get('rle_norm', latest.get('rle_smoothed', latest.get('rle_raw', 0)))
    temp_val = latest.get('temp_c', 0)
    power_val = latest.get('power_w', 0)
    util_val = latest.get('util_pct', 0)
    t_sustain = latest.get('t_sustain_s', 0)
    collapse = latest.get('collapse', 0)
    
    # File info
    file_size = os.path.getsize(latest_csv) / 1024  # KB
    file_age = datetime.now() - datetime.fromtimestamp(latest_csv.stat().st_mtime)
    
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
                File: {latest_csv.name} | {file_size:.1f} KB | {file_age.seconds}s old | {len(df_filtered)} samples
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown("### 📊 Live Gauge")
        st.plotly_chart(create_gauge(rle_val, "RLE (normalized)", 0, 1), width='stretch')
        
        st.markdown("### 🔢 System Status")
        st.metric("Temperature", f"{temp_val:.1f}°C" if not pd.isna(temp_val) else "N/A", delta=None)
        st.metric("Power", f"{power_val:.1f}W" if not pd.isna(power_val) else "N/A", delta=None)
        st.metric("Utilization", f"{util_val:.1f}%" if not pd.isna(util_val) else "N/A", delta=None)
        st.metric("Sustain Time", f"{t_sustain:.1f}s" if not pd.isna(t_sustain) else "N/A", delta=None)
        
        # Status indicators
        st.markdown("### ⚠️ System Status")
        led_color = get_rle_color(rle_val)[0]
        collapse_status = "🔴 COLLAPSE DETECTED" if collapse else "🟢 STABLE"
        st.markdown(f"<div style='color: {led_color}; font-size: 18px;'>● {collapse_status}</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📈 Time Series")
        
        # Show last N minutes
        if len(df_filtered) > 0:
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
        
        # RLE trace (prefer normalized)
        rle_series = (
            df_window['rle_norm'] if 'rle_norm' in df_window.columns else
            df_window.get('rle_smoothed', df_window.get('rle_raw', 0))
        )
        fig.add_trace(
            go.Scatter(
                x=df_window['timestamp_dt'],
                y=rle_series,
                mode='lines',
                name='RLE',
                line=dict(color='#00d4ff', width=2),
                hovertemplate='RLE: %{y:.4f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Temperature trace
        if 'temp_c' in df_window.columns:
            temp_data = df_window['temp_c']
            if temp_data.notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=df_window['timestamp_dt'],
                        y=temp_data,
                        mode='lines',
                        name='Temperature',
                        line=dict(color='#ff4444', width=2),
                        hovertemplate='Temp: %{y:.1f}°C<extra></extra>'
                    ),
                    row=2, col=1
                )
        
        # Power trace
        if 'power_w' in df_window.columns:
            power_data = df_window['power_w']
            if power_data.notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=df_window['timestamp_dt'],
                        y=power_data,
                        mode='lines',
                        name='Power',
                        line=dict(color='#00ff88', width=2),
                        hovertemplate='Power: %{y:.1f}W<extra></extra>'
                    ),
                    row=2, col=1
                )
        
        # Utilization trace
        if 'util_pct' in df_window.columns:
            util_data = df_window['util_pct']
            if util_data.notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=df_window['timestamp_dt'],
                        y=util_data,
                        mode='lines',
                        name='Utilization',
                        line=dict(color='#ffaa00', width=2),
                        hovertemplate='Util: %{y:.1f}%<extra></extra>'
                    ),
                    row=3, col=1
                )
        
        # Update layout
        fig.update_layout(
            height=800,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15, 52, 96, 0.5)',
            font=dict(color='#7fdbda'),
            hovermode='x unified',
            showlegend=False,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        fig.update_xaxes(showgrid=True, gridcolor='#0f3460', color='#7fdbda')
        fig.update_yaxes(showgrid=True, gridcolor='#0f3460', color='#7fdbda')
        
        st.plotly_chart(fig, width='stretch', theme=None)
    
    with col3:
        st.markdown("### 📉 Statistics")
        
        # Rolling stats (prefer normalized RLE)
        numeric_cols = (['rle_norm'] if 'rle_norm' in df_filtered.columns else ['rle_smoothed']) + ['temp_c', 'power_w', 'util_pct']
        available_cols = [col for col in numeric_cols if col in df_filtered.columns]
        if available_cols:
            stats_df = df_filtered[available_cols].describe()
            st.dataframe(stats_df, width='stretch')
        
        st.markdown("### 📊 Distribution")
        
        # RLE distribution
        if len(df_filtered) > 0:
            rle_col = 'rle_norm' if 'rle_norm' in df_filtered.columns else ('rle_smoothed' if 'rle_smoothed' in df_filtered.columns else 'rle_raw')
            if rle_col in df_filtered.columns:
                fig_dist = px.histogram(
                    df_filtered,
                    x=rle_col,
                    nbins=30,
                    color_discrete_sequence=[get_rle_color(0.7)[0]]
                )
                fig_dist.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(15, 52, 96, 0.5)',
                    font=dict(color='#7fdbda'),
                    showlegend=False,
                    height=300
                )
                fig_dist.update_xaxes(showgrid=True, gridcolor='#0f3460')
                fig_dist.update_yaxes(showgrid=True, gridcolor='#0f3460')
                st.plotly_chart(fig_dist, width='stretch', theme=None)
        
        # Collapse count
        if 'collapse' in df_filtered.columns:
            collapse_count = df_filtered['collapse'].sum()
            total_samples = len(df_filtered)
            collapse_pct = 100.0 * collapse_count / total_samples if total_samples > 0 else 0
            st.metric("Collapse Events", f"{collapse_count}/{total_samples} ({collapse_pct:.1f}%)")
        
        # Export button
        st.markdown("---")
        if len(df_filtered) > 0:
            csv_export = df_filtered.to_csv(index=False)
            st.download_button(
                label="📥 Export CSV",
                data=csv_export,
                file_name=f"rle_live_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # Bottom panel: Event log
    st.markdown("---")
    st.markdown("### 📋 Event Log")
    
    # Find alerts
    if 'alerts' in df_filtered.columns:
        alert_rows = df_filtered[df_filtered['alerts'].notna() & (df_filtered['alerts'] != '')]
        if len(alert_rows) > 0:
            rle_col = 'rle_norm' if 'rle_norm' in df_filtered.columns else ('rle_smoothed' if 'rle_smoothed' in df_filtered.columns else 'rle_raw')
            cols = ['timestamp', 'alerts', rle_col, 'temp_c', 'power_w']
            cols = [c for c in cols if c in alert_rows.columns]
            alert_display = alert_rows[cols].tail(20)
            st.dataframe(alert_display, width='stretch')
        else:
            st.info("No alerts in current session")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(5)
        st.rerun()

if __name__ == '__main__':
    main()


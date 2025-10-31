#!/usr/bin/env python3
"""
SCADA-style RLE Dashboard
Modern control-room visualization for thermal efficiency monitoring
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from pathlib import Path
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="RLE SCADA Monitor",
    page_icon="📊",
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

def load_csv(file_path=None, uploaded_file=None):
    """Load CSV data from file path or uploaded file"""
    if uploaded_file is not None:
        # Don't cache uploaded files - they change
        return pd.read_csv(uploaded_file)
    elif file_path and Path(file_path).exists():
        # Cache repo files
        return _load_cached_csv(file_path)
    else:
        return pd.DataFrame()

@st.cache_data
def _load_cached_csv(file_path):
    """Cached loader for repo files"""
    return pd.read_csv(file_path)

@st.cache_data
def filter_device(df, device):
    """Filter data by device"""
    return df[df['device'] == device].copy()

def get_rle_color(rle):
    """Get color based on RLE value"""
    if rle >= 0.8:
        return '#00ff88', 'status-green', '✅ EXCELLENT'
    elif rle >= 0.5:
        return '#ffaa00', 'status-yellow', '⚠️ WARNING'
    else:
        return '#ff4444', 'status-red', '🔴 COLLAPSE'

def create_gauge(value, title, min_val=0, max_val=1):
    """Create gauge widget"""
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
        st.markdown("<h1 style='text-align: center; color: #00d4ff;'>📊 RLE SCADA Monitor</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #7fdbda;'>Recursive Load Efficiency Control Center</p>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        
        # File upload option
        st.markdown("### 📁 Upload CSV File")
        uploaded_file = st.file_uploader("Choose RLE CSV file", type=['csv'], help="Upload a session CSV from your monitoring")
        
        # File selection from repo (if files exist)
        data_sources = {
            'PC GPU Session': 'lab/sessions/recent/rle_20251028_08.csv',
            'Phone Benchmarks': 'lab/sessions/archive/mobile/phone_all_benchmarks.csv',
            'Laptop Session 1': 'sessions/laptop/rle_20251030_19.csv',
            'Laptop Session 2': 'sessions/laptop/rle_20251030_20.csv',
        }
        
        # Filter to only existing files
        existing_sources = {}
        for name, path in data_sources.items():
            if Path(path).exists():
                existing_sources[name] = path
        
        file_path = None
        if uploaded_file:
            # Use uploaded file
            file_path = None  # Will use uploaded_file in load_csv
            selected_source = "Uploaded File"
        elif existing_sources:
            selected_source = st.selectbox("Data Source", list(existing_sources.keys()))
            file_path = existing_sources[selected_source]
        else:
            st.info("Upload a CSV file or ensure session files are in the repo")
            selected_source = None
        
        # Device selection
        st.markdown("---")
        st.markdown("### 📡 Device Selection")
        device = st.radio("Monitor Device", ['cpu', 'gpu', 'mobile'], index=0)
        
        # Refresh controls
        st.markdown("---")
        st.markdown("### ⚙️ Display Settings")
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
        smoothing_window = st.slider("Smoothing Window", 1, 20, 5)
        
        # Warning thresholds
        st.markdown("---")
        st.markdown("### 🚨 Alert Thresholds")
        rle_warning = st.slider("RLE Warning", 0.0, 1.0, 0.5, 0.1)
        temp_warning = st.slider("Temp Warning (°C)", 40.0, 100.0, 70.0, 5.0)
    
    # Load data
    if not uploaded_file and not file_path:
        st.warning("Please upload a CSV file or select a data source")
        return
    
    try:
        df = load_csv(file_path=file_path, uploaded_file=uploaded_file)
        if df.empty:
            st.error("No data loaded. Please check your file.")
            return
        
        df_filtered = filter_device(df, device)
        
        if len(df_filtered) == 0:
            st.error(f"No data found for device: {device}")
            return
        
        # Get latest values
        latest = df_filtered.iloc[-1]
        rle_val = latest.get('rle_smoothed', latest.get('rle_raw', 0))
        temp_val = latest.get('temp_c', 0)
        power_val = latest.get('power_w', 0)
        util_val = latest.get('util_pct', 0)
        t_sustain = latest.get('t_sustain_s', 0)
        collapse = latest.get('collapse', 0)
        
        # Top bar: Big RLE display
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            rle_color, color_class, status_text = get_rle_color(rle_val)
            st.markdown(f"""
            <div class='metric-card'>
                <p style='text-align: center; color: #7fdbda; font-size: 24px; margin: 0;'>CURRENT EFFICIENCY</p>
                <p class='big-number {color_class}' style='color: {rle_color};'>{rle_val:.4f}</p>
                <p style='text-align: center; color: #00d4ff; font-size: 20px; margin: 0;'>{status_text}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Main layout
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            st.markdown("### 📊 Live Gauge")
            st.plotly_chart(create_gauge(rle_val, "RLE", 0, 1), use_container_width=True)
            
            st.markdown("### 🔢 System Status")
            st.metric("Temperature", f"{temp_val:.1f}°C", delta=None)
            st.metric("Power", f"{power_val:.1f}W", delta=None)
            st.metric("Utilization", f"{util_val:.1f}%", delta=None)
            st.metric("Sustain Time", f"{t_sustain:.1f}s", delta=None)
            
            # Status indicators
            st.markdown("### ⚠️ System Status")
            led_color = get_rle_color(rle_val)[0]
            collapse_status = "🔴 COLLAPSE DETECTED" if collapse else "🟢 STABLE"
            st.markdown(f"<div style='color: {led_color}; font-size: 18px;'>● {collapse_status}</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 📈 Time Series")
            
            # Create subplots
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=("RLE Efficiency", "Temperature & Power", "Utilization"),
                row_heights=[0.4, 0.3, 0.3]
            )
            
            # RLE trace
            df_filtered['timestamp_dt'] = pd.to_datetime(df_filtered['timestamp'])
            fig.add_trace(
                go.Scatter(
                    x=df_filtered['timestamp_dt'],
                    y=df_filtered.get('rle_smoothed', df_filtered.get('rle_raw', 0)),
                    mode='lines',
                    name='RLE',
                    line=dict(color='#00d4ff', width=2),
                    hovertemplate='RLE: %{y:.4f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Temperature trace
            if 'temp_c' in df_filtered.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_filtered['timestamp_dt'],
                        y=df_filtered['temp_c'],
                        mode='lines',
                        name='Temperature',
                        line=dict(color='#ff4444', width=2),
                        yaxis='y2',
                        hovertemplate='Temp: %{y:.1f}°C<extra></extra>'
                    ),
                    row=2, col=1
                )
            
            # Power trace
            if 'power_w' in df_filtered.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_filtered['timestamp_dt'],
                        y=df_filtered['power_w'],
                        mode='lines',
                        name='Power',
                        line=dict(color='#00ff88', width=2),
                        yaxis='y3',
                        hovertemplate='Power: %{y:.1f}W<extra></extra>'
                    ),
                    row=2, col=1
                )
            
            # Utilization trace
            if 'util_pct' in df_filtered.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_filtered['timestamp_dt'],
                        y=df_filtered['util_pct'],
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
            
            st.plotly_chart(fig, use_container_width=True, theme=None)
        
        with col3:
            st.markdown("### 📉 Statistics")
            
            # Rolling stats
            stats_df = df_filtered[['rle_smoothed', 'temp_c', 'power_w', 'util_pct']].describe()
            st.dataframe(stats_df, use_container_width=True)
            
            st.markdown("### 📊 Distribution")
            
            # RLE distribution
            fig_dist = px.histogram(
                df_filtered,
                x='rle_smoothed' if 'rle_smoothed' in df_filtered.columns else 'rle_raw',
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
            st.plotly_chart(fig_dist, use_container_width=True, theme=None)
            
            # Collapse count
            if 'collapse' in df_filtered.columns:
                collapse_count = df_filtered['collapse'].sum()
                total_samples = len(df_filtered)
                collapse_pct = 100.0 * collapse_count / total_samples
                st.metric("Collapse Events", f"{collapse_count}/{total_samples} ({collapse_pct:.1f}%)")
            
            # Export button
            st.markdown("---")
            csv_export = df_filtered.to_csv(index=False)
            st.download_button(
                label="📥 Export CSV",
                data=csv_export,
                file_name=f"rle_scada_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Bottom panel: Event log
        st.markdown("---")
        st.markdown("### 📋 Event Log")
        
        # Find alerts
        if 'alerts' in df_filtered.columns:
            alert_rows = df_filtered[df_filtered['alerts'].notna() & (df_filtered['alerts'] != '')]
            if len(alert_rows) > 0:
                alert_display = alert_rows[['timestamp', 'alerts', 'rle_smoothed', 'temp_c', 'power_w']].tail(20)
                st.dataframe(alert_display, use_container_width=True)
            else:
                st.info("No alerts in current session")
        
        # Auto-refresh
        if auto_refresh:
            st.rerun()
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Make sure data files are in the correct location")

if __name__ == '__main__':
    main()


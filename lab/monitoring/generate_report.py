"""
Auto-generated session report generator
Creates a summary report when monitoring stops
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

def generate_session_report(csv_path):
    """Generate a session report from a CSV file"""
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return f"Error reading CSV: {e}"
    
    # Calculate stats
    start = pd.to_datetime(df.iloc[0]['timestamp'])
    end = pd.to_datetime(df.iloc[-1]['timestamp'])
    duration = (end - start).total_seconds() / 60
    
    # Report content
    report = f"""
========================================================================
RLE Session Report - AUTO-GENERATED
========================================================================

Session File: {csv_path.name}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

========================================================================
SESSION DURATION
========================================================================
Duration: {duration:.1f} minutes
Samples: {len(df)} ({len(df) / max(duration, 0.1):.1f} samples/minute)

========================================================================
TEMPERATURE ANALYSIS
========================================================================
Max Temperature: {df['temp_c'].max():.1f}°C
Mean Temperature: {df['temp_c'].mean():.1f}°C
Min Temperature: {df['temp_c'].min():.1f}°C

Verdict: """
    
    max_temp = df['temp_c'].max()
    if max_temp < 70:
        report += "✅ EXCELLENT - Well below thermal limits\n"
    elif max_temp < 80:
        report += "✅ GOOD - Within safe operating range\n"
    else:
        report += "⚠️ WARNING - Approaching thermal limits\n"
    
    report += f"""
========================================================================
POWER CONSUMPTION
========================================================================
Max Power: {df['power_w'].max():.2f}W
Mean Power: {df['power_w'].mean():.2f}W
Median Power: {df['power_w'].median():.2f}W

Power Limit Utilization: {df['a_load'].max():.3f}
"""
    
    if df['a_load'].max() > 1.0:
        report += "⚠️ Power limit exceeded (>1.0) - card throttling\n"
    elif df['a_load'].max() > 0.95:
        report += "⚠️ Power limit near - frequent throttling likely\n"
    else:
        report += "✅ Power limit healthy\n"
    
    report += f"""
========================================================================
RLE EFFICIENCY
========================================================================
Max RLE: {df['rle_smoothed'].max():.6f}
Mean RLE: {df['rle_smoothed'].mean():.6f}
Median RLE: {df['rle_smoothed'].median():.6f}

RLE Efficiency Verdict: """
    
    mean_rle = df['rle_smoothed'].mean()
    max_rle = df['rle_smoothed'].max()
    
    if mean_rle > 0.5 and max_rle > 0.8:
        report += "✅ EXCELLENT - System running efficiently\n"
    elif mean_rle > 0.3:
        report += "✅ GOOD - Normal operation\n"
    elif max_rle > 0.8:
        report += "⚠️ MODERATE - Mean RLE low (bimodal load, scene switching)\n"
    else:
        report += "⚠️ POOR - System may be overstressed\n"
    
    report += f"""
========================================================================
COLLAPSE ANALYSIS
========================================================================
Total Collapse Events: {df['collapse'].sum()}
Collapse Rate: {df['collapse'].sum() / len(df) * 100:.1f}%

Collapse Verdict: """
    
    collapse_rate = df['collapse'].sum() / len(df) * 100
    
    if collapse_rate < 5:
        report += f"✅ EXCELLENT - System healthy ({collapse_rate:.1f}%)\n"
    elif collapse_rate < 15:
        report += f"⚠️ MODERATE - Some thermal/power stress ({collapse_rate:.1f}%)\n"
    else:
        report += f"🔴 HIGH - System frequently overstressed ({collapse_rate:.1f}%)\n"
    
    # Detailed collapse analysis if any occurred
    if df['collapse'].sum() > 0:
        collapsed = df[df['collapse'] == 1]
        report += f"""
During Collapse Events:
  - Avg Temperature: {collapsed['temp_c'].mean():.1f}°C
  - Avg Power: {collapsed['power_w'].mean():.2f}W
  - Avg Utilization: {collapsed['util_pct'].mean():.1f}%
"""
    
    report += f"""
========================================================================
GPU UTILIZATION
========================================================================
Max Utilization: {df['util_pct'].max():.1f}%
Mean Utilization: {df['util_pct'].mean():.1f}%
Median Utilization: {df['util_pct'].median():.1f}%

"""
    
    # Thermal sustainability
    report += f"""========================================================================
THERMAL SUSTAINABILITY
========================================================================
Mean t_sustain: {df['t_sustain_s'].mean():.1f}s
Min t_sustain: {df['t_sustain_s'].min():.1f}s
Samples <60s (close to limit): {(df['t_sustain_s'] < 60).sum()}

"""
    
    # Health verdict
    report += f"""========================================================================
OVERALL HEALTH VERDICT
========================================================================
"""
    
    # Determine overall health
    health_issues = []
    
    if max_temp >= 80:
        health_issues.append("thermal limit")
    if df['a_load'].max() > 1.0:
        health_issues.append("power limit exceeded")
    if collapse_rate > 15:
        health_issues.append("frequent efficiency collapse")
    if df['t_sustain_s'].min() < 30:
        health_issues.append("near thermal throttling")
    
    if not health_issues:
        report += "✅ SYSTEM HEALTHY\n\n"
        report += "Your system is running within safe operating limits.\n"
        report += "No thermal or power issues detected.\n"
    else:
        report += f"⚠️ SYSTEM NEEDS ATTENTION\n\n"
        report += "Issues detected:\n"
        for issue in health_issues:
            report += f"  - {issue.capitalize()}\n"
        report += "\nRecommendations:\n"
        if "thermal limit" in " ".join(health_issues) or "thermal" in " ".join(health_issues):
            report += "  - Improve cooling (better airflow, fan curve, undervolt)\n"
        if "power limit" in " ".join(health_issues):
            report += "  - Consider increasing power limit or reducing load\n"
        if "collapse" in " ".join(health_issues):
            report += "  - Check for thermal bottlenecks or throttling\n"
    
    report += f"""
========================================================================
NEXT STEPS
========================================================================
1. Review the detailed analysis: python lab/analyze_session.py {csv_path}
2. Validate system: python kia_validate.py {csv_path}
3. Check other sessions: python lab/scripts/batch_analyze.py lab/sessions/recent/

========================================================================
Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================================================
"""
    
    return report

def save_report(csv_path, report_path=None):
    """Save report to a file"""
    if report_path is None:
        # Save next to CSV with REPORT_ prefix
        csv_file = Path(csv_path)
        report_path = csv_file.parent / f"REPORT_{csv_file.name.replace('.csv', '.txt')}"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(generate_session_report(csv_path))
    
    return report_path


# Cloud Sync Setup Guide

## Quick Setup for GitHub → Streamlit Cloud Live Data

### 1. Create GitHub Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: `RLE Live Monitor`
4. Select scope: **`repo`** (check the box)
5. Click "Generate token"
6. **COPY THE TOKEN** - you won't see it again!

### 2. Set Token in PowerShell

```powershell
# Set for current session
$env:GITHUB_TOKEN='paste_your_token_here'

# Or set permanently (survives reboot)
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'paste_your_token_here', 'User')
```

### 3. Start the Sync

Run this alongside your monitor:

```powershell
cd F:\RLE\lab\monitoring
python push_to_github.py --interval 30
```

### 4. Streamlit Cloud Setup

- Main file: `lab/monitoring/scada_dashboard_cloud.py`
- Branch: `main`
- The dashboard will pull from `live-data` branch automatically

### 5. Verify

Check your repo - you should see a `live-data` branch with `lab/sessions/live/latest.csv` updating every 30 seconds.


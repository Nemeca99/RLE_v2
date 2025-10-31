#!/usr/bin/env python3
"""
Auto-push latest RLE CSV to GitHub for Streamlit Cloud to read
Uses GitHub Contents API to update file without commit spam
Runs as a background daemon alongside the monitor
"""
import time
from pathlib import Path
import base64
import requests
import os

def find_latest_csv():
    """Find the latest CSV in sessions/recent/"""
    sessions_dir = Path(__file__).parent.parent / "sessions" / "recent"
    if not sessions_dir.exists():
        return None
    
    csv_files = list(sessions_dir.glob("rle_*.csv"))
    if not csv_files:
        return None
    
    return max(csv_files, key=lambda p: p.stat().st_mtime)

def push_to_github(csv_path, github_token=None, branch="live-data"):
    """
    Update CSV on GitHub using Contents API (no commit spam)
    Updates the same file without creating commit history
    """
    # Get token from environment or prompt
    token = github_token or os.environ.get('GITHUB_TOKEN')
    if not token:
        print("[GitHub Sync] ERROR: GITHUB_TOKEN not set. Create a GitHub Personal Access Token and set it as environment variable.")
        print("  Set it: $env:GITHUB_TOKEN='your_token_here'  (PowerShell)")
        print("  Get token: https://github.com/settings/tokens (repo scope)")
        return False
    
    # GitHub repo config
    owner = "Nemeca99"
    repo = "RLE"
    file_path = "lab/sessions/live/latest.csv"
    
    try:
        # Read CSV content
        with open(csv_path, 'rb') as f:
            content = f.read()
        content_b64 = base64.b64encode(content).decode('utf-8')
        
        # Check if file exists (get SHA for update)
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get current file SHA (if exists)
        get_resp = requests.get(url, headers=headers, params={'ref': branch}, timeout=5)
        sha = None
        if get_resp.status_code == 200:
            sha = get_resp.json().get('sha')
        
        # Update file
        data = {
            'message': f'Update live RLE data {time.strftime("%Y%m%d_%H%M%S")}',
            'content': content_b64,
            'branch': branch
        }
        if sha:
            data['sha'] = sha  # Include SHA for updates
        
        put_resp = requests.put(url, headers=headers, json=data, timeout=10)
        
        if put_resp.status_code in (200, 201):
            return True
        else:
            print(f"[GitHub Sync] API error: {put_resp.status_code} - {put_resp.text}")
            return False
    except Exception as e:
        print(f"[GitHub Sync] Failed: {e}")
        return False

def main():
    """Watch and push latest CSV every N seconds (configurable)"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Push RLE CSV to GitHub for Streamlit Cloud")
    parser.add_argument("--interval", type=int, default=30, help="Update interval in seconds (default: 30)")
    parser.add_argument("--branch", type=str, default="live-data", help="GitHub branch name (default: live-data)")
    args = parser.parse_args()
    
    last_csv = None
    last_mtime = 0
    
    print(f"[GitHub Sync] Started - pushing latest CSV every {args.interval}s to {args.branch} branch")
    print("[GitHub Sync] Make sure GITHUB_TOKEN is set in environment")
    
    while True:
        latest = find_latest_csv()
        
        if latest and latest.stat().st_mtime > last_mtime:
            print(f"[GitHub Sync] New CSV detected: {latest.name}")
            
            if push_to_github(latest, branch=args.branch):
                print(f"[GitHub Sync] Successfully updated on GitHub")
                last_csv = latest
                last_mtime = latest.stat().st_mtime
            else:
                print(f"[GitHub Sync] Push failed for {latest.name}")
        
        time.sleep(args.interval)

if __name__ == "__main__":
    main()


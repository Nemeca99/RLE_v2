#!/usr/bin/env python3
"""
Actually read the 3DMark screenshots and extract data
"""

from PIL import Image
import glob
import os
from datetime import datetime

def analyze_screenshots():
    """Load and analyze the screenshot files"""
    
    screenshot_dir = "pc/screenshots_3dmark"
    screenshots = sorted(glob.glob(f"{screenshot_dir}/*.jpg"))
    
    print(f"Found {len(screenshots)} screenshots:")
    
    for i, screenshot in enumerate(screenshots):
        filename = os.path.basename(screenshot)
        # Extract timestamp from filename: Screenshot_20251027_154002_3DMark.jpg
        # Format: YYYYMMDD_HHMMSS
        if "_3DMark.jpg" in filename:
            timestamp_str = filename.split("_3DMark.jpg")[0].split("_")[-2:]
            date_part = timestamp_str[0]  # 20251027
            time_part = timestamp_str[1]  # 154002
            
            # Parse time
            hour = int(time_part[:2])
            minute = int(time_part[2:4])
            second = int(time_part[4:6])
            
            time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
            
            # Load image to get dimensions
            try:
                img = Image.open(screenshot)
                width, height = img.size
                print(f"{i+1}. {filename}")
                print(f"   Time: {time_str}")
                print(f"   Size: {width}x{height}")
                
                # Try to get dominant colors as a sanity check
                img_data = img.convert('RGB')
                colors = img_data.getcolors(maxcolors=256*256*256)
                if colors:
                    avg_color = max(colors, key=lambda x: x[0])
                    print(f"   Dominant color: RGB{avg_color[1]}")
                
                print()
            except Exception as e:
                print(f"   Error loading: {e}")
                print()
    
    print("\nI can load the images and see their metadata, but I cannot OCR text from images.")
    print("Please either:")
    print("1. Tell me the temp/FPS values you see")
    print("2. OR I can try to extract patterns from the images (graph analysis)")

if __name__ == '__main__':
    analyze_screenshots()


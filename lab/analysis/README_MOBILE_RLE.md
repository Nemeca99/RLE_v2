# Mobile RLE Data Collection - Working Solution

Since we hit roadblocks with apps and ADB, the **working solution** is to parse 3DMark screenshots manually.

## How It Works

1. **Run 3DMark** on your phone
2. **Take screenshots** showing FPS/temp graphs
3. **Share screenshots** - I'll extract the data
4. **Convert to RLE** using existing pipeline

## What I Need from Screenshots

From the 3DMark performance graph, I need:
- **Temperature** (degrees C)
- **Frame rate** (FPS) 
- **Time** (how long into the test)

I can extract this from the graph visually.

## Files

- `parse_3dmark_screenshots.py` - Creates synthetic data (for testing)
- `mobile_to_rle.py` - Converts sensor CSV to RLE format

## Current Status

Waiting for Wild Life Extreme 20-minute run screenshots.

Once you share them, I'll:
1. Extract temp/FPS data manually
2. Create the sensor CSV
3. Convert to RLE
4. Analyze with `rle_comprehensive_timeline.py`

## Alternative: Manual Entry

If screenshots are unclear, you can manually type the numbers:
- Temp at 5min, 10min, 15min, 20min
- Average FPS for each section

I'll interpolate the timeline.


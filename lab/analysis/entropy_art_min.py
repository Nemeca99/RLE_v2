"""
Entropy Art (Lightweight)

Generates a compact PNG from the latest RLE CSV (or a provided CSV).
Color mapping:
- Hue (0-360): from normalized RLE (rle_norm if available, else rle_smoothed)
- Saturation (0-1): from temp_c (scaled), falls back to 0.5 if missing
- Value/Brightness (0-1): from power_w (scaled), falls back to util_pct/100 or 0.6

Output: sessions/recent/plots/entropy_art_YYYYMMDD_HHMMSS.png

Usage:
  python lab/analysis/entropy_art_min.py               # uses latest recent CSV
  python lab/analysis/entropy_art_min.py path/to/file  # specific CSV
"""

from __future__ import annotations
import csv
import math
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

try:
    from PIL import Image
except Exception as e:
    raise SystemExit("Pillow is required: pip install Pillow")

RECENT_DIR = Path(__file__).resolve().parents[1] / "sessions" / "recent"

def find_latest_csv() -> Path | None:
    if not RECENT_DIR.exists():
        return None
    candidates = sorted(RECENT_DIR.glob("rle_*.csv"))
    return candidates[-1] if candidates else None

def read_rows(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append(r)
    return rows

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def hsv_to_rgb(h: float, s: float, v: float) -> tuple[int,int,int]:
    h = h % 360.0
    c = v * s
    x = c * (1 - abs(((h / 60.0) % 2) - 1))
    m = v - c
    if h < 60:
        r,g,b = c,x,0
    elif h < 120:
        r,g,b = x,c,0
    elif h < 180:
        r,g,b = 0,c,x
    elif h < 240:
        r,g,b = 0,x,c
    elif h < 300:
        r,g,b = x,0,c
    else:
        r,g,b = c,0,x
    return (
        int((r + m) * 255 + 0.5),
        int((g + m) * 255 + 0.5),
        int((b + m) * 255 + 0.5),
    )

def parse_float(row: Dict[str,str], key: str) -> float | None:
    v = row.get(key, "").strip()
    if not v:
        return None
    try:
        return float(v)
    except Exception:
        return None

def map_row_to_color(row: Dict[str,str]) -> tuple[int,int,int]:
    # Prefer rle_norm, else rle_smoothed, else rle_raw
    rle = (
        parse_float(row, "rle_norm")
        or parse_float(row, "rle_smoothed")
        or parse_float(row, "rle_raw")
        or 0.0
    )
    rle_norm = clamp(rle, 0.0, 1.0)  # assume already normalized when using rle_norm
    # Temp → saturation (scale 30-90C)
    temp = parse_float(row, "temp_c")
    if temp is None:
        s = 0.5
    else:
        s = clamp((temp - 30.0) / 60.0, 0.0, 1.0)
    # Power → value (0-150W), fallback util
    power = parse_float(row, "power_w")
    if power is None:
        util = parse_float(row, "util_pct") or 60.0
        v = clamp(util / 100.0, 0.2, 1.0)
    else:
        v = clamp(power / 150.0, 0.2, 1.0)
    # Hue from RLE (0→240deg good-to-bad or vice versa). Use 240→0 so higher RLE = greener/warmer hues.
    h = (1.0 - rle_norm) * 240.0
    return hsv_to_rgb(h, s, v)

def render_image(rows: List[Dict[str,str]], height: int = 80) -> Image.Image:
    if not rows:
        raise ValueError("No rows to render")
    w = len(rows)
    img = Image.new("RGB", (w, height), (0,0,0))
    px = img.load()
    for x, row in enumerate(rows):
        c = map_row_to_color(row)
        for y in range(height):
            px[x, y] = c
    return img

def main():
    import sys
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = find_latest_csv() or None
    if not csv_path or not csv_path.exists():
        raise SystemExit("No CSV found. Provide a path or run the monitor first.")

    rows = read_rows(csv_path)
    # Keep only one device if both present; prioritize cpu for laptop
    device = None
    if any(r.get("device") == "cpu" for r in rows):
        device = "cpu"
    elif any(r.get("device") == "gpu" for r in rows):
        device = "gpu"
    if device:
        rows = [r for r in rows if r.get("device") == device]

    out_dir = RECENT_DIR / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"entropy_art_{device or 'mixed'}_{ts}.png"

    img = render_image(rows)
    img.save(out_path)
    print(f"Saved {out_path}")

if __name__ == "__main__":
    main()



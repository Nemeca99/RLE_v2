#!/usr/bin/env python3
import sys
import os
import pandas as pd
from pathlib import Path


def summarize_file(path: str) -> str:
	if not os.path.exists(path):
		return f"{Path(path).name},0,,,nan,nan,nan,nan,0.0,0.0"
	df = pd.read_csv(path)
	cols = {c.lower(): c for c in df.columns}
	def get(col):
		return df[cols.get(col, col)] if col in cols else (df[col] if col in df.columns else None)
	rle = get('rle_smoothed')
	if rle is None:
		rle = get('rle')
	temp = get('temp_c')
	collapse = get('collapse')
	alerts = get('alerts')
	device = get('device')
	n = len(df)
	rle_min = float(rle.min()) if rle is not None and n else float('nan')
	rle_max = float(rle.max()) if rle is not None and n else float('nan')
	rle_mean = float(rle.mean()) if rle is not None and n else float('nan')
	tmin = float(temp.min()) if temp is not None and n else float('nan')
	tmax = float(temp.max()) if temp is not None and n else float('nan')
	coll_count = int(collapse.sum()) if collapse is not None and n else 0
	coll_rate = (coll_count / n * 100.0) if n else 0.0
	alert_pct = 0.0
	if alerts is not None and n:
		alert_pct = (alerts.fillna('').ne('').sum() / n) * 100.0
	devs = ''
	if device is not None and n:
		devs = ','.join(sorted(map(str, pd.unique(device)))[:3])
	return ','.join([
		Path(path).name,
		str(n),
		devs,
		f"{rle_min:.3f}",
		f"{rle_max:.3f}",
		f"{rle_mean:.3f}",
		f"{tmin:.1f}",
		f"{tmax:.1f}",
		f"{coll_rate:.1f}",
		f"{alert_pct:.1f}",
	])


def main(args: list[str]) -> None:
	if not args:
		print("Usage: summarize_sessions.py <csv> [<csv> ...]")
		return
	print('file,samples,devices,rle_min,rle_max,rle_mean,temp_min_c,temp_max_c,collapse_pct,alerts_pct')
	for p in args:
		print(summarize_file(p))
	# Combined overview
	dfs = []
	for p in args:
		if not os.path.exists(p):
			continue
		df = pd.read_csv(p)
		cols = {c.lower(): c for c in df.columns}
		rle_col = cols.get('rle_smoothed') or cols.get('rle')
		t_col = cols.get('temp_c')
		if rle_col and t_col:
			dfs.append(df[[rle_col, t_col]])
	if dfs:
		all_df = pd.concat(dfs, ignore_index=True)
		rn = [c for c in all_df.columns if 'rle' in c.lower()][0]
		tn = [c for c in all_df.columns if 'temp' in c.lower()][0]
		print('\ncombined:')
		print(f"samples={len(all_df)} rle_mean={all_df[rn].mean():.3f} rle_range={all_df[rn].min():.3f}-{all_df[rn].max():.3f} temp={all_df[tn].min():.1f}-{all_df[tn].max():.1f}°C")


if __name__ == '__main__':
	main(sys.argv[1:])

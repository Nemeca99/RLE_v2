#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

plt.rcParams.update({
	'figure.figsize': (11, 7),
	'axes.grid': True,
	'axes.titlesize': 12,
	'axes.labelsize': 10,
	'legend.fontsize': 9,
})


def load_session(path: str) -> pd.DataFrame:
	df = pd.read_csv(path)
	# Parse timestamp if present
	if 'timestamp' in df.columns:
		df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
		# Drop unparsable rows
		df = df[df['timestamp'].notna()].copy()
		# Derive hour key
		df['hour'] = df['timestamp'].dt.floor('H')
	else:
		# Fallback to index-based time
		df['timestamp'] = pd.RangeIndex(start=0, stop=len(df), step=1)
		df['hour'] = (df.index // 3600)
	return df


def plot_hour(axs, sdf: pd.DataFrame, title: str) -> None:
	rle = 'rle_smoothed' if 'rle_smoothed' in sdf.columns else ('rle' if 'rle' in sdf.columns else None)
	temp = 'temp_c' if 'temp_c' in sdf.columns else None
	pwr = 'power_w' if 'power_w' in sdf.columns else None
	col = 'collapse' if 'collapse' in sdf.columns else None

	t = sdf['timestamp']
	# RLE
	ax = axs[0]
	if rle:
		ax.plot(t, sdf[rle], color='tab:blue', label='RLE')
		ax.set_ylabel('RLE')
		ax.legend(loc='upper right')
	ax.set_title(title)

	# Temperature
	ax = axs[1]
	if temp:
		ax.plot(t, sdf[temp], color='tab:red', label='Temp °C')
		ax.set_ylabel('Temp (°C)')
		ax.legend(loc='upper right')

	# Power
	ax = axs[2]
	if pwr:
		ax.plot(t, sdf[pwr], color='tab:green', label='Power W')
		ax.set_ylabel('Power (W)')
		ax.legend(loc='upper right')

	# Collapse markers
	ax = axs[3]
	if col:
		ax.plot(t, sdf[col], color='tab:purple', label='Collapse (0/1)')
		ax.set_ylabel('Collapse')
		ax.legend(loc='upper right')
	ax.set_xlabel('Time')


def generate_report(paths: list[str], out_pdf: str) -> None:
	with PdfPages(out_pdf) as pdf:
		for p in paths:
			if not os.path.exists(p):
				continue
			df = load_session(p)
			if df.empty:
				continue
			name = Path(p).name
			# Overall page
			fig, axs = plt.subplots(4, 1, sharex=True)
			plot_hour(axs, df, f"{name} — Full Session")
			pdf.savefig(fig, bbox_inches='tight')
			plt.close(fig)
			# Per-hour pages
			for hour_key, sdf in df.groupby('hour'):
				fig, axs = plt.subplots(4, 1, sharex=True)
				plot_hour(axs, sdf, f"{name} — {hour_key}")
				pdf.savefig(fig, bbox_inches='tight')
				plt.close(fig)


def main():
	if len(sys.argv) < 3:
		print("Usage: report_sessions.py <out.pdf> <csv> [<csv> ...]")
		return
	out = sys.argv[1]
	paths = sys.argv[2:]
	generate_report(paths, out)
	print(f"Saved report to {out}")


if __name__ == '__main__':
	main()

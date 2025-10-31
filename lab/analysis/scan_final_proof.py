#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path
from typing import List, Dict

BASE_DIR = Path('Final Proof') / 'Collection' / 'Formula'
OUT_DIR = Path('lab') / 'docs' / 'archive' / 'Final_Proof'
OUT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_MD = OUT_DIR / 'INDEX.md'
SUMMARY_JSON = OUT_DIR / 'sources_summary.json'

TEXT_EXT = {'.txt', '.tex', '.md', '.csv'}  # skip pdf/docx for now

KEYWORDS = [
	# Thermal horizon / RC
	'r c', 'rc', 'thermal', 'heat capacity', 'thermal resistance', 'dT/dt', 'time to limit', 'time-to-limit',
	'T_sustain', 'Tsustain', 't_sustain', 'limit temperature',
	# Load / power
	'A_load', 'load ratio', 'rated power', 'power limit', 'cap', 'TDP', 'P_rated', 'P_rated', 'P/P_rated',
	# Utilization / stability
	'util', 'utilization', 'variance', 'std', 'stability', 'rolling std', 'volatility',
	# Energy/entropy
	'energy balance', 'entropy', 'entropy rate', 'S_gen', 'Sdot', 'P =', 'Wdot', 'Qdot', 'heat',
	# RLE terms
	'RLE', 'E_th', 'E_pw'
]

KEYWORDS_RE = re.compile('|'.join([re.escape(k) for k in KEYWORDS]), re.IGNORECASE)

EXCLUDE_NAMES = {
	# Likely non-technical/fantasy items to avoid pulling snippets from
	'RIS immortality', 'gravitational threeness', 'Ouroboros', 'O_W_L', 'Recursive_Encryption',
	'warp', 'magic', 'poem', 'poetry', 'theology', 'Genesis', 'immortality', 'resurrection',
}


def is_real_technical(filepath: Path) -> bool:
	name = filepath.name.lower()
	# Only scan allowed extensions and non-excluded names
	if filepath.suffix.lower() not in TEXT_EXT:
		return False
	for token in EXCLUDE_NAMES:
		if token.lower() in name:
			return False
	return True


def extract_snippets(text: str, max_snippets: int = 6, window: int = 60) -> List[str]:
	lines = text.splitlines()
	snippets: List[str] = []
	for i, line in enumerate(lines):
		if KEYWORDS_RE.search(line):
			start = max(0, i - 1)
			end = min(len(lines), i + 2)
			snippet = '\n'.join(lines[start:end]).strip()
			if snippet and snippet not in snippets:
				snippets.append(snippet)
				if len(snippets) >= max_snippets:
					break
	return snippets


def scan() -> Dict[str, Dict]:
	results: Dict[str, Dict] = {}
	if not BASE_DIR.exists():
		return results
	for root, _, files in os.walk(BASE_DIR):
		for fn in files:
			fp = Path(root) / fn
			if not is_real_technical(fp):
				continue
			try:
				text = fp.read_text(encoding='utf-8', errors='ignore')
			except Exception:
				continue
			matches = KEYWORDS_RE.findall(text)
			if not matches:
				continue
			snips = extract_snippets(text)
			if not snips:
				continue
			results[str(fp)] = {
				'bytes': fp.stat().st_size,
				'keywords_hit': len(matches),
				'unique_keywords': sorted(set([m.lower() for m in matches]))[:20],
				'snippets': snips,
			}
	return results


def write_outputs(results: Dict[str, Dict]) -> None:
	# Write JSON summary
	with SUMMARY_JSON.open('w', encoding='utf-8') as f:
		json.dump(results, f, indent=2, ensure_ascii=False)
	# Write markdown index
	lines: List[str] = []
	lines.append('# Final Proof: Technical Sources Index')
	lines.append('')
	lines.append('This index was auto-generated from Final Proof/Collection/Formula. Only technical items relevant to RLE were included (thermal horizon, load normalization, utilization/stability, energy/entropy). Non-technical files were skipped.')
	lines.append('')
	for path, info in sorted(results.items(), key=lambda kv: (-kv[1]['keywords_hit'], kv[0])):
		name = Path(path).name
		lines.append(f'## {name}')
		lines.append(f'- Path: `{path}`')
		lines.append(f'- Size: {info.get("bytes",0)} bytes')
		uniq = ', '.join(info.get('unique_keywords', [])[:10])
		if uniq:
			lines.append(f'- Top terms: {uniq}')
		lines.append('')
		lines.append('Sample snippets:')
		lines.append('')
		for sn in info.get('snippets', [])[:4]:
			# fence the snippet
			lines.append('```')
			lines.append(sn)
			lines.append('```')
			lines.append('')
		lines.append('---')
		lines.append('')
	INDEX_MD.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
	results = scan()
	write_outputs(results)
	print(f"Indexed {len(results)} technical sources → {INDEX_MD}")

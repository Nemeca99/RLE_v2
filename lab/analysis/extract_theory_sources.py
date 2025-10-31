#!/usr/bin/env python3
import json
from pathlib import Path
from typing import List, Tuple, Dict

SUMMARY_JSON = Path('lab') / 'docs' / 'archive' / 'Final_Proof' / 'sources_summary.json'
OUT_FILE = Path('lab') / 'docs' / 'RLE_THEORY_APPENDICES.md'


def load_summary() -> Dict[str, Dict]:
	if not SUMMARY_JSON.exists():
		return {}
	return json.loads(SUMMARY_JSON.read_text(encoding='utf-8'))


def write_appendices(items: List[Tuple[str, Dict]]) -> None:
	lines: List[str] = []
	lines.append('# RLE Theory Appendices (Sourced)')
	lines.append('')
	lines.append('Technical sources from Final Proof/Collection/Formula relevant to RLE terms. Non-technical content omitted by the scanner.')
	lines.append('')
	app_idx = 1
	for path, info in items:
		snips = info.get('snippets', [])
		if not snips:
			continue
		name = Path(path).name
		lines.append(f'## Appendix {app_idx}: {name}')
		lines.append(f'Path: `{path}`')
		uniq = ', '.join(info.get('unique_keywords', [])[:10])
		if uniq:
			lines.append(f'Terms: {uniq}')
		lines.append('')
		for sn in snips:
			lines.append('```')
			lines.append(sn)
			lines.append('```')
			lines.append('')
		lines.append('---')
		lines.append('')
		app_idx += 1
	OUT_FILE.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
	summary = load_summary()
	# Sort by number of keyword hits descending
	items: List[Tuple[str, Dict]] = sorted(summary.items(), key=lambda kv: (-kv[1].get('keywords_hit', 0), kv[0]))
	write_appendices(items)
	print(f"Wrote appendices for {sum(1 for _, v in items if v.get('snippets'))} sources → {OUT_FILE}")

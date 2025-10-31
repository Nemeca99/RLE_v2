#!/usr/bin/env python3
"""
Minimal Markdown-to-PDF (text-only) using reportlab.
Usage:
  python lab/scripts/md_to_pdf.py --in lab/docs/FILE.md --out lab/pdf/FILE.pdf
"""
from __future__ import annotations
import argparse
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, width: float, line_height: float = 12):
    import textwrap
    for line in text.splitlines():
        if not line.strip():
            y -= line_height
            continue
        for wline in textwrap.wrap(line, width=int(width/7.2)):
            c.drawString(x, y, wline)
            y -= line_height
    return y


def convert(md_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    txt = md_path.read_text(encoding='utf-8', errors='ignore')
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    margin = 0.75 * inch
    x = margin
    y = height - margin
    c.setTitle(md_path.stem)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(x, y, md_path.stem)
    y -= 18
    c.setFont('Helvetica', 10)
    y = draw_wrapped(c, txt, x, y, width - 2 * margin)
    c.showPage()
    c.save()
    print(f"Wrote {pdf_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='infile', required=True)
    ap.add_argument('--out', dest='outfile', required=True)
    args = ap.parse_args()
    convert(Path(args.infile), Path(args.outfile))


if __name__ == '__main__':
    main()



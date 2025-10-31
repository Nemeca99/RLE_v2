@echo off
setlocal
REM Create tiny demo CSV
mkdir sessions\recent 2>NUL
echo timestamp,device,util_pct,temp_c,power_w> sessions\recent\demo.csv
echo 2025-10-31T00:00:00Z,cpu,40,45,35>> sessions\recent\demo.csv
echo 2025-10-31T00:00:01Z,cpu,60,45.4,55>> sessions\recent\demo.csv
echo 2025-10-31T00:00:02Z,cpu,75,46.0,75>> sessions\recent\demo.csv
echo 2025-10-31T00:00:03Z,cpu,65,46.5,62>> sessions\recent\demo.csv
echo 2025-10-31T00:00:04Z,cpu,55,46.7,48>> sessions\recent\demo.csv

REM Augment (θ-clock default ON)
python lab\monitoring\rle_core.py --in sessions\recent\demo.csv --out sessions\recent\demo_aug.csv

REM Plots
python analysis\theta_plots.py --in sessions\recent\demo_aug.csv --outdir sessions\archive\plots

REM PDFs (already generated in repo). To regenerate with reportlab script if needed:
REM python lab\scripts\md_to_pdf.py --in lab\docs\MINERS_LAW_UNIFIED_v2.md --out lab\pdf\MINERS_LAW_UNIFIED_v2.pdf

echo Done. Outputs in sessions\recent and sessions\archive\plots and lab\pdf.

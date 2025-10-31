import csv
from pathlib import Path

def main():
    p = Path('lab/sessions/recent/out_aug.csv')
    n=0; bad=0; maxdiff=0.0
    n_raw=0; bad_raw=0; maxdiff_raw=0.0
    with p.open('r', encoding='utf-8', errors='ignore', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                rr = float(row['rle_raw'])
                rrm = float(row['rle_raw_ms'])
                fm = float(row['F_mu'])
                diff_raw = abs(rrm - (rr*fm))
                if diff_raw > maxdiff_raw:
                    maxdiff_raw = diff_raw
                if diff_raw > 1e-8:
                    bad_raw += 1
                n_raw += 1

                rs = float(row['rle_smoothed'])
                fm = float(row['F_mu'])
                rms = float(row['rle_smoothed_ms'])
                diff = abs(rms - (rs*fm))
                if diff > maxdiff:
                    maxdiff = diff
                if diff > 1e-5:
                    bad += 1
                n += 1
            except Exception:
                pass
    print(f'raw rows {n_raw} bad {bad_raw} maxdiff {maxdiff_raw:.12f}')
    print(f'smoothed rows {n} bad {bad} maxdiff {maxdiff:.8f}')

if __name__ == '__main__':
    main()



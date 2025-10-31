# Google Drive Upload Checklist - Mobile RLE Dataset

## Already in Drive ✓
- ✅ Publication documents (PUBLICATION_*.md, RLE_*.md)
- ✅ Geekbench JSON files
- ✅ 3DMark screenshots (14 images)
- ✅ Perfetto trace file

## Missing Files to Upload

### 1. Core Mobile RLE Data (CSV files)
- **phone_rle_wildlife.csv** - Wild Life Extreme RLE profile (1000 samples)
- **phone_rle_with_constants.csv** - RLE with computed physics constants
- **phone_all_benchmarks.csv** - Combined timeline (1280 samples)

### 2. Scientific Documentation (Markdown)
- **MOBILE_RLE_VALIDATION.md** - Scientific summary
- **MOBILE_RLE_PHYSICS.md** - Physics interpretation  
- **MOBILE_DEPLOYMENT_COMPLETE.md** - Deployment summary
- **PERFETTO_INFO.md** - Perfetto trace documentation

### 3. Reproducibility Scripts (Python)
- **analyze_mobile_constants.py** - Computes mobile RLE constants
- **combine_all_benchmarks.py** - Fuses 3DMark + Geekbench data
- **mobile_to_rle.py** - Converts raw sensor data to RLE format

## Upload Instructions

1. Navigate to: https://drive.google.com/drive/folders/1iRiVV0HVY8tsAF5zpE2o_xThkXN3KXss
2. Upload the 11 files listed above (3 CSVs, 4 MDs, 4 PYs)
3. Total size: ~500 KB (mostly CSVs)

## Critical Files for Publication

**Must have for reviewers**:
- `phone_rle_wildlife.csv` - The actual data
- `MOBILE_RLE_VALIDATION.md` - Scientific summary
- `MOBILE_RLE_PHYSICS.md` - Constants interpretation
- `analyze_mobile_constants.py` - Reproducibility script

**Nice to have**:
- Combined timeline and other supporting files


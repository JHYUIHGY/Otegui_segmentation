# mCherry‑H2B Nuclear Segmentation Pipeline

Automated, reproducible pipeline for quantifying nuclear morphology and fluorescence in *Arabidopsis* root tips.
The confocal image set is not uploaded due to file size.
Google drive link to the folder used in this project:
https://drive.google.com/drive/folders/1lyRpDqsC8ukQ7ZqJe-EhZeCihV2n9mO5?usp=drive_link

**Highlights**

- **One‑command batch processing** for every `.tif`/`.tiff` under a project folder  
- **Robust adaptive thresholding** that copes with uneven illumination  
- Dual outputs: **SQLite** (per‑nucleus) **and CSV** (per‑image)  
- **Publication‑ready bar plots** with SEM error bars (z‑slice *and* stitched)  
- Modular—drop in deep‑learning models (U‑Net, SAM) without changing downstream code

---

## 1️⃣ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/JHYUIHGY/Otegui_segmentation.git
cd Otegui_segmentation

# 2. Set up a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Organize your data

```
data/
├── istl_control_elongation_zone/
│   ├── mchH2B-istl345_seedling3_z01.tif
│   └── …
├── istl_mutant_meristem_zone/
│   └── *.tiff
└── …
```

### Edit `seg_process_batch.py`

```python
root_dir     = "data"   # top-level folder with images
overwrite_db = True     # wipe old DB on every run
```

### Run the batch processor

```bash
python seg_process_batch.py
```

### Create figures

```bash
python plot_nuclear_metrics_dual.py
open bar_zslices.png     # macOS example
```

---

## 2️⃣ Dependencies

```
numpy
pandas
matplotlib
seaborn
scikit-image
tifffile
scipy
```

Install with:

```bash
pip install -r requirements.txt
```

**Optional**

| Package      | Purpose                             |
|--------------|-------------------------------------|
| `jupyterlab` | Interactive exploration & debugging |
| `ipykernel`  | Use the virtualenv inside notebooks |

---

## 3️⃣ Pipeline Overview

| Stage             | Script / Function                   | What it does                                            |
|------------------|--------------------------------------|---------------------------------------------------------|
| Folder crawl      | `discover_image_folders()`           | Picks all subdirs containing `.tif` or `.tiff` images   |
| Metadata parsing  | `segmentation.parse_filename()`      | Extracts region, genotype, seedling, z-slice, channel   |
| Segmentation      | `segment_and_measure_spots()`        | Adaptive local threshold → morphological cleanup        |
| Measurements      | (same as above)                      | Area, mean intensity, integrated intensity              |
| Storage           | `store_measurements_in_sql()`        | Writes to `results.db` and `image_summary.csv`          |
| QC overlays       | `visualize_segmentation_detailed()`  | Saves labeled overlays in `results/…`                  |
| Plotting          | `plot_nuclear_metrics_dual.py`       | Generates bar plots for z-slices and stitched images    |

---

## 4️⃣ Re-running Cleanly

To reset everything:

```bash
rm image_summary.csv results.db -r results/
python seg_process_batch.py
```

Or just set `overwrite_db = True` and delete `image_summary.csv` manually.

---

## 5️⃣ Extending the Pipeline

| Task                       | Where to modify                           |
|----------------------------|-------------------------------------------|
| Background subtraction     | Add logic at the top of `segment_and_measure_spots()` |
| Use deep learning models   | Replace thresholding block with model inference |
| Add parallel processing    | Wrap `process_folder()` in `ThreadPoolExecutor`     |

---

## 6️⃣ Troubleshooting

| Issue                        | Fix                                           |
|-----------------------------|----------------------------------------------|
| Duplicate rows in CSV       | Delete `image_summary.csv` before re-running |
| KeyError in plotting        | Ensure seaborn ≥ 0.13 and use latest script  |
| Blurry / incomplete masks   | Lower `min_area`, tweak threshold kernel     |

---

## 7️⃣ License & Citation

Released under the MIT License.

If you use this pipeline in a publication, please cite:

> **Phillip Duan** (2025). *Automated Quantification of Nuclear Fluorescence in ISTL Mutant Arabidopsis Roots.*

---

Happy segmenting! 🧬 Pull requests & issues are always welcome.

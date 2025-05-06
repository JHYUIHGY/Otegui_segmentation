"""
Batch version of seg_process.py - processes EVERY folder that
contains .tif/.tiff images underneath `root_dir`.
"""

import os, glob, pathlib, shutil
import numpy as np
from skimage import measure
from segmentation import (
    parse_filename, load_tif, segment_and_measure_spots,
    store_measurements_in_sql, visualize_segmentation_detailed
)

# ─── configure once ────────────────────────────────────────────────────────────
root_dir        = "/Users/hydrablaster/Desktop/Otegui_lab/mCherry_H2B_istl_mutant"
db_path         = "results.db"
output_root     = "results"                           # mirror lives here
overwrite_db    = False                               # set True to wipe DB first
min_area_px     = 5

# ─── utils ─────────────────────────────────────────────────────────────────────
def convert_tiff_to_tif(folder: str):
    for tiff in glob.glob(os.path.join(folder, "*.tiff")):
        tif = tiff[:-5] + ".tif"
        os.rename(tiff, tif)
        print(f"renamed → {pathlib.Path(tif).name}")

def discover_image_folders(top: str):
    """Yield folders that contain at least one .tif/.tiff"""
    for cur, _dirs, files in os.walk(top):
        if any(f.lower().endswith((".tif", ".tiff")) for f in files):
            yield cur

def prepare_output_folder(img_folder: str) -> str:
    rel_path = os.path.relpath(img_folder, root_dir)
    out_dir  = os.path.join(output_root, rel_path)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

# ─── main processing logic ─────────────────────────────────────────────────────
def process_folder(img_folder: str):
    print(f"\n📂  {img_folder}")

    convert_tiff_to_tif(img_folder)
    tif_files = sorted(glob.glob(os.path.join(img_folder, "*.tif")))
    if not tif_files:
        print("    no TIFs – skipped.")
        return

    out_dir = prepare_output_folder(img_folder)

    for fname in tif_files:
        try:
            meta  = parse_filename(fname)                     # full path
            img   = load_tif(fname)
            if img is None or not isinstance(img, np.ndarray):
                print(f"    ✗ failed to load {fname}")
                continue

            spots, mask = segment_and_measure_spots(img, min_area=min_area_px)
            store_measurements_in_sql(db_path, meta, spots)

            labeled = measure.label(mask)
            out_png = os.path.join(out_dir,
                                   pathlib.Path(fname).stem + "_seg.png")
            visualize_segmentation_detailed(img, mask, labeled, spots, out_png)

            print(f"    ✔ {pathlib.Path(fname).name}: {len(spots)} nuclei")

        except Exception as e:
            print(f"    ⚠ error on {fname}: {e}")

# ─── entry‑point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if overwrite_db and os.path.exists(db_path):
        os.remove(db_path)
        print("• previous results.db removed")

    folders = list(discover_image_folders(root_dir))
    print(f"\nFound {len(folders)} folders with images under {root_dir}")

    for f in folders:                  # core, batch processing
        process_folder(f)

    print("\n🎉  All images processed.  Check out →", pathlib.Path(output_root).resolve())

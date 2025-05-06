# This script performs image segmentation and analysis on fluorescence microscopy images.
# It extracts metadata from filenames, loads images, segments spots, measures their properties,
# and stores the results in an SQLite database.
# The script assumes the images are in TIFF format and follow a specific naming convention.
import os
import re
import sqlite3
import numpy as np
import tifffile
import csv
import pathlib

from skimage import filters, measure, morphology, segmentation
from skimage.color import label2rgb
from skimage.io import imsave
import matplotlib.pyplot as plt


def parse_filename(file_path: str) -> dict:
    """
    Works for *both* stacked images (inside `istl_*` folders) and the
    original z-slices stored under `Individual images`.
    
    Examples:
    istl_control_elongation_zone/h2b-istl345_normal_11_seedling3_elong.tif
    control_elongation_zone/h2b-..._seedling12_elong_z16c1.tif
    """
    p = pathlib.Path(file_path)
    fname = p.name.lower()

    # Extract region + genotype from any parent folder that contains them
    parts = [x.lower() for x in p.parts]
    region   = next((r for r in ["meristem", "elongation"] if any(r in s for s in parts)), "unknown")
    genotype = next((g for g in ["control", "mutant"]     if any(g in s for s in parts)), "unknown")

    # Seedling number, z‑slice & channel from the filename
    seedling = re.search(r"seedling(\d+)", fname)
    zslice   = re.search(r"_z(\d+)",        fname)   # matches "_z12"  or "_z12c1"
    channel  = re.search(r"c(\d+)(?=\.tif)", fname)  # c1, c2 …

    return {
        "filename": str(p),
        "region"  : region,
        "genotype": genotype,
        "seedling": int(seedling.group(1)) if seedling else None,
        "zslice"  : int(zslice.group(1))   if zslice   else None,
        "channel" : f"c{channel.group(1)}" if channel  else "unknown",
        # protocol‑fixed info
        "magnification": "40x",
        "fluorophore" : "mCherry-H2B"
    }


def normalize_image(img):
    """Normalize an image to the range 0-255."""
    img = img.astype(np.float32)  # Convert to float for processing
    img = (img - img.min()) / (img.max() - img.min()) * 255  # Stretch contrast, original image was too dim (only 0-170)
    return img.astype(np.uint8)  # Convert back to uint8


def load_tif(fname):
    try:
        img = tifffile.imread(fname)
        if not isinstance(img, np.ndarray):
            raise ValueError(f"File {fname} could not be loaded as an image.")
        
        # print(f"Loaded {fname} with shape: {img.shape}, dtype: {img.dtype}")  

        # Convert RGB to grayscale
        if img.ndim == 3 and img.shape[2] == 3:
            print("Converting RGB image to grayscale.")
            img = np.mean(img, axis=2).astype(np.uint8)

        elif img.ndim > 2:  
            img = img[0, ...]  # Take the first slice if it's a stack

        img = normalize_image(img)
        # print(f"Final shape after processing: {img.shape}, unique values: {np.unique(img)}")
        
        return img

    except Exception as e:
        print(f"Error loading {fname}: {e}")
        return None  


def segment_and_measure_spots(image, min_area=5, closing_radius=3, opening_radius=1) -> tuple[list, np.ndarray]:
    """
    Segments bright 'spots' in a fluorescence image using local thresholding
    and morphological cleanup. Returns a list of region measurements.
    
    Input image : 2D np.array

    Returns list of dict
        Each dict has { 'label': int, 'area': float, 'mean_intensity': float,
                        'integrated_intensity': float, etc. }
    """
    # Adaptive thresholding using Gaussian-weighted local mean
    thresh_val = filters.threshold_local(image, block_size=201, method='gaussian') # adjust block_size base on your need
    mask = image > thresh_val # Create a binary mask where pixels above the threshold are True
    
    # Morphological refinement
    mask = morphology.binary_closing(mask, morphology.disk(closing_radius))
    mask = morphology.binary_opening(mask, morphology.disk(opening_radius))
    # Remove small artifacts and edge touching objects
    mask = morphology.remove_small_objects(mask, min_size=min_area)
    mask = segmentation.clear_border(mask)
    #Label connected components
    labeled = measure.label(mask)
    #Measure properties including intensity
    props = measure.regionprops(labeled, intensity_image=image)
    
    measurements = []
    for p in props: #props is a regionprops object
            measurements.append({
                "label": p.label,
                "area_pixels": p.area,
                "mean_intensity": p.mean_intensity,
                "integrated_intensity": p.mean_intensity * p.area,
            })
    return measurements, mask

SUMMARY_CSV = 'image_summary.csv'

def store_measurements_in_sql(db_path, metadata, measurements):
    """
    'metadata' is a dict with {filename, magnification, zslice, channel}.
    'measurements' is the list of measurement dicts from 'segment_and_measure_spots'.
    """
    
    
    total_area       = sum(m["area_pixels"]         for m in measurements)
    total_intensity  = sum(m["integrated_intensity"] for m in measurements)
    mean_intensity   = total_intensity / total_area if total_area else 0

    # ---- enrich metadata & write to CSV ----
    # ① make sure metadata knows the biological context
    fname_lower = metadata["filename"].lower()
    metadata["region"]   = "meristem"   if "meristem"   in fname_lower else "elongation"
    metadata["genotype"] = "control"    if "control"    in fname_lower else "mutant"

    # ② append one line per Z‑stack
    header = [
        "filename", "region", "genotype", "seedling", "zslice",  
        "total_area", "integrated_intensity", "mean_intensity"
    ]

    row = [
        metadata["filename"], metadata["region"], metadata["genotype"],
        metadata["seedling"], metadata["zslice"],                
        total_area, total_intensity, mean_intensity
    ]

    first_time = not os.path.exists(SUMMARY_CSV)

    with open(SUMMARY_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if first_time:
            writer.writerow(header)
        writer.writerow(row)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Table for individual spots
    c.execute("""
    CREATE TABLE IF NOT EXISTS spots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        magnification TEXT,
        zslice TEXT,
        channel TEXT,
        label INTEGER,
        area_pixels REAL,
        mean_intensity REAL,
        integrated_intensity REAL
    )
    """)

    # Insert each spot
    for m in measurements:
        c.execute("""
        INSERT INTO spots (
            filename, magnification, zslice, channel,
            label, area_pixels, mean_intensity, integrated_intensity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("filename"),
            metadata.get("magnification"),
            metadata.get("zslice"),
            metadata.get("channel"),
            m["label"],
            m["area_pixels"],
            m["mean_intensity"],
            m["integrated_intensity"]
        ))

    # Now also store aggregated in a separate table
    c.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        magnification TEXT,
        zslice TEXT,
        channel TEXT,
        total_area REAL,
        mean_intensity REAL,
        integrated_intensity REAL
    )
    """)

    # Summation
    total_area = sum(m["area_pixels"] for m in measurements)
    total_intensity = sum(m["integrated_intensity"] for m in measurements)
    mean_intensity = total_intensity / total_area if total_area else 0

    # Insert aggregated row
    c.execute("""
    INSERT INTO images (
        filename, magnification, zslice, channel,
        total_area, mean_intensity, integrated_intensity
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        metadata.get("filename"),
        metadata.get("magnification"),
        metadata.get("zslice"),
        metadata.get("channel"),
        total_area,
        mean_intensity,
        total_intensity
    ))

    conn.commit()
    conn.close()

    
def visualize_segmentation_detailed(image, mask, labeled_image=None, measurements=None, output_path=None):
    """
    Create a detailed visualization of segmentation results.
    
    Required:
    - image: Original 2D NumPy array (grayscale)
    - mask: Binary segmentation mask (same dimensions as 'image')
    """

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    num_plots = 2 if labeled_image is None else 3
    fig, axes = plt.subplots(1, num_plots, figsize=(12, 5))
    
    # If only 2 subplots, axes will be a single numpy array of length 2
    # For consistency, handle that by turning 'axes' into a list
    if num_plots == 2:
        axes = list(axes)
    else:
        axes = list(axes)

    # Original image
    axes[0].imshow(image, cmap='gray')
    axes[0].set_title('Original Image')
    axes[0].axis('off')
    
    # Binary mask
    axes[1].imshow(mask, cmap='binary')
    axes[1].set_title('Segmentation Mask')
    axes[1].axis('off')
    
    # If we have a labeled image, show it
    if labeled_image is not None:
        overlay = label2rgb(labeled_image, image=image, bg_label=0)
        axes[2].imshow(overlay)
        axes[2].set_title('Labeled Segments')
        axes[2].axis('off')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=200) # Change dpi on your need
        plt.close()
    else:
        plt.show()
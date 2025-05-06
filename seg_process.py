import glob
import os
import numpy as np
from skimage import measure
from segmentation import parse_filename, load_tif, segment_and_measure_spots, store_measurements_in_sql, visualize_segmentation_detailed

image_folder = "/Users/hydrablaster/Desktop/Otegui_lab/mCherry-H2B_istlmutant/istl_mutant_elongation_zone"
db_path = "results.db"
output_folder = "results"  

def convert_tiff_to_tif(image_folder):
    
    # Convert all .tiff files to .tif

    for tiff_file in glob.glob(os.path.join(image_folder, "*.tiff")):
        tif_file = tiff_file[:-5] + ".tif"
        os.rename(tiff_file, tif_file)
        print(f"Renamed {tiff_file} to {tif_file}")

def process_images():
    
    # # Overwrite the database if it exists
    # if os.path.exists(db_path):
    #     os.remove(db_path)
    # os.makedirs(output_folder, exist_ok=True)
    
    tiff_files = glob.glob(os.path.join(image_folder, "*.tiff"))
    if tiff_files:
        print(f"Found {len(tiff_files)} .tiff files — converting to .tif...")
        convert_tiff_to_tif(image_folder)

    tif_files = glob.glob(os.path.join(image_folder, "*.tif"))
    if not tif_files:
        print("No TIF files found in the specified folder.")
        return

    print(f"Found {len(tif_files)} TIF files.")
    
    for fname in tif_files:
        print(f"Processing: {fname}")
        try:
            meta = parse_filename(os.path.basename(fname))

            img = load_tif(fname)
            
            if img is None or not isinstance(img, np.ndarray):
                print(f"Failed to load image {fname} properly. Skipping.")
                continue

            spots, mask = segment_and_measure_spots(img, min_area=5)

            store_measurements_in_sql(db_path, meta, spots)
        
            # Create a labeled image for visualization
            labeled_image = measure.label(mask)
            
            # Generate visualization
            output_path = os.path.join(output_folder, f"{os.path.basename(fname)[:-4]}_seg.png")
            visualize_segmentation_detailed(img, mask, labeled_image, spots, output_path)

            print(f"{fname} - {len(spots)} spots detected and stored.")

        except Exception as e:
            print(f"Error processing {fname}: {e}")

    print("All images processed successfully!")

if __name__ == "__main__":
    process_images()

"""
Run Full Feature Engineering Pipeline
Author: Nguoi 1 - Core Pipeline & Arrhenius Engine

Cho phep chay bang relative path mac dinh hoac truyen qua tham so:
py run_pipeline.py --data-dir ../../DTS --output-dir ../data
"""

import os
import sys
import time
import argparse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from pipeline import load_master_data, merge_and_enrich_master
from feature_engineering import extract_features

def parse_args():
    parser = argparse.ArgumentParser(description="Chay pipeline xu ly du lieu chuoi lanh")
    parser.add_argument(
        "--data-dir", 
        type=str, 
        default=os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "DTS")),
        help="Thu muc chua 3 file CSV goc (sensor, batches, products)"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default=os.path.abspath(os.path.join(CURRENT_DIR, "..", "data")),
        help="Thu muc luu ket qua features_engineered.csv"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    data_dir = args.data_dir
    output_dir = args.output_dir

    start_time = time.time()
    print("=== BAT DAU PIPELINE XU LY DU LIEU (NGUOI 1) ===")
    print(f"Data directory:   {data_dir}")
    print(f"Output directory: {output_dir}")
    
    os.makedirs(output_dir, exist_ok=True)

    # 1. Load data
    df_sensor, df_batches, df_products = load_master_data(data_dir)
    print(f"Loaded: Sensor={df_sensor.shape}, Batches={df_batches.shape}, Products={df_products.shape}")

    # 2. Merge master
    print("Merging & Enriching Master Data...")
    df_master = merge_and_enrich_master(df_sensor, df_batches, df_products)
    print(f"Master merged shape: {df_master.shape}")

    # 3. Extract features
    print("Extracting features (Arrhenius + Rolling + Lags)...")
    df_features = extract_features(df_master)
    print(f"Features engineered shape: {df_features.shape}")

    # 4. Save output
    output_file = os.path.join(output_dir, "features_engineered.csv")
    print(f"Saving to {output_file}...")
    df_features.to_csv(output_file, index=False)

    elapsed = time.time() - start_time
    print(f"=== HOAN THANH XU LY DU LIEU TRONG {elapsed:.2f} GIAY ===")
    print(f"Tong so dong: {len(df_features)}, Tong so cot dac trung: {len(df_features.columns)}")

if __name__ == "__main__":
    main()

"""
Data Pipeline & Master Ingestion (FR01, FR02 / Process 1.0, 2.0)
Author: Nguoi 1 - Core Pipeline & Arrhenius Engine

Chuc nang:
1. Load 3 file CSV: sensor.csv, batches.csv, products.csv.
2. Validate schema va timestamp.
3. Hieu chuan nhiet do theo Calibration_Offset_Pct:
   Don vi chuan cua cot la % (vi du 0.337 = +0.337%, -1.285 = -1.285%).
   calibrated_temp = Temperature * (1.0 + Calibration_Offset_Pct / 100.0)
4. Merge dong bo thong so dong hoc (Ea, A, Standard Shelf Life) tu products va batches sang sensor.
"""

import os
import pandas as pd
import numpy as np


def load_master_data(data_dir: str):
    """
    Doc 3 file CSV tu thu muc du lieu data_dir.
    """
    batches_path = os.path.join(data_dir, 'batches.csv')
    products_path = os.path.join(data_dir, 'products.csv')
    sensor_path = os.path.join(data_dir, 'sensor.csv')

    if not os.path.exists(batches_path):
        raise FileNotFoundError(f"Khong tim thay batches.csv tai: {batches_path}")
    if not os.path.exists(products_path):
        raise FileNotFoundError(f"Khong tim thay products.csv tai: {products_path}")
    if not os.path.exists(sensor_path):
        raise FileNotFoundError(f"Khong tim thay sensor.csv tai: {sensor_path}")

    print(f"[Pipeline] Loading batches from: {batches_path}")
    df_batches = pd.read_csv(batches_path)

    print(f"[Pipeline] Loading products from: {products_path}")
    df_products = pd.read_csv(products_path)

    print(f"[Pipeline] Loading sensor readings from: {sensor_path}...")
    df_sensor = pd.read_csv(sensor_path)

    # Chuyen doi kieu ngay gio
    df_batches['Manufacture_Date'] = pd.to_datetime(df_batches['Manufacture_Date'])
    df_batches['Label_Expiry_Date'] = pd.to_datetime(df_batches['Label_Expiry_Date'])
    df_batches['Delivered_Date'] = pd.to_datetime(df_batches['Delivered_Date'])
    df_sensor['Timestamp'] = pd.to_datetime(df_sensor['Timestamp'])

    # Validate khong co null o cac cot khoa lien ket
    assert df_batches['Batch_ID'].isnull().sum() == 0, "Null Batch_ID in batches.csv"
    assert df_batches['Product_ID'].isnull().sum() == 0, "Null Product_ID in batches.csv"
    assert df_products['Product_ID'].isnull().sum() == 0, "Null Product_ID in products.csv"
    assert df_sensor['Batch_ID'].isnull().sum() == 0, "Null Batch_ID in sensor.csv"

    # Hieu chuan nhiet do theo dinh nghia % (Percent):
    # Cot mang ten Calibration_Offset_Pct nen 0.5 nghia la 0.5%
    # calibrated_temp = Temperature * (1 + offset_pct / 100)
    df_sensor['calibrated_temp'] = np.round(
        df_sensor['Temperature'] * (1.0 + (df_sensor['Calibration_Offset_Pct'] / 100.0)), 
        3
    )

    return df_sensor, df_batches, df_products


def merge_and_enrich_master(df_sensor: pd.DataFrame,
                            df_batches: pd.DataFrame,
                            df_products: pd.DataFrame) -> pd.DataFrame:
    """
    Ket noi 3 bang du lieu thanh 1 Master DataFrame hoan chinh phuc vu Feature Engineering.
    Log ro rang neu co cot trung lap de tranh mat du lieu am tham.
    """
    # 1. Merge batches voi products
    batches_enriched = df_batches.merge(df_products, on='Product_ID', how='left', suffixes=('', '_prod'))

    # 2. Merge sensor voi batches_enriched
    common_cols = [c for c in batches_enriched.columns if c in df_sensor.columns and c != 'Batch_ID']
    if common_cols:
        print(f"[Pipeline Warning] Cac cot trung giua Sensor va Batches se duoc giu lai tu Sensor: {common_cols}")
        batches_enriched = batches_enriched.drop(columns=common_cols)

    master_df = df_sensor.merge(batches_enriched, on='Batch_ID', how='left')

    # Sap xep theo Batch_ID va Timestamp
    master_df = master_df.sort_values(by=['Batch_ID', 'Timestamp']).reset_index(drop=True)
    return master_df

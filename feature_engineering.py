"""
Feature Engineering Module for Time-Series Sensor Stream
Author: Nguoi 1 - Core Pipeline & Arrhenius Engine

Trich xuat cac dac trung chuoi thoi gian phuc vu:
- Nguoi 3 (Model 1 - Isolation Forest Anomaly Detection)
- Nguoi 4 (Model 2 - LightGBM Temperature Forecasting)
- Nguoi 5 (Model 3 - Quality Risk Score & Dynamic FEFO)

Luu y chong Data Leakage / Bias:
Cac bien lag va diff giu nguyen gia tri NaN o nhung reading dau tien cua moi batch
(thay vi fillna bang chinh gia tri hien tai, gay bias cho model du bao).
Bo sung co `has_full_lag_history` (1 neu du lich su lag 6h, 0 neu thieu).
"""

import pandas as pd
import numpy as np
from arrhenius import calculate_decay_rate_ratio


def extract_features(df_master: pd.DataFrame) -> pd.DataFrame:
    """
    Trich xuat dac trung rolling, lags, delta nhiet do va ti le Arrhenius.
    """
    df = df_master.copy()
    
    # Su dung nhiet do hieu chuan neu co
    temp_col = 'calibrated_temp' if 'calibrated_temp' in df.columns else 'Temperature'

    # 1. Arrhenius Decay Rate Ratio
    print("[FeatureEng] Calculating Arrhenius Decay Rate Ratios...")
    ea = df['Ea_J_per_mol'].values if 'Ea_J_per_mol' in df.columns else 51044.8
    df['Decay_Rate_Ratio'] = np.round(calculate_decay_rate_ratio(df[temp_col].values, ea_j_per_mol=ea), 4)

    # 2. Time-based features
    print("[FeatureEng] Extracting time & temporal features...")
    df['Hour'] = df['Timestamp'].dt.hour
    df['DayOfWeek'] = df['Timestamp'].dt.dayofweek
    df['Reading_Order'] = df.groupby('Batch_ID').cumcount() + 1

    # 3. Groupby Batch de tinh cac lag va rolling (ngan ngua data leak giua cac batch)
    print("[FeatureEng] Computing rolling statistics & lag features per batch...")
    grouped = df.groupby('Batch_ID')

    # Delta nhiet do so voi gio truoc (reading dau tien cua batch = NaN)
    df['temp_diff_1h'] = grouped[temp_col].diff()
    df['humidity_diff_1h'] = grouped['Humidity'].diff()

    # Lag features (t-1, t-2, t-3, t-6) - GIU NGUYEN NaN CHO CAC READING DAU TIEN
    df['temp_lag_1h'] = grouped[temp_col].shift(1)
    df['temp_lag_2h'] = grouped[temp_col].shift(2)
    df['temp_lag_3h'] = grouped[temp_col].shift(3)
    df['temp_lag_6h'] = grouped[temp_col].shift(6)

    # Co danh dau co du lich su 6h de train model du bao
    df['has_full_lag_history'] = (~df['temp_lag_6h'].isna()).astype(int)

    # Rolling window 6h (min_periods=1)
    rolling_6 = grouped[temp_col].rolling(window=6, min_periods=1)
    df['temp_mean_6h'] = rolling_6.mean().reset_index(level=0, drop=True)
    df['temp_std_6h'] = rolling_6.std().fillna(0.0).reset_index(level=0, drop=True)
    df['temp_max_6h'] = rolling_6.max().reset_index(level=0, drop=True)
    df['temp_min_6h'] = rolling_6.min().reset_index(level=0, drop=True)

    # Rolling window 12h
    rolling_12 = grouped[temp_col].rolling(window=12, min_periods=1)
    df['temp_mean_12h'] = rolling_12.mean().reset_index(level=0, drop=True)
    df['temp_std_12h'] = rolling_12.std().fillna(0.0).reset_index(level=0, drop=True)

    # Rolling window 24h
    rolling_24 = grouped[temp_col].rolling(window=24, min_periods=1)
    df['temp_mean_24h'] = rolling_24.mean().reset_index(level=0, drop=True)
    df['temp_std_24h'] = rolling_24.std().fillna(0.0).reset_index(level=0, drop=True)

    # Rolling humidity 6h
    df['humidity_mean_6h'] = grouped['Humidity'].rolling(window=6, min_periods=1).mean().reset_index(level=0, drop=True)
    df['humidity_std_6h'] = grouped['Humidity'].rolling(window=6, min_periods=1).std().fillna(0.0).reset_index(level=0, drop=True)

    # Tinh so ngay thiet hai tich luy do nhiet do cao
    # dt = 1/24 ngay
    dt_days = 1.0 / 24.0
    excess_decay = np.maximum(0.0, df['Decay_Rate_Ratio'] - 1.0) * dt_days
    df['hourly_excess_days_lost'] = excess_decay
    df['cumulative_days_lost'] = df.groupby('Batch_ID')['hourly_excess_days_lost'].cumsum()

    # Dynamic Expiry Date
    df['Dynamic_Expiry_Date'] = df['Label_Expiry_Date'] - pd.to_timedelta(df['cumulative_days_lost'], unit='D')
    
    # Remaining Shelf Life Days tai thoi diem do
    df['Remaining_Days'] = np.round((df['Dynamic_Expiry_Date'] - df['Timestamp']).dt.total_seconds() / 86400.0, 2)

    # He so nguy co vuot nguong tuc thoi (> 8 deg C)
    df['is_temp_exceeded'] = (df[temp_col] > 8.0).astype(int)

    return df

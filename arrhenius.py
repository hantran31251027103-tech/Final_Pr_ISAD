"""
Arrhenius Kinetic Degradation Module (FR03 / Process 3.1)
Author: Nguoi 1 - Core Pipeline & Arrhenius Engine

Ly thuyet dong hoc Arrhenius:
k(T) = A * exp(-Ea / (R * T_kelvin))
k_ref = A * exp(-Ea / (R * T_ref))  # Nhiet do chuan 5 degC = 278.15 K (trung tam 2-8 degC)
Decay_Rate_Ratio = k(T) / k_ref = exp((Ea / R) * (1/T_ref - 1/T_kelvin))

Khi T > T_ref: Decay_Rate_Ratio > 1.0 (thuoc bi phan huy / hao mon nhanh hon binh thuong)
Khi T < T_ref: Decay_Rate_Ratio < 1.0
Khi T vuot nguong mat lanh (> 8 degC): Decay_Rate_Ratio tang vot theo ham mu.
"""

import numpy as np
import pandas as pd
from datetime import timedelta

# Hang so khi ly tuong (J / (mol * K))
R_GAS_CONSTANT = 8.31446261815324

# Nhiet do chuan luu tru chuoi lanh 5 deg C = 278.15 Kelvin (trung diem dai an toan 2-8 deg C)
T_REF_KELVIN = 278.15

# T zero Kelvin
KELVIN_ZERO = 273.15


def calculate_arrhenius_k(temperature_celsius: float | np.ndarray,
                          ea_j_per_mol: float,
                          a_per_s: float) -> float | np.ndarray:
    """
    Tinh hang so toc do phan huy k(T) theo phuong trinh Arrhenius:
    k = A * exp(-Ea / (R * T))
    """
    t_kelvin = np.asarray(temperature_celsius) + KELVIN_ZERO
    t_kelvin = np.maximum(t_kelvin, 1e-5)
    exponent = -ea_j_per_mol / (R_GAS_CONSTANT * t_kelvin)
    exponent = np.clip(exponent, -100.0, 100.0)
    return a_per_s * np.exp(exponent)


def calculate_decay_rate_ratio(temperature_celsius: float | np.ndarray,
                               ea_j_per_mol: float,
                               t_ref_celsius: float = 5.0) -> float | np.ndarray:
    """
    Tinh he so suy giam chat luong Decay_Rate_Ratio = k(T) / k_ref.
    Luu y: Tham so A (tan so va cham) triet tieu khi lay ti le.
    Decay_Rate_Ratio = exp((Ea / R) * (1 / T_ref_K - 1 / T_K))
    """
    t_ref_k = t_ref_celsius + KELVIN_ZERO
    t_k = np.asarray(temperature_celsius) + KELVIN_ZERO
    t_k = np.maximum(t_k, 1e-5)

    factor = (ea_j_per_mol / R_GAS_CONSTANT) * (1.0 / t_ref_k - 1.0 / t_k)
    factor = np.clip(factor, -50.0, 50.0)
    return np.exp(factor)


def compute_cumulative_shelf_life_impact(df_sensor_batch: pd.DataFrame,
                                         standard_shelf_life_days: float,
                                         ea_j_per_mol: float,
                                         label_expiry_date: pd.Timestamp) -> pd.DataFrame:
    """
    Tinh toan tich luy thiet hai tuoi tho thuoc (cumulative shelf life consumption)
    va tinh Han dung dong (Dynamic Expiry Date) theo thoi gian thuc tren 1 lo thuoc.
    """
    df = df_sensor_batch.copy()
    if 'calibrated_temp' in df.columns:
        temp = df['calibrated_temp']
    else:
        temp = df['Temperature']

    # Tinh Decay_Rate_Ratio cho tung moc gio
    ratios = calculate_decay_rate_ratio(temp.values, ea_j_per_mol=ea_j_per_mol)
    df['Decay_Rate_Ratio'] = np.round(ratios, 4)

    # dt = 1 gio = 1.0 / 24 ngay
    dt_days = 1.0 / 24.0
    
    # So ngay tuoi tho tieu hao thuc te o dieu kien do
    effective_days_consumed = df['Decay_Rate_Ratio'] * dt_days
    # So ngay thiet hai vuot muc so voi bao quan chuan 5 degC (neu Ratio > 1 thi > 0)
    excess_days_lost = np.maximum(0.0, df['Decay_Rate_Ratio'] - 1.0) * dt_days

    df['Hourly_Effective_Days_Lost'] = effective_days_consumed
    df['Cumulative_Days_Lost'] = np.cumsum(excess_days_lost)

    # Dynamic Expiry Date: Ngay het han in tren nhan tru di tong so ngay bi thiet hai do mat nhiet
    label_exp = pd.to_datetime(label_expiry_date)
    dynamic_exp_dates = [label_exp - timedelta(days=float(lost)) for lost in df['Cumulative_Days_Lost']]
    df['Dynamic_Expiry_Date'] = pd.to_datetime(dynamic_exp_dates)

    if 'Timestamp' in df.columns:
        current_timestamps = pd.to_datetime(df['Timestamp'])
        remaining_days = [(exp - cur).total_seconds() / 86400.0 
                          for exp, cur in zip(df['Dynamic_Expiry_Date'], current_timestamps)]
        df['Remaining_Shelf_Life_Days'] = np.round(remaining_days, 2)

    return df

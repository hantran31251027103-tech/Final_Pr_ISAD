"""
Unit Test for Arrhenius & Core Pipeline
Author: Nguoi 1
"""
import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from arrhenius import calculate_arrhenius_k, calculate_decay_rate_ratio, compute_cumulative_shelf_life_impact

class TestArrheniusEngine(unittest.TestCase):

    def test_decay_rate_at_reference_temp(self):
        """O nhiet do chuan 5 degC, Decay_Rate_Ratio phai bang chinh xac 1.0"""
        ratio = calculate_decay_rate_ratio(5.0, ea_j_per_mol=51044.8, t_ref_celsius=5.0)
        self.assertAlmostEqual(ratio, 1.0, places=4)

    def test_decay_rate_increases_with_temperature(self):
        """Khi nhiet do tang (> 5 degC), toc do phan huy phai tang > 1.0"""
        ratio_25c = calculate_decay_rate_ratio(25.0, ea_j_per_mol=51044.8, t_ref_celsius=5.0)
        ratio_8c = calculate_decay_rate_ratio(8.0, ea_j_per_mol=51044.8, t_ref_celsius=5.0)
        ratio_2c = calculate_decay_rate_ratio(2.0, ea_j_per_mol=51044.8, t_ref_celsius=5.0)

        self.assertGreater(ratio_25c, ratio_8c)
        self.assertGreater(ratio_8c, 1.0)
        self.assertLess(ratio_2c, 1.0)

    def test_cumulative_shelf_life_loss(self):
        """Kiem tra tinh toan ngay ton that tich luy"""
        df_sample = pd.DataFrame({
            'Timestamp': pd.date_range('2026-01-01', periods=24, freq='h'),
            'calibrated_temp': [15.0] * 24 # bi sot nhiet o 15 do C suot 24h
        })
        label_expiry = pd.Timestamp('2028-01-01')
        df_out = compute_cumulative_shelf_life_impact(df_sample, 730, 51044.8, label_expiry)

        # Do nhiet do 15 degC > 5 degC, phai co thiet hai ngay su dung
        self.assertGreater(df_out['Cumulative_Days_Lost'].iloc[-1], 0.0)
        self.assertLess(df_out['Dynamic_Expiry_Date'].iloc[-1], label_expiry)

if __name__ == '__main__':
    unittest.main()

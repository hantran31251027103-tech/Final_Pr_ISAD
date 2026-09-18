# README & DATA SPECIFICATION (TÀI LIỆU BÀN GIAO DỮ LIỆU)
# Dự án: AI-Powered Pharmaceutical Cold Chain Monitoring & Dynamic FEFO
# Tác giả: Người 1 (Core Pipeline & Arrhenius Engine)
# File dữ liệu xuất: `cold_chain_project/data/features_engineered.csv` (416,688 dòng x 54 cột)

---

## ⚠️ QUY TẮC QUAN TRỌNG VỀ XỬ LÝ DỮ LIỆU KHUYẾT (NaN) CHO NGƯỜI 3 & NGƯỜI 4

Trong chuỗi thời gian, các dòng đầu tiên của mỗi lô hàng sẽ **không có dữ liệu lịch sử**:
- `temp_diff_1h` và `temp_lag_1h`: có **1,500 giá trị NaN** (tương ứng dòng đầu tiên của 1,500 lô hàng).
- `temp_lag_2h`, `3h`, `6h`: có số lượng NaN tăng dần (lên tới **9,000 giá trị NaN** ở 6 dòng đầu của 1,500 lô).
- **CÁC CỘT CHẤT LƯỢNG ARRHENIUS KHÔNG BỊ NaN**: `Decay_Rate_Ratio`, `hourly_excess_days_lost`, `cumulative_days_lost`, `Dynamic_Expiry_Date`, `Remaining_Days` có **0 giá trị NaN (100% sạch)**.

### 🔴 Hướng dẫn chống Crash Model (Scikit-Learn / Isolation Forest / LightGBM):
Scikit-learn **không hỗ trợ dữ liệu NaN**. Do đó, Người 3 và Người 4 **BẮT BUỘC** phải lọc bỏ các dòng thiếu lịch sử trước khi đưa vào hàm `fit()`:

```python
import pandas as pd

# Đọc file dữ liệu bàn giao
df = pd.read_csv("data/features_engineered.csv")

# Cách 1 (Khuyến nghị cho cả Model 1 & Model 2): Lọc theo cờ lịch sử đầy đủ
# Cột has_full_lag_history = 1 đảm bảo cả temp_diff_1h và tất cả lag 1h-6h ĐỀU KHÔNG CÒN NaN (0 null)
df_train = df[df['has_full_lag_history'] == 1].copy()

# Hoặc Cách 2: Dropna trên tập feature cụ thể bạn sử dụng
feature_cols = ['calibrated_temp', 'temp_diff_1h', 'temp_mean_6h', 'temp_std_6h', 'Decay_Rate_Ratio']
df_train = df.dropna(subset=feature_cols).copy()
```

---

## 📌 QUY ƯỚC ĐƠN VỊ CÁC CỘT ĐẶC TRƯNG CHÍNH

1. **`Calibration_Offset_Pct`**: 
   - **Đơn vị**: Phần trăm (`%`).
   - **Ví dụ**: Giá trị `0.337` tương ứng với `+0.337%`. Giá trị `-1.285` tương ứng với `-1.285%`.
   - **Công thức hiệu chuẩn đã áp dụng**: 
     $$\text{calibrated\_temp} = \text{Temperature} \times \left(1 + \frac{\text{Calibration\_Offset\_Pct}}{100}\right)$$
   - Khuyến nghị: Các mô hình ML và phân tích nên ưu tiên dùng `calibrated_temp` thay cho `Temperature` thô.

2. **`has_full_lag_history`**:
   - **Giá trị**: `1` nếu dòng hiện tại đã có đủ ít nhất 6 giờ lịch sử đo (nghĩa là cả `temp_diff_1h`, `temp_lag_1h`, `2h`, `3h`, `6h` đều hợp lệ, không bị NaN).
   - **Giá trị**: `0` ở 6 dòng đầu của mỗi lô. Có tổng cộng **407,688 dòng đạt chuẩn (= 1)** và 9,000 dòng khởi đầu (= 0).

3. **`Decay_Rate_Ratio`**:
   - **Ý nghĩa**: Tỷ lệ hao mòn chất lượng theo động học Arrhenius so với nhiệt độ bảo quản chuẩn $5^\circ\text{C}$ ($278.15\text{K}$).
   - Tại $5^\circ\text{C}$, tỷ lệ $= 1.0$. Nhiệt độ càng cao, tỷ lệ càng tăng theo hàm số mũ.

---

## 👥 CHI TIẾT BÀN GIAO CHO TỪNG THÀNH VIÊN

### 1. Dành cho Người 3 (Model 1 - Isolation Forest Anomaly Detection):
- **Features đầu vào**: `['calibrated_temp', 'temp_diff_1h', 'temp_mean_6h', 'temp_std_6h', 'Decay_Rate_Ratio', 'humidity_mean_6h']`
- **Nhãn đánh giá**: `Anomaly_Flag` (gồm 8,528 mẫu sự cố = 1, chiếm 2.05%).
- **Lưu ý**: Lọc `df[df['has_full_lag_history'] == 1]` trước khi `model.fit()`.
- **Đầu ra cần nộp**: Model `model1_isolation_forest.pkl` và hàm trả về `Anomaly_Score` (0 - 100).

### 2. Dành cho Người 4 (Model 2 - Forecaster & FEFO Engine):
- **Features đầu vào**: Các lag `temp_lag_1h` đến `temp_lag_6h`, `Hour`, `DayOfWeek`, `Lead_Time_Days`, `Shipment_Mode`.
- **Cột Người 4 cần tự tạo khi huấn luyện**:
  - `temp_target_3h = grouped['calibrated_temp'].shift(-3)`
  - `temp_target_6h = grouped['calibrated_temp'].shift(-6)`
  - `Excursion_Probability`: Xác suất $P(\text{temp\_pred} > 8.0^\circ\text{C})$.
- **Module xuất kho**: Lập trình `fefo_engine.py` tính `Quality_Risk_Score` và đảo thứ tự xuất kho `Dynamic_FEFO_Rank`.

### 3. Dành cho Người 5 (Streamlit App Developer):
- Dữ liệu đã có sẵn: `Batch_ID`, `Product_Name`, `Timestamp`, `calibrated_temp`, `Decay_Rate_Ratio`, `cumulative_days_lost`, `Dynamic_Expiry_Date`, `Remaining_Days`.
- Dựng giao diện 3 tab: QA Manager, Warehouse Staff và Driver Alert.

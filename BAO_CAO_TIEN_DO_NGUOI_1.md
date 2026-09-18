# BÁO CÁO KẾT QUẢ NHIỆM VỤ NGƯỜI 1: CORE PIPELINE & ARRHENIUS ENGINE

## 1. Đánh giá tập dữ liệu mới tăng cường (`C:\Users\Admin\Downloads\HTTT\DTS`)

So sánh với dataset ban đầu, tập dữ liệu mới **đã được tăng cường cực kỳ lý tưởng cho bài toán Machine Learning**:

| Tiêu chí | Dataset cũ | Dataset mới tăng cường (`DTS`) | Nhận xét |
| :--- | :--- | :--- | :--- |
| **Số lô hàng (`batches.csv`)** | 30 lô | **1,500 lô** (Tăng gấp 50 lần) | Rất phong phú các lộ trình, loại xe, nhà sản xuất |
| **Số bản ghi cảm biến (`sensor.csv`)** | 7,200 dòng | **416,688 dòng** | Chuỗi thời gian đủ lớn cho cả mô hình Deep Learning/ML |
| **Số lượng nhãn sự cố (`Anomaly_Flag=1`)** | 10 mẫu (0.14%) | **8,528 mẫu (2.05%)** | **Cực tốt**: Tỷ lệ dị thường 2% là chuẩn thực tế, đủ data cho Người 3 train/test |
| **Số dòng khuyết thiếu (Nulls)** | 0 | **0** | Dữ liệu sạch, sẵn sàng sử dụng ngay |
| **Độ lệch cảm biến** | Có | **Có (`Calibration_Offset_Pct`)** | Đã được xử lý hiệu chuẩn nhiệt độ |

---

## 2. Kết quả công việc đã hoàn thành của Người 1

Toàn bộ code và dữ liệu đã được khởi tạo và kiểm thử thành công tại thư mục:  
`C:\Users\Admin\.gemini\antigravity\scratch\cold_chain_project\`

### Các module đã hoàn thiện:
1. **[arrhenius.py](file:///C:/Users/Admin/.gemini/antigravity/scratch/cold_chain_project/src/arrhenius.py)**:
   * Hiện thực hóa công thức động học phân hủy hóa sinh Arrhenius.
   * Tính `Decay_Rate_Ratio = k(T) / k_ref`.
   * Tính tích lũy tổn thất tuổi thọ (`Cumulative_Days_Lost`) và cập nhật Hạn dùng động (`Dynamic_Expiry_Date`).
   * Đã chạy kiểm thử tự động đạt 100%: `test_arrhenius.py` (OK).

2. **[pipeline.py](file:///C:/Users/Admin/.gemini/antigravity/scratch/cold_chain_project/src/pipeline.py)**:
   * Đọc, validate kiểu dữ liệu, chuẩn hóa thời gian và merge 3 bảng dữ liệu lớn.
   * Tự động bù trừ sai số cảm biến: `calibrated_temp = Temperature * (1 + offset)`.

3. **[feature_engineering.py](file:///C:/Users/Admin/.gemini/antigravity/scratch/cold_chain_project/src/feature_engineering.py)**:
   * Trích xuất các đặc trưng thời gian: `Hour`, `DayOfWeek`, `Reading_Order`.
   * Trích xuất các biến trễ: `temp_lag_1h`, `temp_lag_2h`, `temp_lag_3h`, `temp_lag_6h`.
   * Trích xuất các đặc trưng biến động cửa sổ trượt: rolling mean, std, min, max (6h, 12h, 24h).

4. **[run_pipeline.py](file:///C:/Users/Admin/.gemini/antigravity/scratch/cold_chain_project/src/run_pipeline.py)**:
   * Chạy batch xử lý thành công toàn bộ **416,688 dòng dữ liệu** chỉ trong **14.65 giây**.

---

## 3. Sản phẩm bàn giao cho các thành viên khác

### 📦 File dữ liệu bàn giao:
* Đường dẫn file: `cold_chain_project/data/features_engineered.csv`
* Dung lượng: **~222 MB** (416,688 dòng × 53 cột đặc trưng).
* File tài liệu hướng dẫn sử dụng: [DATA_SPEC.md](file:///C:/Users/Admin/.gemini/antigravity/scratch/cold_chain_project/DATA_SPEC.md).

### 🎯 Phân phối cho các bạn trong nhóm:
* **Người 3 (Model 1 - Anomaly Detection):** Dùng các cột `calibrated_temp`, `temp_diff_1h`, `temp_mean_6h`, `temp_std_6h` để train Isolation Forest. Đối chiếu với cột `Anomaly_Flag` (có 8,528 mẫu = 1) để tính Precision/Recall.
* **Người 4 (Model 2 - Forecaster & FEFO):** Dùng các cột `temp_lag_1h` đến `temp_lag_6h` để train mô hình LightGBM dự báo trước 3–6 giờ, sau đó kết hợp với `Decay_Rate_Ratio` để tính điểm rủi ro.
* **Người 5 (App Developer):** Đã có sẵn các cột `Decay_Rate_Ratio`, `Dynamic_Expiry_Date`, `Remaining_Days` để dựng biểu đồ trực quan cho QA Manager ngay lập tức.

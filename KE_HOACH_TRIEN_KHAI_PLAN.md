# Kế hoạch Triển khai: AI-Powered Pharmaceutical Cold Chain IS

## Mô tả dự án

Hệ thống giám sát chuỗi lạnh dược phẩm tích hợp **Arrhenius kinetic decay**, **3 AI model** (Anomaly Detection, Temperature Forecasting, Quality Risk Scoring) và **Dynamic FEFO** tự động sắp xếp lại thứ tự xuất kho. Mục tiêu cuối là một **sản phẩm hoàn chỉnh** gồm backend pipeline, web dashboard (QA Manager + Warehouse Staff) và mobile alert (Driver).

---

## 🔍 Phân tích dữ liệu: Dataset có dùng được không?

### Tổng quan 3 file CSV

| File | Rows | Cols | Null | Ghi chú |
|------|------|------|------|---------|
| `sensor.csv` | 7,200 | 9 | **0** | 30 batch × 240 readings (mỗi giờ trong ~10 ngày) |
| `batches.csv` | 30 | 15 | **0** | 30 lô hàng ARV/HRDT, 10 quốc gia |
| `products.csv` | 63 | 8 | **0** | 63 sản phẩm, Ea/A parameters đầy đủ |

### ✅ Điểm mạnh của dataset

| Khía cạnh | Kết quả | Đánh giá |
|-----------|---------|----------|
| **Join** | 3 bảng merge hoàn hảo 7,200 rows | ✅ Tốt |
| **Null values** | 0 null trên toàn bộ 3 file | ✅ Tốt |
| **Nhiệt độ** | Mean 5.08°C, trong khoảng 2–8°C quy chuẩn | ✅ |
| **Arrhenius params** | `Ea_J_per_mol` và `A_per_s` có sẵn cho 63 sp | ✅ |
| **Calibration** | `Calibration_Offset_Pct` có trong sensor | ✅ |
| **Schema** | `Anomaly_Flag` có sẵn → ground truth cho Model 1 | ✅ |
| **Lead time** | Min 11 ngày, Max 194 ngày → đủ phong phú | ✅ |

### ⚠️ Hạn chế cần xử lý

| Vấn đề | Chi tiết | Giải pháp |
|--------|---------|-----------|
| **Dataset nhỏ** | 30 batch × 240 readings = 7,200 rows | Dùng sliding window + feature engineering để tăng số mẫu |
| **Anomaly rất hiếm** | Chỉ **10/7200** rows có `Anomaly_Flag=1` (0.14%) | Class imbalance → dùng SMOTE hoặc weighted loss |
| **Ea/A đồng nhất** | Tất cả 63 sản phẩm có Ea=51,044.8 và A=6.442 giống hệt nhau | Dataset mô phỏng → Arrhenius vẫn tính được, nhưng không phân biệt per-compound |
| **Chỉ 1 loại cảm biến** | `Sensor_Type` toàn bộ là `Cold-chain Temp/Humidity Logger` | OK cho prototype |
| **Readings cố định** | Mỗi batch đúng 240 readings, không miss | Thực tế sẽ có gaps → cần xử lý interpolation |
| **Không có GPS** | Đúng như đã ghi trong scope (out-of-scope) | Chấp nhận được |

> [!IMPORTANT]
> **Kết luận**: Dataset **đủ dùng cho prototype** nhưng cần augmentation để train Model 1 (anomaly detection). Model 2 (forecasting) và Model 3 (risk scoring) hoàn toàn train được với data hiện tại.

---

## Kiến trúc tổng thể

```
sensor.csv ──┐
batches.csv ─┼─► [Feature Engineering] ─► [Arrhenius Engine] ─► Decay_Rate_Ratio
products.csv ┘                                                    Dynamic_Expiry
                                            ↓
                              ┌─────────────────────────────┐
                              │  Model 1: Anomaly Detection  │ → Anomaly_Score
                              │  Model 2: Temp Forecasting   │ → Excursion_Prob
                              │  Model 3: Quality Risk Score │ → Risk_Score 0–100
                              └─────────────────────────────┘
                                            ↓
                              [Dynamic FEFO Engine] → Dispatch Rank
                                            ↓
                    ┌────────────────────────────────────────┐
                    │ Web Dashboard (React/Streamlit)        │
                    │ Mobile Alert (Flutter / Telegram bot)  │
                    └────────────────────────────────────────┘
```

---

## Kế hoạch triển khai theo giai đoạn

### Phase 0 — Setup & EDA (Ngày 1)

- [ ] Tạo project structure Python
- [ ] Load và verify 3 CSV, kiểm tra join
- [ ] Vẽ EDA: phân phối nhiệt độ, humidity, anomaly distribution
- [ ] Verify công thức Arrhenius trên 1 batch thủ công

---

### Phase 1 — Feature Engineering & Arrhenius Engine (Ngày 2–3)

#### Mục tiêu
Tính `Decay_Rate_Ratio` và `Dynamic_Expiry` cho mỗi reading theo Arrhenius.

#### Công thức
```
k(T) = A × exp(−Ea / (R × T_kelvin))
k_ref = A × exp(−Ea / (R × T_ref))   # T_ref = 278.15K = 5°C (nhiệt độ chuẩn chuỗi lạnh)
Decay_Rate_Ratio = k(T) / k_ref
```

#### Features cần tạo (per reading, sliding window 6h, 12h, 24h)

| Feature | Mô tả |
|---------|-------|
| `temp_mean_6h` | Rolling mean nhiệt độ 6 giờ |
| `temp_std_6h` | Rolling std nhiệt độ 6 giờ |
| `temp_max_6h` | Rolling max nhiệt độ 6 giờ |
| `humidity_mean_6h` | Rolling mean độ ẩm 6 giờ |
| `temp_diff` | Độ chênh lệch so với reading trước |
| `temp_rate_of_change` | Tốc độ thay đổi nhiệt độ (°C/h) |
| `Decay_Rate_Ratio` | Từ Arrhenius (số thực) |
| `cumulative_decay` | Tích luỹ suy giảm theo thời gian |
| `Dynamic_Expiry_Days` | Hạn dùng còn lại ước tính |
| `time_elapsed_pct` | % thời gian vận chuyển đã qua |
| `Lead_Time_Days` | Từ batches.csv |
| `Shipment_Mode_encoded` | Air=0, Truck=1, Air Charter=2, Ocean=3 |
| `calibrated_temp` | `Temperature × (1 + Calibration_Offset_Pct)` |

**Output**: `features_engineered.csv` (~7,200 rows × ~25 features)

---

### Phase 2 — Model 1: Anomaly Detection (Ngày 4–5)

#### Bài toán
Phát hiện anomaly ngầm trong chuỗi nhiệt độ trước khi vượt ngưỡng.

#### Chiến lược xử lý class imbalance (10 positive / 7190 negative)

**Option A — Unsupervised (không cần label):**
- **Isolation Forest** trên các features rolling window
- **LSTM Autoencoder** học pattern bình thường, reconstruction error = Anomaly_Score
- → Dùng `Anomaly_Flag` chỉ để evaluate, không để train

**Option B — Supervised với augmentation:**
- **SMOTE** / **ADASYN** để tăng minority class
- **XGBoost** với `scale_pos_weight = 7190/10 = 719`
- → Dùng khi muốn precision/recall rõ ràng

> [!TIP]
> **Khuyến nghị**: Dùng **LSTM Autoencoder** (unsupervised). Vì data thực tế sẽ không có đủ label, approach này scalable hơn. Threshold được calibrate bằng 10 anomaly samples hiện có.

**Output**: `Anomaly_Score` (0–1) cho mỗi reading

---

### Phase 3 — Model 2: Temperature Forecasting (Ngày 6–7)

#### Bài toán
Dự báo nhiệt độ 3–6 giờ tiếp theo, tính `Excursion_Probability` (xác suất vượt 8°C).

#### Phương pháp

| Model | Ưu | Nhược |
|-------|-----|-------|
| **LSTM** (nhiều-bước) | Tốt với chuỗi thời gian, handle patterns | Cần nhiều data hơn |
| **LightGBM** trên lagged features | Nhanh, ít overffit, interpretable | Không tốt với long-range dependency |
| **Prophet** (Meta) | Tự động seasonality | Không predict nhiều steps tốt |

> [!TIP]
> **Khuyến nghị**: **LightGBM** với lagged features (t-1 đến t-12) + rolling stats. Với 7,200 rows chia 30 batch, tránh LSTM sẽ overfit. Thêm `MultiOutputRegressor` để predict 3h và 6h cùng lúc.

**Input features**: Nhiệt độ lag 1–12h, humidity lag, rolling stats, batch metadata  
**Output**: `temp_pred_3h`, `temp_pred_6h`, `Excursion_Probability`

---

### Phase 4 — Model 3: Quality Risk Scoring (Ngày 8–9)

#### Bài toán
Tổng hợp 4 yếu tố thành `Quality_Risk_Score` (0–100).

#### Thiết kế

Không train supervised (không có ground truth risk score), thay vào đó dùng **rule-based aggregation + normalization**:

```python
# Công thức tổng hợp có trọng số
Risk_Score = (
    w1 × normalize(Decay_Rate_Ratio)     # 40%
  + w2 × Anomaly_Score                   # 25%
  + w3 × Excursion_Probability           # 20%
  + w4 × normalize(humidity_variance)    # 15%
) × 100

# FEFO rank: batch có Risk_Score cao nhất → xuất trước
Dynamic_FEFO_Rank = rank(desc(Risk_Score), partition_by=batch)
```

Trọng số `w1–w4` có thể tune bởi QA Manager qua dashboard.

---

### Phase 5 — Evaluation & Validation (Ngày 10)

| Model | Metric |
|-------|--------|
| Model 1 (Anomaly) | Precision, Recall, F1 vs `Anomaly_Flag`; AUC-ROC |
| Model 2 (Forecast) | MAE, RMSE trên hold-out 20% cuối mỗi batch |
| Model 3 (Risk) | Correlation với `Decay_Rate_Ratio`; manual review 5 batches |
| Arrhenius Engine | Verify `Dynamic_Expiry` với hand calculation trên 3 batches |

---

### Phase 6 — Dashboard & Presentation Layer (Ngày 11–14)

#### Tech stack khuyến nghị (lightweight cho prototype)

| Component | Technology | Lý do |
|-----------|-----------|-------|
| Backend / API | **FastAPI** (Python) | Dễ dùng, tích hợp tốt với ML code |
| Dashboard | **Streamlit** hoặc React | Streamlit nhanh hơn cho prototype |
| DB | **SQLite** (prototype) / PostgreSQL | Không cần setup phức tạp |
| Mobile alert | **Telegram Bot** (thay Flutter) | Nhanh hơn, đủ để demo |
| Caching | In-memory (dict) hoặc Redis | Demo không cần Redis |

#### Trang dashboard

1. **QA Manager View**: Bảng FEFO rank theo Risk_Score, biểu đồ Decay_Rate_Ratio theo thời gian, Dynamic Expiry cập nhật real-time
2. **Warehouse Staff View**: Danh sách xuất kho đơn giản theo thứ tự priority, màu đỏ/vàng/xanh
3. **Alert Panel**: Log các anomaly và predictive alert

---

### Phase 7 — Deployment & Demo (Ngày 15)

- Package toàn bộ thành Docker Compose (tùy chọn)
- Chạy demo simulation: feed sensor.csv vào hệ thống theo thời gian thực (replay data)
- Demo sequence: 1 batch có anomaly → hệ thống detect → alert → FEFO re-rank

---

## Cấu trúc thư mục dự án

```
cold_chain_is/
├── data/
│   ├── raw/               # sensor.csv, batches.csv, products.csv
│   └── processed/         # features_engineered.csv, predictions.csv
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_arrhenius.ipynb
│   ├── 03_model1_anomaly.ipynb
│   ├── 04_model2_forecast.ipynb
│   └── 05_model3_risk.ipynb
├── src/
│   ├── arrhenius.py       # Arrhenius engine
│   ├── feature_engineering.py
│   ├── model1_anomaly.py
│   ├── model2_forecast.py
│   ├── model3_risk.py
│   └── fefo_engine.py
├── app/
│   ├── main.py            # FastAPI backend
│   └── dashboard.py       # Streamlit dashboard
├── models/                # Saved model files (.pkl, .h5)
├── requirements.txt
└── README.md
```

---

## Libraries cần cài

```txt
pandas numpy scikit-learn
lightgbm xgboost
tensorflow keras          # cho LSTM Autoencoder (Model 1, optional)
imbalanced-learn          # SMOTE
streamlit fastapi uvicorn
plotly matplotlib seaborn
scipy                     # cho Arrhenius tính toán
python-telegram-bot       # cho mobile alert (tùy chọn)
joblib
```

---

## Open Questions

> [!IMPORTANT]
> **Q1**: Sản phẩm cuối trình bày dưới dạng nào? Jupyter notebook demo, Streamlit web app hay có backend FastAPI riêng?

> [!IMPORTANT]
> **Q2**: Có cần deploy lên cloud (Heroku, GCP, AWS) hay chỉ chạy local để demo?

> [!WARNING]
> **Q3 — Class imbalance nghiêm trọng**: Chỉ có 10 anomaly samples. Muốn dùng supervised learning cho Model 1 thì cần **augment data** (synthetic anomaly injection). Có đồng ý inject synthetic anomalies vào dataset không?

> [!NOTE]
> **Q4**: Ea và A trong `products.csv` hoàn toàn đồng nhất (51,044.8 và 6.442 cho tất cả 63 sản phẩm). Đây là dataset mô phỏng — Arrhenius vẫn chạy tốt nhưng không phân biệt được per-compound. Thầy/cô có biết điều này chưa?

---

## Verification Plan

### Automated
```bash
py -m pytest tests/
```
- Test Arrhenius: verify `Decay_Rate_Ratio > 1` khi `T > T_ref`
- Test FEFO: batch risk cao nhất phải có rank = 1
- Test join integrity: 7,200 rows sau merge

### Manual
- Demo replay sensor.csv theo thứ tự thời gian
- QA Manager xem bảng Risk Score trên dashboard
- Inject 1 batch có nhiệt độ tăng cao → kiểm tra alert kích hoạt

---

## Tóm tắt timeline

| Ngày | Phase | Deliverable |
|------|-------|-------------|
| 1 | EDA + Setup | Project structure, EDA report |
| 2–3 | Feature Eng + Arrhenius | `features_engineered.csv`, Decay_Rate_Ratio |
| 4–5 | Model 1 | LSTM Autoencoder / Isolation Forest, Anomaly_Score |
| 6–7 | Model 2 | LightGBM Forecaster, Excursion_Probability |
| 8–9 | Model 3 | Risk Scoring engine, Dynamic_FEFO_Rank |
| 10 | Evaluation | Metrics report |
| 11–14 | Dashboard | Streamlit app hoàn chỉnh |
| 15 | Demo | End-to-end demo, README |

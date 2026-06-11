# Phiên làm việc: 09/06/2026 (Session 02 - Hardening và giảm rủi ro vận hành)

## 1. Mục tiêu
- Kiểm tra lại sản phẩm cuối và các log đang làm để tìm bất thường trong model.
- Giảm tối đa rủi ro bỏ sót tấn công trong runtime, đặc biệt với mẫu low-and-slow (slow port scan).
- Nâng cấp API và UI để có dữ liệu chẩn đoán rõ ràng, có thể theo dõi sức khỏe hệ thống theo thời gian thực.

## 2. Vấn đề phát hiện trong phiên
- Nguy cơ deployment không an toàn do scaler có thể bị thiếu và pipeline vẫn chạy theo đường fallback.
- Ngưỡng Autoencoder cũ (`0.008481`) không phù hợp domain Snort runtime, gây lệch gate Stage-1.
- Đầu ra confidence từng bị cao bất thường do nhánh Normal gate gán xác suất cứng 1.0.
- Kịch bản `slow_port_scan` ban đầu dễ bị dự đoán về Normal nếu chỉ dựa vào classifier chính.
- Frontend thiếu dashboard cho dataset/input và diagnostics để theo dõi độ tin cậy của kết quả.

## 3. Hạng mục đã thực hiện
### 3.1 Hardening artifacts và preprocess
- Bước preprocess đã bắt buộc scaler (`strict=True`) để tránh chạy unscaled mà không cảnh báo.
- Pipeline backend thêm kiểm tra đủ artifact trước khi infer: checkpoint, autoencoder, feature columns, scaler.

### 3.2 Calibration và smoke guard
- Thêm runtime calibration cho ngưỡng Autoencoder trên luồng normal giả lập.
- Thêm smoke test gate sau calibration để chặn deployment nếu quality gate thất bại.
- Lưu diagnostics smoke trong response để đối chiếu khi vận hành.

### 3.3 Slow-attack features và simulator
- Mở rộng feature engineering với các biến meta:
  - `flow_inter_arrival_sec`
  - `src_conn_count_60s`
  - `src_unique_dst_ports_60s`
  - `slow_attack_score`
  - `slow_attack_flag`
- Nâng cấp simulator `slow_port_scan` theo hướng có tính liên tục (ổn định src/dst, quét nhiều cổng theo thời gian) để mô phỏng sát thực tế hơn.

### 3.4 Inference và diagnostics
- Predict hai tầng trả thêm diagnostics Stage-1 và trường pattern:
  - `stage1_is_attack`, `stage1_mse`, `autoencoder_threshold`
  - `traffic_pattern_label` với nhãn `SlowAttackSuspected` khi có slow flag.
- Bỏ logic confidence cứng 1.0 ở nhánh Normal, thay bằng confidence mềm theo tỷ lệ MSE/threshold để giảm hiện tượng overconfident.

### 3.5 Risk override để giảm false-normal
- Thêm cơ chế `risk override` trong backend:
  - Kích hoạt khi gate Normal quá cao hoặc slow ratio cao.
  - Promote có kiểm soát các vector slow-scan đang bị gán Normal sang hướng Probe.
  - Chuẩn hóa lại xác suất và tính lại top-k sau override.
- Thêm các chỉ số mới vào summary:
  - `effective_attack_ratio`
  - `risk_override_applied`
  - `risk_override_count`
- Thêm các tham số tuning trong `inference_config.json`:
  - `stage1_normal_gate_override_threshold`
  - `slow_attack_ratio_override_threshold`
  - `slow_attack_score_override_threshold`
  - `slow_attack_override_min_rows`

### 3.6 API và UI
- API `/api/detect` trả thêm:
  - `diagnostics`, `input_profile`, `dataset_profile`, `sample_features`
- Cải tiến cách lấy sample predictions để ưu tiên các dòng có `slow_attack_flag=1`, giúp UI dễ quan sát hơn.
- Frontend bổ sung phần Dataset/Input và Diagnostics:
  - Bảng so sánh feature input vs dataset
  - Chart diagnostics
  - KPI mới: effective attack ratio, risk override
  - Toast cảnh báo khi risk override kích hoạt

## 4. Kết quả kiểm thử và xác nhận
- Đã kiểm tra lỗi cho các file backend/inference/frontend liên quan: không còn syntax error.
- Smoke test API sau hardening:

### 4.1 Scenario normal (V5)
- `predicted_counts`: `{"Normal":159,"Probe":1}`
- `mean_confidence`: `0.6621`
- `high_confidence_share`: `0.00625`
- `stage1_normal_gate_rate`: `0.99375`
- `risk_override_applied`: `false`

### 4.2 Scenario slow_port_scan (V5)
- `predicted_counts`: `{"Normal":58,"Probe":162}`
- `mean_confidence`: `0.5445`
- `high_confidence_share`: `0.0`
- `slow_attack_count`: `162`
- `slow_attack_ratio`: `0.7364`
- `effective_attack_ratio`: `0.7364`
- `risk_override_applied`: `true`
- `risk_override_count`: `162`

### 4.3 Kiểm tra mẫu hiển thị
- Sample trả về có đầy đủ hai nhóm:
  - `SlowAttackSuspected`
  - `StandardTrafficPattern`
- Có cột `risk_override` để biết dòng nào đã được promote bằng heuristic.

## 5. Tổng kết
- Đã nâng cấp hệ thống từ mức cảnh báo thụ động lên mức có cơ chế can thiệp chủ động khi phát hiện rủi ro bỏ sót slow attack.
- Rủi ro "confidence cao bất thường" đã giảm rõ rệt sau khi đổi confidence mềm cho nhánh Normal.
- Rủi ro "all-Normal" ở slow scan đã được khắc phục thực tế trong smoke test bằng risk override có điều kiện.

## 6. Công việc tiếp theo để hoàn thiện
- Tinh chỉnh thêm ngưỡng override theo dữ liệu replay thực tế (pcap/log sản xuất) để giảm false positive.
- Bổ sung bộ test tự động cho regressions (normal, mixed, slow_port_scan) trong CI local.
- Nếu có dữ liệu gán nhãn thực tế, retrain Stage-1/Stage-2 theo domain Snort để giảm phụ thuộc vào heuristic override.

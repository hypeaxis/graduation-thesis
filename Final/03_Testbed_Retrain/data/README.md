# GĐ3 — Dữ liệu Testbed (KHÔNG kèm trong gói)

Dữ liệu GĐ3 là **tự thu** trên Testbed WSL2 (không tải sẵn ở đâu). Xem [../HUONG_DAN_THU_DU_LIEU.md](../HUONG_DAN_THU_DU_LIEU.md).

Cấu trúc mong đợi sau khi thu:
```
03_Testbed_Retrain/data/
├── raw_pcap/                 # pcap thu được (bỏ qua git)
├── flows/                    # *_Flow.csv do CICFlowMeter xuất
└── Combined_V8_5.csv         # dataset gộp dùng train V8.5 (~62MB) — sinh bởi build_dataset_v8_5.py
```
Có thể bổ sung mẫu Web Attack từ CIC (mapper: `retrain/v8/v8.5_Combined/cic_webattack_mapper.py`).

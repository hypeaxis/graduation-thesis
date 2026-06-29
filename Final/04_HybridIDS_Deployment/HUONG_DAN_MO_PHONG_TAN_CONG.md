# GĐ4 — HƯỚNG DẪN MÔ PHỎNG TẤN CÔNG (cho demo End-to-End)

Sinh tấn công để kiểm chứng tính bổ sung hai tầng Snort (dấu hiệu) + FT-Transformer (ML).

## Chuẩn bị
- Victim: DVWA + SSH (trong WSL2/lab). Attacker: máy có nmap/hydra/slowhttptest.
- Snort 3 chạy chế độ IDS với ruleset (xem `snort/`).

## Kịch bản
| Tấn công | Lệnh mẫu | Kỳ vọng phát hiện |
|---|---|---|
| PortScan | `nmap -sS -p- <victim>` | Snort (luật scan) + luật đếm cổng |
| Brute Force SSH | `hydra -L users.txt -P rockyou.txt ssh://<victim>` | ML (flow pattern) |
| DoS slow | `slowhttptest -c 1000 -H -u http://<victim>` | **Chỉ ML** (Snort dễ bỏ sót) |
| XSS payload ngắn | inject `<script>` vào DVWA | **Chỉ Snort** (ML khó vì flow giống Benign) |
| DoS flood | `hping3 --flood -S -p 80 <victim>` | Snort + ML |

## Quan sát
- Bảng cảnh báo trên dashboard phân loại đúng lớp tấn công.
- Đối chiếu: tấn công nào chỉ một tầng bắt được → minh hoạ giá trị của kiến trúc lai ghép.
- Luật hậu xử lý đếm cổng (kiểu dấu hiệu) nâng **PortScan F1 từ 0,000 → 0,996** mà không train lại mô hình.

> ⚠️ Chỉ thực hiện trong **mạng lab cô lập** mà bạn sở hữu/được phép. Không nhắm vào hệ thống ngoài.

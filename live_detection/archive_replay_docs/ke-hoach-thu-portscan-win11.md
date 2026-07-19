# Kế hoạch thu PortScan đúng cách (capture trên Win11 host)

## 0. Vì sao phải làm thế này

Victim `192.168.0.103` là **máy Windows 11 host**; WSL Ubuntu victim nằm sau nó (mirrored/NAT).
Khi PortScan quét các **cổng đóng**, **Windows host tự trả RST** — gói này **không vào namespace
WSL** nên `tcpdump -i eth0` trong WSL **không bắt được** → chỉ còn flow tới vài cổng mở
(80/21/22/443) → 9 cổng / 153 flow.

(Brute/Web/DoS đánh cổng **mở** = service trong WSL → được bridge vào WSL → tcpdump bắt đủ →
nên các loại đó vẫn OK. Chỉ PortScan bị.)

→ **Giải pháp: bắt gói NGAY TRÊN Win11 host** (nơi gói scan thực sự nằm), rồi mới trích đặc trưng.

---

## 1. Chuẩn bị trên Win11 host (làm 1 lần)

1. **Xác định card mạng + IP LAN:** mở `cmd` → `ipconfig` → tìm card Wi-Fi/Ethernet có
   `IPv4 Address . . . : 192.168.0.103`. Nhớ tên card (vd "Wi-Fi").
2. **Firewall:** đã xác nhận cổng đóng trả RST (tốt). Nếu muốn chắc, mở PowerShell admin:
   `netsh advfirewall set allprofiles state off` (bật lại sau khi thu nếu cần).
3. **Cài Wireshark** (khuyến nghị — bắt + lưu pcap dễ nhất): tải tại https://www.wireshark.org/
   → khi cài **nhớ tích cài Npcap**. (Wireshark kèm `editcap.exe` để convert nếu cần.)
4. **CICFlowMeter:** vẫn chạy trong WSL như cũ (đọc pcap offline) — không cần cài thêm trên Win.

---

## 2. PHƯƠNG ÁN A — Wireshark (khuyến nghị)

### B1. Bật capture trên Win11 host
1. Mở **Wireshark** (chuột phải → Run as administrator).
2. Ở ô **capture filter** (trên cùng) gõ: `host 192.168.0.106`
   *(chỉ bắt traffic với attacker → file gọn, sạch).*
3. Nháy đúp vào card mạng LAN (vd "Wi-Fi", card có IP `.103`) → capture bắt đầu (🦈 xanh).

### B2. Chạy scan từ Attacker (WSL Win10)
```bash
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
python3 auto_attack_v4.py --target 192.168.0.103 --type portscan
```
> v4 đã có `-Pn` (scan luôn chạy dù ping bị chặn) + 12 vòng × 4 dải cổng.
> KHÔNG cần `tcpdump` trong WSL victim cho phiên PortScan này.

### B3. Dừng + lưu pcap (trên Win11)
1. Wireshark → nút **⏹ đỏ** để Stop.
2. **File → Save As** → đặt tên `portscan_host.pcap` → ô **Save as type** chọn
   **"Wireshark/tcpdump/... - pcap"** (KHÔNG chọn pcapng) → Save.
   *(Nếu chỉ lưu được pcapng: File → Export Specified Packets → Save as type = pcap.)*
3. Lưu vào nơi WSL đọc được, vd `C:\Users\<ban>\portscan_host.pcap`.

---

## 3. PHƯƠNG ÁN B — pktmon (không cần cài Wireshark)

PowerShell **admin** trên Win11:
```powershell
pktmon filter remove
pktmon filter add PScan -i 192.168.0.106
pktmon start --capture --pkt-size 0 --file C:\portscan.etl
#   >>> sang Attacker chạy lệnh scan ở B2, đợi xong <<<
pktmon stop
pktmon etl2pcap C:\portscan.etl --out C:\portscan.pcapng
```
Convert pcapng → pcap (CICFlowMeter đọc pcap chuẩn hơn) — cần `editcap` của Wireshark:
```powershell
& "C:\Program Files\Wireshark\editcap.exe" -F pcap C:\portscan.pcapng C:\portscan_host.pcap
```
> Nếu không có editcap, thử cho CICFlowMeter đọc thẳng `.pcapng`; lỗi thì mới cần convert.

---

## 4. Trích đặc trưng bằng CICFlowMeter (trong WSL — đọc pcap host offline)

```bash
# Copy pcap host vào WSL (attacker hoặc victim đều được)
cp /mnt/c/Users/<ban>/portscan_host.pcap ~/

# Chạy CICFlowMeter offline trên file đó
cd <thư_mục_CICFlowMeter>
sudo ./cfm ~/portscan_host.pcap ~/cicflow/
# → sinh ~/cicflow/portscan_host.pcap_Flow.csv
```

---

## 5. Kiểm tra ĐẠT (quan trọng nhất)

```bash
# số cổng đích duy nhất — phải LỚN (hàng trăm+), không phải 9
tail -n +2 ~/cicflow/portscan_host.pcap_Flow.csv | cut -d',' -f5 | sort -u | wc -l
# số flow
wc -l ~/cicflow/portscan_host.pcap_Flow.csv
```
- ✅ **> 100 cổng duy nhất** + hàng nghìn flow → THÀNH CÔNG, port-spread đã về.
- ❌ Vẫn ít cổng → kiểm tra: bắt đúng card LAN `.103` chưa? scan có chạy lúc capture đang bật
  không? (capture phải bật TRƯỚC khi scan).

---

## 6. Đưa vào hệ thống + push

```bash
cp ~/cicflow/portscan_host.pcap_Flow.csv \
   ~/Graduation-Thesis/Replay_Live_Detection/data/portscan_only.pcap_Flow.csv

cd ~/Graduation-Thesis
git add Replay_Live_Detection/data/portscan_only.pcap_Flow.csv
git commit -m "PortScan thu lại trên Win11 host (đủ port-spread)"
git push origin main
```

## 7. Bật rule + validate (sau khi data đạt)

Trong [replay_config.json](replay_config.json) đổi `portscan_rule` → `"enabled": true`.
Báo mình để chạy lại đánh giá: kỳ vọng **PortScan F1 ↑** và **macro-F1 ~0.96**.

---

## 8. Phương án dự phòng (nếu host capture vẫn không ra port-spread)

Inject **PortScan từ CIC-IDS-2017** vào corpus (đúng tinh thần domain-adaptation của đồ án):
testbed WSL khó bắt portscan sạch → dùng mẫu PortScan chuẩn để lớp này có đủ dữ liệu. Báo mình
sẽ hỗ trợ map đặc trưng + trộn.

---

## Checklist
- [ ] `ipconfig` xác định card LAN `.103`
- [ ] Wireshark (hoặc pktmon) bật capture với filter `host 192.168.0.106`
- [ ] Attacker chạy `auto_attack_v4.py --type portscan` lúc capture đang bật
- [ ] Lưu `portscan_host.pcap` (định dạng pcap)
- [ ] CICFlowMeter offline → `portscan_host.pcap_Flow.csv`
- [ ] Kiểm tra **> 100 cổng duy nhất**
- [ ] Copy vào `data/` → push → bật rule → validate

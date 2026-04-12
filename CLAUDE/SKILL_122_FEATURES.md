```markdown
# Cẩm nang Kỹ năng: 122 Đặc trưng NSL-KDD (SKILL_122_FEATURES.md)

**Mục đích:** Chi tiết mapping 122 đặc trưng mà parser log Snort cần trích xuất, bao gồm cách tính toán từ packet metadata và alert records.

## 1. Tổng quan cấu trúc Features

| Nhóm | Số lượng | Index | Mô tả |
|------|----------|-------|-------|
| Basic Features | 9 | 1-9 | Trích xuất trực tiếp từ header TCP/IP |
| Content Features | 13 | 10-22 | Phân tích payload (chỉ áp dụng HTTP/FTP/Telnet) |
| Time-based Traffic Features | 9 | 23-31 | Thống kê trong cửa sổ 2 giây |
| Host-based Traffic Features | 10 | 32-41 | Thống kê theo destination host |
| Derived Features (One-hot) | ~81 | 42-122 | Encoding cho protocol_type, service, flag |

---

## 2. Basic Features (1-9)

| # | Tên | Kiểu | Cách tính từ Packet |
|---|-----|------|---------------------|
| 1 | `duration` | continuous | `connection_end_time - connection_start_time` (giây) |
| 2 | `protocol_type` | symbolic | Từ IP header: `ip->protocol` (6=TCP, 17=UDP, 1=ICMP) |
| 3 | `service` | symbolic | Mapping từ `dst_port`: 80→http, 21→ftp, 22→ssh, 23→telnet... |
| 4 | `flag` | symbolic | Trạng thái kết nối TCP: SF, S0, REJ, RSTO, SH, RSTR... |
| 5 | `src_bytes` | continuous | Tổng bytes gửi từ source (không tính header) |
| 6 | `dst_bytes` | continuous | Tổng bytes gửi từ destination |
| 7 | `land` | binary | 1 nếu `src_ip == dst_ip && src_port == dst_port` |
| 8 | `wrong_fragment` | continuous | Số fragments bị lỗi (IP fragmentation) |
| 9 | `urgent` | continuous | Số packets có cờ URG (TCP urgent pointer) |

### Chi tiết Flag (Feature #4)
| Flag | Ý nghĩa | Cách nhận biết |
|------|---------|----------------|
| SF | Normal (SYN→SYN-ACK→ACK→FIN) | Connection hoàn thành bình thường |
| S0 | Connection attempt, no reply | Chỉ thấy SYN, không có SYN-ACK |
| REJ | Connection rejected | Nhận RST sau SYN |
| RSTO | Connection reset by originator | Source gửi RST |
| RSTOS0 | RST sau SYN, source reset | Tương tự RSTO nhưng sớm hơn |
| SH | SYN-FIN (half open) | Bất thường, có thể là scan |
| S1 | Connection established, not terminated | SYN-ACK nhưng không FIN |
| S2 | Established, originator tries close | FIN từ source |
| S3 | Established, responder tries close | FIN từ destination |
| OTH | Other/Midstream | Không match pattern nào |

---

## 3. Content Features (10-22)

| # | Tên | Kiểu | Cách tính |
|---|-----|------|-----------|
| 10 | `hot` | continuous | Số "hot" indicators (truy cập file nhạy cảm) |
| 11 | `num_failed_logins` | continuous | Đếm "Login incorrect" trong payload |
| 12 | `logged_in` | binary | 1 nếu login thành công |
| 13 | `num_compromised` | continuous | Số điều kiện "compromised" |
| 14 | `root_shell` | binary | 1 nếu có root shell |
| 15 | `su_attempted` | binary | 1 nếu có lệnh `su` |
| 16 | `num_root` | continuous | Số lần truy cập root |
| 17 | `num_file_creations` | continuous | Số file được tạo |
| 18 | `num_shells` | continuous | Số shell prompts |
| 19 | `num_access_files` | continuous | Số lần truy cập access control files |
| 20 | `num_outbound_cmds` | continuous | Số outbound commands trong FTP session |
| 21 | `is_host_login` | binary | 1 nếu login thuộc "host" list |
| 22 | `is_guest_login` | binary | 1 nếu guest login |

**Lưu ý:** Các features này cần Deep Packet Inspection (DPI). Đối với encrypted traffic (HTTPS, SSH), đặt giá trị = 0.

---

## 4. Time-based Traffic Features (23-31)

Thống kê trong **cửa sổ 2 giây** (sliding window), đếm các connections có cùng `dst_ip` hoặc `service`.

| # | Tên | Công thức |
|---|-----|-----------|
| 23 | `count` | Số connections đến cùng dst_ip trong 2s |
| 24 | `srv_count` | Số connections đến cùng service trong 2s |
| 25 | `serror_rate` | `SYN_error_count / count` |
| 26 | `srv_serror_rate` | `SYN_error_count / srv_count` |
| 27 | `rerror_rate` | `REJ_error_count / count` |
| 28 | `srv_rerror_rate` | `REJ_error_count / srv_count` |
| 29 | `same_srv_rate` | `same_service_count / count` |
| 30 | `diff_srv_rate` | `different_service_count / count` |
| 31 | `srv_diff_host_rate` | `different_host_count / srv_count` |

---

## 5. Host-based Traffic Features (32-41)

Thống kê theo **100 connections gần nhất** đến cùng `dst_ip`.

| # | Tên | Công thức |
|---|-----|-----------|
| 32 | `dst_host_count` | Số connections đến dst_ip trong 100 connections gần nhất |
| 33 | `dst_host_srv_count` | Số connections cùng dst_port trong 100 |
| 34 | `dst_host_same_srv_rate` | `same_service / dst_host_count` |
| 35 | `dst_host_diff_srv_rate` | `diff_service / dst_host_count` |
| 36 | `dst_host_same_src_port_rate` | `same_src_port / dst_host_count` |
| 37 | `dst_host_srv_diff_host_rate` | `diff_src_ip / dst_host_srv_count` |
| 38 | `dst_host_serror_rate` | `SYN_errors / dst_host_count` |
| 39 | `dst_host_srv_serror_rate` | `SYN_errors / dst_host_srv_count` |
| 40 | `dst_host_rerror_rate` | `REJ_errors / dst_host_count` |
| 41 | `dst_host_srv_rerror_rate` | `REJ_errors / dst_host_srv_count` |

---

## 6. Derived Features - One-hot Encoding (42-122)

### 6.1 Protocol Type (3 values → 3 features)
| Index | Feature Name | Condition |
|-------|--------------|-----------|
| 42 | `protocol_type_icmp` | protocol == ICMP |
| 43 | `protocol_type_tcp` | protocol == TCP |
| 44 | `protocol_type_udp` | protocol == UDP |

### 6.2 Service (66 values → 66 features)
| Index | Feature Name |
|-------|--------------|
| 45 | `service_aol` |
| 46 | `service_auth` |
| 47 | `service_bgp` |
| 48 | `service_courier` |
| 49 | `service_csnet_ns` |
| 50 | `service_ctf` |
| 51 | `service_daytime` |
| 52 | `service_discard` |
| 53 | `service_domain` |
| 54 | `service_domain_u` |
| 55 | `service_echo` |
| 56 | `service_eco_i` |
| 57 | `service_ecr_i` |
| 58 | `service_efs` |
| 59 | `service_exec` |
| 60 | `service_finger` |
| 61 | `service_ftp` |
| 62 | `service_ftp_data` |
| 63 | `service_gopher` |
| 64 | `service_harvest` |
| 65 | `service_hostnames` |
| 66 | `service_http` |
| 67 | `service_http_2784` |
| 68 | `service_http_443` |
| 69 | `service_http_8001` |
| 70 | `service_imap4` |
| 71 | `service_IRC` |
| 72 | `service_iso_tsap` |
| 73 | `service_klogin` |
| 74 | `service_kshell` |
| 75 | `service_ldap` |
| 76 | `service_link` |
| 77 | `service_login` |
| 78 | `service_mtp` |
| 79 | `service_name` |
| 80 | `service_netbios_dgm` |
| 81 | `service_netbios_ns` |
| 82 | `service_netbios_ssn` |
| 83 | `service_netstat` |
| 84 | `service_nnsp` |
| 85 | `service_nntp` |
| 86 | `service_ntp_u` |
| 87 | `service_other` |
| 88 | `service_pm_dump` |
| 89 | `service_pop_2` |
| 90 | `service_pop_3` |
| 91 | `service_printer` |
| 92 | `service_private` |
| 93 | `service_red_i` |
| 94 | `service_remote_job` |
| 95 | `service_rje` |
| 96 | `service_shell` |
| 97 | `service_smtp` |
| 98 | `service_sql_net` |
| 99 | `service_ssh` |
| 100 | `service_sunrpc` |
| 101 | `service_supdup` |
| 102 | `service_systat` |
| 103 | `service_telnet` |
| 104 | `service_tftp_u` |
| 105 | `service_tim_i` |
| 106 | `service_time` |
| 107 | `service_urh_i` |
| 108 | `service_urp_i` |
| 109 | `service_uucp` |
| 110 | `service_uucp_path` |
| 111 | `service_vmnet` |
| 112 | `service_whois` |
| 113 | `service_X11` |
| 114 | `service_Z39_50` |

### 6.3 Flag (11 values → 11 features)
| Index | Feature Name |
|-------|--------------|
| 115 | `flag_OTH` |
| 116 | `flag_REJ` |
| 117 | `flag_RSTO` |
| 118 | `flag_RSTOS0` |
| 119 | `flag_RSTR` |
| 120 | `flag_S0` |
| 121 | `flag_S1` |
| 122 | `flag_S2` |
| 123 | `flag_S3` |
| 124 | `flag_SF` |
| 125 | `flag_SH` |

**Lưu ý:** Tổng thực tế là 125 features sau one-hot. Tùy vào cách xử lý (bỏ 1 cột reference để tránh multicollinearity), có thể giảm về 122. Kiểm tra lại với model training code để đảm bảo khớp.

---

## 7. Bảng Port → Service Mapping

```c
const char* port_to_service(uint16_t port, uint8_t protocol) {
    if (protocol == IPPROTO_ICMP) {
        return "eco_i";  // hoặc "ecr_i" tùy loại ICMP
    }
    switch (port) {
        case 20: return "ftp_data";
        case 21: return "ftp";
        case 22: return "ssh";
        case 23: return "telnet";
        case 25: return "smtp";
        case 53: return "domain";
        case 79: return "finger";
        case 80: return "http";
        case 110: return "pop_3";
        case 143: return "imap4";
        case 443: return "http_443";
        case 513: return "login";
        case 514: return "shell";
        // ... thêm các port khác
        default: return "other";
    }
}
```

---

## 8. Normalization

Trước khi đưa vào model, cần normalize các features continuous về [0, 1]:

```
normalized_value = (value - min) / (max - min)
```

Giá trị `min`, `max` được tính từ tập NSL-KDD training set và lưu cố định. Ví dụ:
- `duration`: min=0, max=58329
- `src_bytes`: min=0, max=1379963888
- `dst_bytes`: min=0, max=1309937401

**Quan trọng:** Cùng bộ min/max phải được dùng khi training model và khi inference real-time.
```

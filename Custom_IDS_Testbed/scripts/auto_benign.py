import time
import requests
import random
import threading

# CẤU HÌNH ĐỊA CHỈ IP CỦA LAPTOP 2 (MÁY NẠN NHÂN)
VICTIM_IP = "192.168.1.2"  # IP thực tế của Laptop 2
ENDPOINTS = ["/", "/DVWA/", "/DVWA/login.php", "/DVWA/index.php"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

def simulate_normal_browsing():
    print(f"[*] Đang bắt đầu tạo Benign Traffic tới Máy Nạn Nhân...")
    while True:
        try:
            # Chọn ngẫu nhiên User-Agent để mô phỏng người dùng thật
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            
            # Chọn ngẫu nhiên Endpoint để tránh lỗi 404 liên tục
            url = f"http://{VICTIM_IP}{random.choice(ENDPOINTS)}"
            
            # Gửi request GET bình thường
            response = requests.get(url, headers=headers, timeout=5)
            print(f"[Benign] Truy cập {url} - Status: {response.status_code}")
            
            # Đợi một chút rồi truy cập trang khác hoặc submit form ngẫu nhiên
            time.sleep(random.uniform(2, 5))
            
            # Mô phỏng Login thất bại bình thường (sai pass do gõ nhầm)
            login_url = f"http://{VICTIM_IP}/DVWA/login.php"
            data = {'username': 'admin', 'password': 'wrongpassword', 'Login': 'Login'}
            requests.post(login_url, headers=headers, data=data, timeout=5)
            print("[Benign] Mô phỏng thao tác login...")
            
            # Nghỉ ngơi giữa các vòng lặp (như người dùng đọc web)
            time.sleep(random.uniform(5, 15))
            
        except requests.exceptions.RequestException as e:
            print(f"[!] Lỗi kết nối: {e}")
            time.sleep(15)

if __name__ == "__main__":
    if "192.168.x.x" in VICTIM_IP:
        print("[LỖI] Vui lòng chỉnh sửa biến VICTIM_IP thành IP thật của Laptop 2.")
        exit(1)
        
    print("=== BẮT ĐẦU CHƯƠNG TRÌNH AUTO BENIGN ===")
    print("Nhấn Ctrl+C để dừng.")
    
    # Chạy 3 luồng (threads) mô phỏng 3 người dùng cùng lướt web
    for i in range(3):
        t = threading.Thread(target=simulate_normal_browsing)
        t.daemon = True
        t.start()
        
    # Giữ chương trình chạy
    while True:
        time.sleep(1)

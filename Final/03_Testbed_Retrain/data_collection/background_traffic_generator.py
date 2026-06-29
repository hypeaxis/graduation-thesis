import time
import random
import requests
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor

def generate_web_traffic(target_ip):
    urls = [
        f"http://{target_ip}/",
        f"http://{target_ip}/DVWA/login.php",
        f"http://{target_ip}/DVWA/about.php",
        f"http://{target_ip}/DVWA/instructions.php"
    ]
    try:
        url = random.choice(urls)
        headers = {'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Mozilla/5.0 (X11; Linux x86_64)'
        ])}
        # Fake a normal web request
        requests.get(url, headers=headers, timeout=5)
        # Sleep randomly to simulate reading time
        time.sleep(random.uniform(0.5, 3.0))
    except Exception:
        pass # Ignore connection errors to keep running

def generate_ssh_traffic(target_ip):
    try:
        # Simulate a quick SSH connection attempt that closes immediately
        cmd = f"nc -w 2 -z {target_ip} 22"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(random.uniform(1.0, 5.0))
    except Exception:
        pass

def generate_ftp_traffic(target_ip):
    try:
        cmd = f"nc -w 2 -z {target_ip} 21"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(random.uniform(1.0, 5.0))
    except Exception:
        pass

def traffic_worker(target_ip):
    while True:
        action = random.choice(['web', 'web', 'web', 'ssh', 'ftp'])
        if action == 'web':
            generate_web_traffic(target_ip)
        elif action == 'ssh':
            generate_ssh_traffic(target_ip)
        elif action == 'ftp':
            generate_ftp_traffic(target_ip)
        
        # Idle time between user actions
        time.sleep(random.uniform(0.1, 2.0))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Background Traffic Generator")
    parser.add_argument("--target", required=True, help="IP của Máy Nạn nhân (Victim)")
    parser.add_argument("--workers", type=int, default=10, help="Số lượng 'người dùng' giả lập đồng thời")
    args = parser.parse_args()

    print(f"[*] Bắt đầu sinh lưu lượng mạng bình thường (Benign) tới {args.target} với {args.workers} luồng...")
    print("[*] Nhấn Ctrl+C để dừng.")

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            for _ in range(args.workers):
                executor.submit(traffic_worker, args.target)
    except KeyboardInterrupt:
        print("\n[*] Đã dừng sinh traffic.")

#!/usr/bin/env python3
"""
auto_benign_v2.py - High-volume Benign Traffic Generator cho Run7
=================================================================
Mục tiêu: ~280,000 flows benign trong 1-1.5 giờ
Cách: 50 workers, sleep 0.5-2.0s, đa dạng traffic

Cách chạy:
    python3 auto_benign_v2.py --target 192.168.0.105 --workers 50
    python3 auto_benign_v2.py --target 192.168.0.105 --workers 50 --duration 5400  # 1.5h
"""

import time
import random
import threading
import argparse
import requests
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Đếm flow ước tính
flow_counter = 0
counter_lock = threading.Lock()


def count_flow(n=1):
    global flow_counter
    with counter_lock:
        flow_counter += n


# ============================================================================
# CÁC LOẠI TRAFFIC BENIGN
# ============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/120.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0",
]

DVWA_PAGES = [
    "/", "/DVWA/", "/DVWA/login.php", "/DVWA/index.php",
    "/DVWA/about.php", "/DVWA/instructions.php", "/DVWA/setup.php",
    "/DVWA/security.php", "/DVWA/phpinfo.php",
]


def http_get_browsing(target):
    """Mô phỏng người dùng lướt web bình thường"""
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        url = f"http://{target}{random.choice(DVWA_PAGES)}"
        requests.get(url, headers=headers, timeout=3)
        count_flow()
    except Exception:
        pass


def http_post_login(target):
    """Mô phỏng login bình thường (đúng user sai pass, hoặc đúng cả 2)"""
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        url = f"http://{target}/DVWA/login.php"
        data = {
            'username': random.choice(['admin', 'user', 'guest']),
            'password': random.choice(['password', 'admin', '123456', 'letmein']),
            'Login': 'Login'
        }
        requests.post(url, headers=headers, data=data, timeout=3)
        count_flow()
    except Exception:
        pass


def http_download_resource(target):
    """Mô phỏng tải resource (CSS, JS, images)"""
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        paths = [
            "/DVWA/dvwa/css/main.css",
            "/DVWA/dvwa/js/dvwaPage.js",
            "/DVWA/dvwa/images/login_logo.png",
            "/DVWA/favicon.ico",
            "/favicon.ico",
        ]
        url = f"http://{target}{random.choice(paths)}"
        requests.get(url, headers=headers, timeout=3)
        count_flow()
    except Exception:
        pass


def ssh_connection_check(target):
    """Mô phỏng kiểm tra SSH port (benign monitoring)"""
    try:
        subprocess.run(
            f"nc -w 2 -z {target} 22",
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        count_flow()
    except Exception:
        pass


def ftp_connection_check(target):
    """Mô phỏng kiểm tra FTP port (benign monitoring)"""
    try:
        subprocess.run(
            f"nc -w 2 -z {target} 21",
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        count_flow()
    except Exception:
        pass


def browsing_session(target):
    """Mô phỏng 1 phiên lướt web hoàn chỉnh: vào trang → đọc → click link → đọc"""
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        session = requests.Session()

        # Bước 1: Vào trang chủ
        session.get(f"http://{target}/DVWA/", headers=headers, timeout=3)
        count_flow()
        time.sleep(random.uniform(0.5, 1.5))

        # Bước 2: Đi tới login page
        session.get(f"http://{target}/DVWA/login.php", headers=headers, timeout=3)
        count_flow()
        time.sleep(random.uniform(0.3, 1.0))

        # Bước 3: Submit login form
        session.post(f"http://{target}/DVWA/login.php", headers=headers,
                     data={'username': 'admin', 'password': 'password', 'Login': 'Login'},
                     timeout=3)
        count_flow()
        time.sleep(random.uniform(0.5, 1.5))

        # Bước 4: Lướt vài trang sau khi login
        for _ in range(random.randint(1, 3)):
            page = random.choice(DVWA_PAGES)
            session.get(f"http://{target}{page}", headers=headers, timeout=3)
            count_flow()
            time.sleep(random.uniform(0.3, 1.0))

    except Exception:
        pass


# ============================================================================
# WORKER CHÍNH
# ============================================================================

def traffic_worker(target, worker_id, stop_event):
    """Worker thread sinh traffic benign liên tục"""
    # Trọng số các loại traffic: web browsing chiếm nhiều nhất
    actions = [
        (http_get_browsing, 35),      # 35% GET requests
        (http_post_login, 10),        # 10% POST login
        (http_download_resource, 20), # 20% tải resource
        (ssh_connection_check, 5),    # 5% SSH check
        (ftp_connection_check, 5),    # 5% FTP check
        (browsing_session, 25),       # 25% full browsing session (nhiều flows)
    ]

    # Xây dựng weighted list
    weighted_actions = []
    for action, weight in actions:
        weighted_actions.extend([action] * weight)

    while not stop_event.is_set():
        try:
            action = random.choice(weighted_actions)
            action(target)

            # Sleep tự nhiên: phần lớn ngắn, đôi khi dài (đọc web)
            sleep_time = random.choices(
                [random.uniform(0.3, 0.8),   # Nhanh (click liên tục)
                 random.uniform(0.8, 1.5),   # Trung bình (đọc lướt)
                 random.uniform(1.5, 3.0)],  # Chậm (đọc kỹ)
                weights=[50, 35, 15]
            )[0]
            time.sleep(sleep_time)

        except Exception:
            time.sleep(1)


def status_reporter(stop_event, target_flows):
    """Thread báo cáo tiến trình định kỳ"""
    start_time = time.time()
    while not stop_event.is_set():
        time.sleep(30)
        elapsed = time.time() - start_time
        rate = flow_counter / elapsed if elapsed > 0 else 0
        pct = (flow_counter / target_flows * 100) if target_flows > 0 else 0
        eta_s = (target_flows - flow_counter) / rate if rate > 0 else 0

        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        eta_min = int(eta_s // 60)
        eta_sec = int(eta_s % 60)

        print(f"  [📊 {mins:02d}:{secs:02d}] Flows: ~{flow_counter:,} ({pct:.1f}%) | "
              f"Rate: ~{rate:.0f}/s | ETA: {eta_min:02d}:{eta_sec:02d}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Auto Benign Traffic v2 — Run7")
    parser.add_argument("--target", required=True, help="IP Victim")
    parser.add_argument("--workers", type=int, default=50, help="Số worker threads (mặc định: 50)")
    parser.add_argument("--duration", type=int, default=0,
                        help="Thời gian chạy tính bằng giây (0 = chạy đến Ctrl+C)")
    parser.add_argument("--target-flows", type=int, default=280000,
                        help="Mục tiêu số flows (để hiển thị progress)")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║        AUTO BENIGN TRAFFIC v2 — Run7 Collection         ║
╠══════════════════════════════════════════════════════════╣
║  Target:     {args.target:<43}║
║  Workers:    {args.workers:<43}║
║  Duration:   {(str(args.duration) + 's') if args.duration > 0 else 'Until Ctrl+C':<43}║
║  Target:     ~{args.target_flows:,} flows{'':<31}║
║                                                          ║
║  Ước tính: {args.workers} workers × ~1.5 req/s = ~{int(args.workers * 1.5)}/s{'':<16}║
╚══════════════════════════════════════════════════════════╝
""")

    stop_event = threading.Event()
    start_time = time.time()

    # Khởi động status reporter
    reporter = threading.Thread(target=status_reporter, args=(stop_event, args.target_flows))
    reporter.daemon = True
    reporter.start()

    # Khởi động workers
    threads = []
    print(f"[*] Khởi động {args.workers} workers...")
    for i in range(args.workers):
        t = threading.Thread(target=traffic_worker, args=(args.target, i, stop_event))
        t.daemon = True
        t.start()
        threads.append(t)
        if (i + 1) % 10 == 0:
            print(f"  ▸ {i + 1}/{args.workers} workers started")

    print(f"[✓] Tất cả {args.workers} workers đang chạy!")
    print("[*] Nhấn Ctrl+C để dừng.\n")

    try:
        if args.duration > 0:
            # Chạy theo thời gian cố định
            time.sleep(args.duration)
            print(f"\n[*] Đã hết thời gian ({args.duration}s)")
        else:
            # Chạy đến khi Ctrl+C
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.time() - start_time
        stop_event.set()
        print(f"\n[*] Đang dừng workers...")
        time.sleep(2)

        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        rate = flow_counter / elapsed if elapsed > 0 else 0

        flow_str = f"{flow_counter:,}"
        rate_str = f"{rate:.0f}"
        print(f"\n╔══════════════════════════════════════════════════════════╗")
        print(f"║               BENIGN TRAFFIC — KẾT QUẢ                  ║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║  Thời gian:    {mins:02d} phút {secs:02d} giây                              ║")
        print(f"║  Flows ước tính: ~{flow_str:<38}║")
        print(f"║  Tốc độ TB:    ~{rate_str} flows/s                                  ║")
        print(f"╚══════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()

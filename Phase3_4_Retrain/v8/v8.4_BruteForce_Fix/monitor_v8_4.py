"""
monitor_v8_4.py — Theo dõi training V8.4 (BruteForce Fix)
Focus: BruteForce Precision / Recall / F1 theo từng epoch.

Chạy: python3 monitor_v8_4.py
"""

import os
import re
import time
import subprocess
from datetime import datetime

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_FILE     = os.path.join(SCRIPT_DIR, 'train_v8_4.log')
MODEL_FILE   = os.path.join(SCRIPT_DIR, 'v8_4_model.pt')
TRAIN_SCRIPT = 'v8_4_train.py'
REFRESH_SEC  = 5

# V8.4 epoch line:
# Epoch 01/25 | Loss: X | B-Acc: X | Macro F1: X | BF F1: X (P:X/R:X) | PS F1: X
RE_EPOCH = re.compile(
    r'Epoch\s+(\d+)/(\d+).*?Loss:\s*([\d.]+).*?B-Acc:\s*([\d.]+)'
    r'.*?Macro F1:\s*([\d.]+).*?BF F1:\s*([\d.]+)\s*\(P:([\d.]+)/R:([\d.]+)\)'
    r'.*?PS F1:\s*([\d.]+)'
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
             '--format=csv,noheader,nounits'], stderr=subprocess.DEVNULL
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
        ep, total_ep, loss, bacc, macro_f1, bf_f1, bf_p, bf_r, ps_f1 = m.groups()
        epochs.append({
            'ep': int(ep), 'total_ep': int(total_ep),
            'loss': float(loss), 'bacc': float(bacc),
            'macro_f1': float(macro_f1),
            'bf_f1': float(bf_f1), 'bf_p': float(bf_p), 'bf_r': float(bf_r),
            'ps_f1': float(ps_f1),
        })
    final = {}
    for m in RE_REPORT.finditer(content):
        label, prec, rec, f1 = m.groups()
        final[label] = {'p': float(prec), 'r': float(rec), 'f1': float(f1)}
    return {
        'epochs':   epochs,
        'finished': bool(RE_DONE.search(content)),
        'final':    final,
        'n_saved':  len(RE_SAVED.findall(content)),
    }


def color(text, code):
    return f'\033[{code}m{text}\033[0m'


def fmt_f1(val, best=None, target=None):
    s = f'{val:.4f}'
    if best is not None and val == best and val > 0:
        return color(s, '92')
    if target is not None and val >= target:
        return color(s, '32')
    if val < 0.3:
        return color(s, '91')
    if val < 0.6:
        return color(s, '93')
    return color(s, '37')


def render_no_log(pid, elapsed_s, gpu_util, gpu_used, gpu_total):
    os.system('clear')
    now = datetime.now().strftime('%H:%M:%S')
    print(color('=' * 62, '36'))
    print(color('  V8.4 BruteForce Fix — MONITOR (no-log mode)', '36') + f'  [{now}]')
    print(color('=' * 62, '36'))
    if pid:
        print(f'\n  PID {pid} — chạy {elapsed_s//60}m {elapsed_s%60}s')
        print(f'  Ước tính epoch: ~{min(elapsed_s//140, 25)}/25')
    else:
        print(color('\n  [!] Không tìm thấy process training!', '91'))
    if gpu_util is not None:
        bar = '█' * int(30 * gpu_util / 100) + '░' * (30 - int(30 * gpu_util / 100))
        col = '92' if gpu_util > 80 else ('93' if gpu_util > 20 else '91')
        print(f'\n  GPU: [{color(bar, col)}] {gpu_util}%  VRAM: {gpu_used}/{gpu_total} MB')
    if os.path.exists(MODEL_FILE):
        ago = int(time.time() - os.path.getmtime(MODEL_FILE))
        mb  = os.path.getsize(MODEL_FILE) / 1024 / 1024
        print(f'\n  Checkpoint: {mb:.1f} MB  |  cập nhật {ago}s trước')
    else:
        print(color('\n  [!] Chưa có checkpoint.', '93'))
    print(f'\n  Chạy bằng ./run_train_v8_4.sh để có log chi tiết')
    print(f'\n  Refresh mỗi {REFRESH_SEC}s  |  Ctrl+C để thoát\n')


def render_with_log(data):
    os.system('clear')
    now = datetime.now().strftime('%H:%M:%S')
    gpu_util, gpu_used, gpu_total = get_gpu()
    pid, elapsed_s = get_process()

    print(color('=' * 70, '36'))
    print(color('  V8.4 — BruteForce Fix Monitor', '36') +
          color('  [CIC FTP+SSH Patator → 4,999 flows]', '37') + f'  [{now}]')
    print(color('=' * 70, '36'))

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
    best_bf    = max(e['bf_f1']    for e in epochs)
    best_ep_m  = next(e['ep'] for e in epochs if e['macro_f1'] == best_macro)
    best_ep_bf = next(e['ep'] for e in epochs if e['bf_f1']    == best_bf)

    pct = done_ep / total_ep * 100
    bar_len = 30
    prog_bar = '█' * int(bar_len * pct / 100) + '░' * (bar_len - int(bar_len * pct / 100))
    print(f'  Tiến độ : [{color(prog_bar, "36")}] {done_ep}/{total_ep} ({pct:.0f}%)')

    # Mục tiêu
    T_BF    = 0.80
    T_MACRO = 0.88
    bf_gap    = T_BF    - best_bf
    macro_gap = T_MACRO - best_macro
    bf_col    = '92' if best_bf    >= T_BF    else ('93' if best_bf    >= 0.60 else '91')
    mac_col   = '92' if best_macro >= T_MACRO else ('93' if best_macro >= 0.75 else '91')

    print(f'  Best BF F1  : {color(f"{best_bf:.4f}", bf_col)} (ep{best_ep_bf})'
          f'  target≥{T_BF:.2f} ({color(f"{bf_gap:+.4f}", bf_col)})')
    print(f'  Best Macro  : {color(f"{best_macro:.4f}", mac_col)} (ep{best_ep_m})'
          f'  target≥{T_MACRO:.2f} ({color(f"{macro_gap:+.4f}", mac_col)})')
    print(f'  Checkpoints : {data["n_saved"]}')

    # Header bảng
    print()
    print(color(f'  {"Ep":>3}  {"Loss":>8}  {"B-Acc":>6}  {"Macro":>7}'
                f'  {"BF_F1":>7}  {"BF_P":>5}  {"BF_R":>5}  {"PS_F1":>7}', '37'))
    print('  ' + '─' * 60)

    for e in epochs:
        is_best = (e['macro_f1'] == best_macro)
        mark    = color(' ★', '92') if is_best else '  '
        bf_col_e = '92' if e['bf_f1'] >= T_BF else ('93' if e['bf_f1'] >= 0.6 else '91')
        bf_f1_s  = color(f'{e["bf_f1"]:.4f}', bf_col_e)
        bf_p_s   = color(f'{e["bf_p"]:.2f}', '37')
        bf_r_s   = color(f'{e["bf_r"]:.2f}', '37')
        print(
            f'  {e["ep"]:>3}  {e["loss"]:>8.4f}  {e["bacc"]:>6.4f}  '
            f'{fmt_f1(e["macro_f1"], best_macro, T_MACRO):>16}  '
            f'{bf_f1_s:>16}  {bf_p_s:>14}  {bf_r_s:>14}  '
            f'{fmt_f1(e["ps_f1"]):>16}{mark}'
        )

    # Kết quả cuối
    if data['finished'] and data['final']:
        print()
        print(color('  ─── KẾT QUẢ CUỐI CÙNG ───', '92'))
        targets  = {'Brute Force': 0.80, 'PortScan': 0.99,
                    'Benign': 0.90, 'DoS': 0.93, 'Web Attack': 0.87}
        order    = ['Brute Force', 'PortScan', 'Benign', 'DoS', 'Web Attack']
        for cls in order:
            if cls in data['final']:
                info = data['final'][cls]
                tgt  = targets.get(cls, 0.80)
                f1   = info['f1']
                col  = '92' if f1 >= tgt else ('93' if f1 >= tgt * 0.8 else '91')
                mark = color('✓', '92') if f1 >= tgt else color('✗', '91')
                bar  = '█' * int(f1 * 20)
                p_s = color(f'{info["p"]:.3f}', col)
                r_s = color(f'{info["r"]:.3f}', col)
                f1_s = color(f'{f1:.4f}', col)
                bar_s = color(bar, col)
                print(f'  {mark} {cls:<15}'
                      f' P={p_s} R={r_s} F1={f1_s}'
                      f'  {bar_s:<20} target≥{tgt:.2f}')

    print()
    if not data['finished']:
        print(f'  Refresh mỗi {REFRESH_SEC}s  |  Ctrl+C để thoát')
    else:
        print(color('  Training hoàn tất. Ctrl+C để thoát.', '92'))


def main():
    print('[*] Monitoring V8.4 BruteForce Fix... (Ctrl+C để dừng)')
    time.sleep(1)
    try:
        while True:
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
                    break
            time.sleep(REFRESH_SEC)
    except KeyboardInterrupt:
        print('\n\n  Thoát monitor.')


if __name__ == '__main__':
    main()

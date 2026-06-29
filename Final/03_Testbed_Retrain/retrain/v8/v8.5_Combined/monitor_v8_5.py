"""
monitor_v8_5.py — Theo dõi training V8.5
Focus: BF (P/R/F1) + WebAttack F1 + PortScan F1 + Macro F1

Chạy: python3 monitor_v8_5.py
"""

import os, re, time, subprocess
from datetime import datetime

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_FILE     = os.path.join(SCRIPT_DIR, 'train_v8_5.log')
MODEL_FILE   = os.path.join(SCRIPT_DIR, 'v8_5_model.pt')
TRAIN_SCRIPT = 'v8_5_train.py'
REFRESH_SEC  = 5

# Epoch 01/30 | Loss: X | B-Acc: X | Macro F1: X | BF: X(PX/RX) | WA: X | PS: X
RE_EPOCH = re.compile(
    r'Epoch\s+(\d+)/(\d+).*?Loss:\s*([\d.]+).*?B-Acc:\s*([\d.]+)'
    r'.*?Macro F1:\s*([\d.]+).*?BF:\s*([\d.]+)\(P([\d.]+)/R([\d.]+)\)'
    r'.*?WA:\s*([\d.]+).*?PS:\s*([\d.]+)'
)
RE_SAVED  = re.compile(r'Checkpoint saved \(Macro F1:\s*([\d.]+)\)')
RE_DONE   = re.compile(r'Model\s+:.*v8_5|KẾT QUẢ CUỐI CÙNG')
RE_REPORT = re.compile(
    r'(Benign|Brute Force|DoS|PortScan|Web Attack)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+\d+'
)


def get_gpu():
    try:
        out = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total',
             '--format=csv,noheader,nounits'], stderr=subprocess.DEVNULL
        ).decode().strip()
        u, m, t = out.split(',')
        return int(u.strip()), int(m.strip()), int(t.strip())
    except Exception:
        return None, None, None


def get_process():
    try:
        out = subprocess.check_output(['pgrep', '-f', TRAIN_SCRIPT],
                                       stderr=subprocess.DEVNULL).decode().strip()
        pids = out.split()
        if not pids:
            return None, None
        pid = pids[0]
        elapsed = subprocess.check_output(['ps', '-p', pid, '-o', 'etimes='],
                                           stderr=subprocess.DEVNULL).decode().strip()
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
        ep, tot, loss, bacc, macro, bf_f1, bf_p, bf_r, wa_f1, ps_f1 = m.groups()
        epochs.append({'ep': int(ep), 'total_ep': int(tot),
                        'loss': float(loss), 'bacc': float(bacc),
                        'macro_f1': float(macro),
                        'bf_f1': float(bf_f1), 'bf_p': float(bf_p), 'bf_r': float(bf_r),
                        'wa_f1': float(wa_f1), 'ps_f1': float(ps_f1)})
    final = {}
    for m in RE_REPORT.finditer(content):
        label, p, r, f1 = m.groups()
        final[label] = {'p': float(p), 'r': float(r), 'f1': float(f1)}
    return {'epochs': epochs, 'finished': bool(RE_DONE.search(content)),
            'final': final, 'n_saved': len(RE_SAVED.findall(content))}


def C(text, code):
    return f'\033[{code}m{text}\033[0m'


def fmt(val, best=None, tgt=None):
    s = f'{val:.4f}'
    if best is not None and val == best and val > 0:
        return C(s, '92')
    if tgt is not None and val >= tgt:
        return C(s, '32')
    return C(s, '91' if val < 0.3 else ('93' if val < 0.6 else '37'))


def render_no_log(pid, elapsed_s, gu, gm, gt):
    os.system('clear')
    now = datetime.now().strftime('%H:%M:%S')
    print(C('=' * 62, '36'))
    print(C('  V8.5 Combined Best — MONITOR (no-log)', '36') + f'  [{now}]')
    print(C('=' * 62, '36'))
    if pid:
        print(f'\n  PID {pid} — {elapsed_s//60}m {elapsed_s%60}s')
        print(f'  Ước tính epoch: ~{min(elapsed_s//150, 15)}/15 (early stop)')
    else:
        print(C('\n  [!] Không tìm thấy process!', '91'))
    if gu is not None:
        bar = '█' * int(30 * gu / 100) + '░' * (30 - int(30 * gu / 100))
        col = '92' if gu > 80 else ('93' if gu > 20 else '91')
        print(f'\n  GPU: [{C(bar, col)}] {gu}%  VRAM: {gm}/{gt} MB')
    if os.path.exists(MODEL_FILE):
        ago = int(time.time() - os.path.getmtime(MODEL_FILE))
        mb  = os.path.getsize(MODEL_FILE) / 1024 / 1024
        print(f'\n  Checkpoint: {mb:.1f} MB  |  {ago}s trước')
    else:
        print(C('\n  [!] Chưa có checkpoint.', '93'))
    print(f'\n  Chạy bằng: ./run_train_v8_5.sh')
    print(f'\n  Refresh {REFRESH_SEC}s  |  Ctrl+C để thoát\n')


def render_with_log(data):
    os.system('clear')
    now = datetime.now().strftime('%H:%M:%S')
    gu, gm, gt = get_gpu()
    pid, elapsed_s = get_process()

    print(C('=' * 72, '36'))
    print(C('  V8.5 Combined Best + Anti-Overfit', '36') +
          C('  [mixed BF + CIC WebAttack]', '37') + f'  [{now}]')
    print(C('=' * 72, '36'))

    status = C('✓ HOÀN TẤT', '92') if data['finished'] else C('⟳ ĐANG CHẠY', '93')
    print(f'\n  Status: {status}', end='')
    if pid:
        print(f'  |  PID {pid}  |  {elapsed_s//60}m {elapsed_s%60}s', end='')
    if gu is not None:
        print(f'  |  GPU {gu}%  ({gm}/{gt} MB)', end='')
    print()

    epochs = data['epochs']
    if not epochs:
        print(C('\n  Đang khởi tạo...', '93'))
        print(f'\n  Refresh {REFRESH_SEC}s  |  Ctrl+C để thoát')
        return

    total_ep   = epochs[0]['total_ep']
    done_ep    = len(epochs)
    best_macro = max(e['macro_f1'] for e in epochs)
    best_bf    = max(e['bf_f1']    for e in epochs)
    best_wa    = max(e['wa_f1']    for e in epochs)
    ep_bm  = next(e['ep'] for e in epochs if e['macro_f1'] == best_macro)
    ep_bf  = next(e['ep'] for e in epochs if e['bf_f1']    == best_bf)
    ep_wa  = next(e['ep'] for e in epochs if e['wa_f1']    == best_wa)

    pct = done_ep / total_ep * 100
    bar = '█' * int(30 * pct / 100) + '░' * (30 - int(30 * pct / 100))
    print(f'  Progress : [{C(bar, "36")}] {done_ep}/{total_ep} ({pct:.0f}%)'
          f'  |  Checkpoints: {data["n_saved"]}')

    # Targets
    T = {'macro': 0.93, 'bf': 0.85, 'wa': 0.90, 'ps': 0.99}
    def gap_str(val, tgt):
        d = val - tgt
        col = '92' if d >= 0 else ('93' if d > -0.05 else '91')
        return C(f'{d:+.4f}', col)

    print(f'  Best Macro F1 : {C(f"{best_macro:.4f}", "92")} (ep{ep_bm})'
          f'  target≥{T["macro"]}  {gap_str(best_macro, T["macro"])}')
    print(f'  Best BF F1    : {C(f"{best_bf:.4f}", "92")} (ep{ep_bf})'
          f'  target≥{T["bf"]}  {gap_str(best_bf, T["bf"])}')
    print(f'  Best WA F1    : {C(f"{best_wa:.4f}", "92")} (ep{ep_wa})'
          f'  target≥{T["wa"]}  {gap_str(best_wa, T["wa"])}')

    # Epoch table
    print()
    hdr = f'  {"Ep":>3}  {"Loss":>8}  {"Macro":>7}  {"BF_F1":>7}  {"BF_P":>5}  {"BF_R":>5}  {"WA_F1":>7}  {"PS_F1":>7}'
    print(C(hdr, '37'))
    print('  ' + '─' * 62)

    for e in epochs:
        is_best = (e['macro_f1'] == best_macro)
        mark    = C(' ★', '92') if is_best else '  '
        bf_col  = '92' if e['bf_f1'] >= T['bf'] else ('93' if e['bf_f1'] >= 0.6 else '91')
        wa_col  = '92' if e['wa_f1'] >= T['wa'] else ('93' if e['wa_f1'] >= 0.7 else '91')
        bf_s    = C(f'{e["bf_f1"]:.4f}', bf_col)
        wa_s    = C(f'{e["wa_f1"]:.4f}', wa_col)
        bf_p_s  = C(f'{e["bf_p"]:.2f}', '37')
        bf_r_s  = C(f'{e["bf_r"]:.2f}', '37')
        print(f'  {e["ep"]:>3}  {e["loss"]:>8.4f}  '
              f'{fmt(e["macro_f1"], best_macro, T["macro"]):>16}  '
              f'{bf_s:>16}  {bf_p_s:>14}  {bf_r_s:>14}  '
              f'{wa_s:>16}  {fmt(e["ps_f1"], tgt=T["ps"]):>16}{mark}')

    # Final
    if data['finished'] and data['final']:
        print()
        print(C('  ─── KẾT QUẢ CUỐI CÙNG ───', '92'))
        targets = {'Brute Force': T['bf'], 'Web Attack': T['wa'],
                   'PortScan': T['ps'], 'Benign': 0.92, 'DoS': 0.93}
        for cls in ['Brute Force', 'Web Attack', 'PortScan', 'Benign', 'DoS']:
            if cls in data['final']:
                info = data['final'][cls]
                tgt  = targets.get(cls, 0.85)
                f1   = info['f1']
                col  = '92' if f1 >= tgt else ('93' if f1 >= tgt * 0.85 else '91')
                mk   = C('✓', '92') if f1 >= tgt else C('✗', '91')
                p_s  = C(f'{info["p"]:.3f}', col)
                r_s  = C(f'{info["r"]:.3f}', col)
                f1_s = C(f'{f1:.4f}', col)
                bar  = C('█' * int(f1 * 20), col)
                print(f'  {mk} {cls:<15} P={p_s} R={r_s} F1={f1_s}  {bar}  target≥{tgt:.2f}')

    print()
    if not data['finished']:
        print(f'  Refresh {REFRESH_SEC}s  |  Ctrl+C để thoát')
    else:
        print(C('  Training hoàn tất. Ctrl+C để thoát.', '92'))


def main():
    print('[*] Monitoring V8.5... (Ctrl+C để dừng)')
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
                gu, gm, gt = get_gpu()
                render_no_log(pid, elapsed_s, gu, gm, gt)
                if not pid and os.path.exists(MODEL_FILE):
                    break
            time.sleep(REFRESH_SEC)
    except KeyboardInterrupt:
        print('\n\n  Thoát monitor.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Theo dõi tiến trình train v8_6 (parse log, không cần đụng job đang chạy).

Dùng:
  python training/watch_train.py                # 1 lần (snapshot)
  python training/watch_train.py --follow       # tự refresh mỗi 5s (Ctrl-C để thoát)
  python training/watch_train.py <file.log>     # chỉ định log khác

Đọc từ log do v8_x_train.py sinh ra: dòng "Epoch NN/MM | ... | Macro F1: ..." + checkpoint.
"""
from __future__ import annotations
import re, sys, time, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_LOG = HERE / "v8_7_train.log"
TRAIN_SCRIPT = r"v8_[0-9]_train"        # pgrep -f regex: khớp mọi script v8_x_train*.py

EPOCH_RE = re.compile(
    r"Epoch\s+(\d+)/(\d+)\s+\|\s+Loss:\s+([\d.]+)\s+\|\s+B-Acc:\s+([\d.]+)\s+\|\s+"
    r"Macro F1:\s+([\d.]+)\s+\|\s+BF:\s+([\d.]+).*?WA:\s+([\d.]+)\s+\|\s+PS:\s+([\d.]+)")
CKPT_RE = re.compile(r"Checkpoint saved \(Macro F1:\s+([\d.]+)\)")
FINAL_RE = re.compile(r"Macro F1\s+:\s+([\d.]+)")
STOP_RE = re.compile(r"Early stop tại epoch (\d+)")

SPARK = "▁▂▃▄▅▆▇█"


def proc_status():
    """(alive, pid, elapsed_seconds) của job train — dò theo tên script.
    Lưu ý: PyTorch đổi comm thành 'pt_main_thread' -> phải xét token đầu của ARGS
    (interpreter python), không dựa vào comm. Đồng thời loại các bash-wrapper."""
    try:
        pids = subprocess.run(["pgrep", "-f", TRAIN_SCRIPT],
                              capture_output=True, text=True).stdout.split()
        for pid in pids:
            r = subprocess.run(["ps", "-o", "etimes=,args=", "-p", pid],
                               capture_output=True, text=True).stdout.strip()
            parts = r.split(None, 1)
            if len(parts) < 2:
                continue
            etimes, args = parts[0], parts[1]
            first = args.split()[0] if args.split() else ""
            if "python" in first and "train" in args:        # là tiến trình python thật (bỏ bash -c)
                return True, pid, int(etimes)
    except Exception:
        pass
    return False, None, None


def spark(vals, lo=None, hi=None):
    if not vals:
        return ""
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    if hi <= lo:
        return SPARK[-1] * len(vals)
    return "".join(SPARK[min(len(SPARK) - 1, int((v - lo) / (hi - lo) * (len(SPARK) - 1)))] for v in vals)


def render(log_path: Path) -> str:
    if not log_path.exists():
        return f"[!] Chưa có log: {log_path}"
    text = log_path.read_text(errors="ignore")
    epochs = EPOCH_RE.findall(text)
    alive, pid, elapsed = proc_status()

    L = []
    L.append("═" * 66)
    L.append(f" THEO DÕI TRAIN  ·  {log_path.name}")
    if alive:
        m, s = divmod(elapsed, 60)
        L.append(f" Trạng thái: 🟢 ĐANG CHẠY  (pid {pid}, đã {m}m{s:02d}s)")
    else:
        done = "✓ hoàn tất" if (FINAL_RE.search(text) or STOP_RE.search(text)) else "⏹ dừng/chưa chạy"
        L.append(f" Trạng thái: ⚪ {done}")
    L.append("═" * 66)

    if not epochs:
        # có thể còn ở giai đoạn nạp dữ liệu
        tail = [ln for ln in text.strip().splitlines() if ln.strip()][-4:]
        L.append(" Chưa có epoch nào (đang nạp dữ liệu / epoch 1 chạy dở). Log cuối:")
        L += [f"   {ln}" for ln in tail]
        return "\n".join(L)

    f1s = [float(e[4]) for e in epochs]
    total = int(epochs[-1][1])
    cur = int(epochs[-1][0])
    best = max(f1s); best_ep = f1s.index(best) + 1
    last = epochs[-1]

    # progress bar
    filled = int(cur / total * 40)
    bar = "█" * filled + "·" * (40 - filled)
    L.append(f" Epoch {cur}/{total}  [{bar}]  {cur/total*100:.0f}%")
    # ETA từ tốc độ trung bình (nếu đang chạy)
    if alive and elapsed and cur:
        per = elapsed / cur
        eta = int(per * (total - cur))
        L.append(f" ~{per:.0f}s/epoch  ·  ETA còn ~{eta//60}m{eta%60:02d}s")
    L.append("")
    L.append(f" Macro-F1  hiện: {float(last[4]):.4f}   |   BEST: {best:.4f} (epoch {best_ep})")
    L.append(f" Xu hướng:  {spark(f1s)}  [{f1s[0]:.3f} → {f1s[-1]:.3f}]")
    L.append(f" Loss hiện: {float(last[2]):.4f}   B-Acc: {float(last[3]):.4f}")
    L.append(f" Per-class F1  ·  BruteForce {float(last[5]):.3f}  WebAttack {float(last[6]):.3f}  PortScan {float(last[7]):.3f}")

    # tiêu chí Done Bước 4: Macro-F1 CIC val >= ~0.96
    tag = "✅ ĐẠT (≥0.96)" if best >= 0.96 else "⚠️ dưới 0.96" if best >= 0.90 else "❌ thấp (<0.90)"
    L.append(f" Tiêu chí model tốt (Macro-F1 CIC val ≥0.96): {tag}")

    if STOP_RE.search(text):
        L.append(f" ⏹ Early stop tại epoch {STOP_RE.search(text).group(1)}")
    fin = FINAL_RE.findall(text)
    if fin and not alive:
        L.append(f" 🏁 Macro-F1 cuối (best checkpoint): {float(fin[-1]):.4f}")
    L.append("═" * 66)
    return "\n".join(L)


def main():
    args = [a for a in sys.argv[1:]]
    follow = "--follow" in args
    args = [a for a in args if a != "--follow"]
    log_path = Path(args[0]) if args else DEFAULT_LOG

    if not follow:
        print(render(log_path))
        return
    try:
        while True:
            print("\033[2J\033[H", end="")   # clear screen
            print(render(log_path))
            alive, *_ = proc_status()
            if not alive and (EPOCH_RE.search(log_path.read_text(errors="ignore")) if log_path.exists() else False):
                print("\n[i] Job đã kết thúc — dừng theo dõi.")
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[i] Thoát theo dõi.")


if __name__ == "__main__":
    main()

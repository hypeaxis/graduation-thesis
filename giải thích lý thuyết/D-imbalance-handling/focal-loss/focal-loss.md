# Focal Loss — vặn nhỏ tiếng mẫu dễ, khuếch đại mẫu khó

## Nó sinh ra để giải quyết chuyện gì?

[[cross-entropy]] có điểm yếu chí mạng: khi dữ liệu lệch, **hàng nghìn mẫu dễ của lớp đông** cộng dồn gradient,
**át** lớp hiếm. Model học tốt cái đã dễ, bỏ bê cái đang khó.

**Focal Loss** (Lin et al., 2017) vá đúng chỗ đó: nó thêm một **hệ số tự động hạ trọng số những mẫu đã dễ**,
để model dồn sức vào **mẫu còn khó** (thường là lớp thiểu số).

> **So sánh đời thường:** như cái **loa tự cân âm** — ai đang nói to (mẫu dễ, đã đúng chắc) thì vặn nhỏ lại;
> ai thì thầm (mẫu khó, đang sai) thì khuếch đại lên. Nhờ vậy thầy nghe được cả nhóm ít nói.

---

## Công thức — bóc từng mảnh

```
L_FL = − α_t · (1 − p_t)^γ · log(p_t)
```

- **`log(p_t)`** → phần Cross-Entropy gốc.
- **`(1 − p_t)^γ`** → **hệ số điều biến (modulating factor)**, trái tim của Focal Loss:
  - Mẫu **dễ** (`p_t → 1`): `(1−p_t)` gần 0 → hệ số **teo về 0** → gần như *tắt tiếng* mẫu này.
  - Mẫu **khó** (`p_t` nhỏ): `(1−p_t)` gần 1 → hệ số **giữ nguyên** → mẫu này vẫn "kêu to".
- **`γ` (gamma)** → nút vặn độ mạnh. `γ=0` → quay về CE. `γ` càng lớn càng mạnh tay với mẫu dễ (đề tài dùng `γ=2`).
- **`α_t`** → trọng số theo lớp (cân thêm giữa các lớp; xem [[class-balanced-focal-loss]]).

---

## Ví dụ SỐ: gradient bị ĐẢO NGƯỢC

Vẫn batch 1000 Benign (`p_t=0,95`) + 10 BruteForce (`p_t=0,4`), với `γ=2`:

| Mẫu | $p_t$ | hệ số $(1-p_t)^2$ | so với CE | Tổng gradient (FL) |
|---|---|---|---|---|
| Benign (1000) | 0,95 | $0,05^2=0,0025$ | giảm **400×** | ≈ **0,128** |
| BruteForce (10) | 0,40 | $0,6^2=0,36$ | giảm ít | ≈ **3,30** |

→ Tỷ lệ đóng góp gradient **đảo ngược**: từ Benign áp đảo **5,6:1** thành **BruteForce áp đảo 25,8:1**.

> **Nói đơn giản:** trước đây lớp đông "nói át"; giờ Focal Loss bịt bớt miệng mẫu dễ → mẫu khó của lớp hiếm
> mới là tiếng nói chính dẫn dắt việc học.

---

## Giới hạn quan trọng: chỉ chữa "mất cân bằng gradient", không chữa "không phân tách"

Focal Loss giả định: hai lớp **có thể phân tách được**, chỉ là lớp đông át gradient. Khi hai lớp **nằm chồng
lên nhau trong không gian đặc trưng** (như PortScan WSL và Benign — xem [[portscan-inseparability-nat]]),
Focal Loss **bó tay**: không có ranh giới nào để học tốt hơn, dù có vặn trọng số kiểu gì.

Bằng chứng trong đồ án: PortScan F1 **7,5% → 6,8%** khi thêm Focal Loss `γ=2` (không cải thiện, thậm chí giảm nhẹ).

---

## Tóm lại

- Focal Loss = Cross-Entropy **× hệ số `(1−p_t)^γ`** để **hạ trọng số mẫu dễ**, dồn sức vào mẫu khó.
- Với `γ=2`, gradient của Benign giảm ~400× → **đảo ngược** ưu thế, lớp hiếm được học tử tế.
- **Chỉ chữa mất cân bằng gradient**, không chữa được trường hợp hai lớp **không phân tách**.

**Hiểu cái này thì làm được gì?** Bạn biết *khi nào Focal Loss cứu được* (lớp hiếm phân tách được nhưng bị át)
và *khi nào vô ích* (hai lớp trộn lẫn) — đúng bài học lớn của đồ án: chọn đúng thuốc cho đúng bệnh.

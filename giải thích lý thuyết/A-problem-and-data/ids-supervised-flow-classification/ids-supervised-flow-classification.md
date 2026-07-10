# Phát hiện xâm nhập như một bài toán phân loại có giám sát trên flow

## Nó sinh ra để giải quyết chuyện gì?

Câu hỏi gốc của IDS (Intrusion Detection System — hệ thống phát hiện xâm nhập) rất đơn giản:
*"Kết nối mạng này là bình thường hay là tấn công?"*

Để máy trả lời được, ta phải **biến câu hỏi đó thành một bài toán máy học**. Cách đề tài chọn là:
**phân loại có giám sát (supervised classification)** trên đơn vị **flow**.

> **Nói nôm na:** thay vì soi từng gói tin lẻ (quá chi tiết, quá nhiều), ta gom chúng thành từng "cuộc hội thoại"
> rồi dạy máy nhìn đặc điểm cuộc hội thoại đó mà đoán: lành hay độc.

---

## Flow là gì? — "cuộc hội thoại" giữa hai máy

Một **flow** là chuỗi gói tin giữa hai đầu cuối, xác định bởi **5-tuple**:

- **IP nguồn** (ai gửi)
- **IP đích** (gửi cho ai)
- **Cổng nguồn** (cửa ra)
- **Cổng đích** (cửa vào — cổng 80 = web, 22 = SSH…)
- **Giao thức** (TCP/UDP…)

…trong một khoảng thời gian nhất định.

> **So sánh đời thường:** flow giống **một cuộc gọi điện thoại**: cùng số gọi – số nhận – trong cùng một
> phiên thì tính là *một* cuộc, dù nói qua nói lại hàng trăm câu (gói tin).

---

## Công thức hoá bài toán

Gọi một flow được mô tả bằng **vector đặc trưng** `x` gồm `k` con số thống kê (duration, số packet, flag…):

```
x = [x₁, x₂, …, x_k] ∈ ℝ^k
```

Ta cần một **bộ phân loại (classifier)** `f` học từ dữ liệu có nhãn, ánh xạ:

```
f : ℝ^k → {Benign, DoS, PortScan, BruteForce, …}
nhãn dự đoán = argmax_c  P(lớp = c | x)
```

Bóc từng mảnh:

- **`x` (input)** → bản tóm tắt bằng số của một flow.
- **`f` (model)** → cái "bộ não" học được từ hàng triệu ví dụ đã dán nhãn.
- **"có giám sát" (supervised)** → mỗi ví dụ huấn luyện đã kèm đáp án đúng (nhãn), máy học bằng cách so đoán với đáp án.
- **`argmax`** → chọn lớp có xác suất cao nhất làm câu trả lời cuối.

---

## Ví dụ cụ thể

Một flow có: `Flow_Duration = 0,3ms`, `Fwd_Packets = 1`, `SYN_flag = 1`, `FIN_flag = 0`, gửi tới cổng lạ.

→ Máy nhìn tổ hợp "cực ngắn + 1 gói SYN + không bắt tay xong" và đoán **PortScan** với xác suất 0,97.

Một flow khác: `Flow_Duration = 2,5s`, `Fwd_Packets = 40`, gói dài 800 byte tới cổng 80.

→ Máy đoán **Benign** (duyệt web bình thường) với xác suất 0,93.

---

## Vì sao chọn tầng "flow" chứ không phải gói tin lẻ?

- **Gói tin lẻ**: quá nhiều, quá chi tiết, và **payload thường mã hoá** (TLS/HTTPS) → không đọc được nội dung.
- **Flow**: gom lại thành **một vector cố định độ dài** → gọn, dạng bảng (tabular), hợp với mô hình máy học,
  và **vẫn hoạt động dù traffic mã hoá** vì chỉ dùng thống kê metadata.

> **Nói đơn giản:** ta không cần đọc trộm nội dung thư, chỉ cần nhìn *ai gửi cho ai, dày mỏng ra sao,
> nhanh chậm thế nào* là đã đoán được ý đồ.

---

## Tóm lại

- IDS được đóng khung thành **phân loại có giám sát**: input là **vector đặc trưng của một flow**,
  output là **nhãn Benign / loại tấn công**.
- **Flow** = một "cuộc hội thoại" định danh bởi **5-tuple**.
- Model `f` học từ ví dụ có nhãn rồi chọn lớp xác suất cao nhất bằng `argmax`.

**Hiểu cái này thì làm được gì?** Đây là *cái khung* mà toàn bộ đồ án đứng lên: mọi kỹ thuật sau này
(FT-Transformer, Focal Loss, ensemble…) đều chỉ là những cách **làm cho hàm `f` này giỏi hơn** — nhất là
ở những lớp tấn công hiếm và khó.

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Vector đặc trưng x của flow | `Final/05_Replay_Detection/ids_replay/features.py` |
| Model f + suy luận (argmax softmax) | `Final/05_Replay_Detection/ids_replay/model.py` |
| Pipeline flow → nhãn (triển khai) | `Final/04_HybridIDS_Deployment/wsl_pipeline/testbed_inference.py` |

**Khi phản biện:** nhấn mạnh input là **vector thống kê của flow** (không phải payload thô), output là `argmax` trên phân phối softmax các lớp.

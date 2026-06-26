# Chỉ dẫn cho agent viết đồ án theo template (LaTeX)

Tài liệu này quy định cách bạn (agent) viết một đồ án hoàn chỉnh bằng LaTeX, dựa trên template được cung cấp và dữ liệu thật của dự án trong folder. Mục tiêu: bản thảo bám khung template, dùng đúng tài nguyên của dự án, giải thích kỹ các lựa chọn, không thừa chi tiết, và đọc như do con người viết. Khi các chỉ dẫn mâu thuẫn nhau, ưu tiên theo thứ tự: (1) yêu cầu cụ thể trong template, (2) các nguyên tắc dưới đây, (3) phán đoán hợp lý của bạn.

> Phạm vi: Các quy tắc văn phong (đặc biệt mục 10) áp dụng cho **nội dung đồ án** bạn viết ra, không áp dụng cho chính tài liệu chỉ dẫn này.

## 1. Nguyên tắc nền tảng

- **Bám khung template, sửa tiêu đề cho khớp dự án.** Giữ cấu trúc phân cấp, định dạng, đánh số và quy ước LaTeX của template; thay nội dung các đầu mục/tiêu đề bằng tiêu đề phù hợp với dự án thực tế.
- **Chỉ dùng tài nguyên thật trong folder.** Mọi hình ảnh, số liệu, sơ đồ kiến trúc, kết quả đều lấy từ folder dự án. Không bịa, không suy diễn ngoài dữ liệu có sẵn.
- **Giải thích kỹ "tại sao", không chỉ "cái gì".** Với mỗi quyết định và lựa chọn, nêu rõ lý do và đánh đổi.
- **Đủ là dừng.** Viết đúng những gì cần để làm rõ luận điểm; không kéo dài, không tô vẽ.
- **Giọng người, không giọng máy.** Văn bản tự nhiên, có mạch lập luận riêng, tránh khuôn mẫu.
- **Làm theo bước.** Trình mục lục cho người dùng trước khi viết; nêu rõ kế hoạch trước mỗi phần (xem mục 11).

## 2. Làm việc với template LaTeX

**Sửa đầu mục cho khớp dự án.** Template hiện tại có các tiêu đề/đầu mục mang tính khung mẫu. Hãy thay phần văn bản tiêu đề bằng tiêu đề phản ánh đúng nội dung dự án, nhưng giữ nguyên:

- Loại lệnh và cấp bậc phân mục (`\chapter`, `\section`, `\subsection`, `\subsubsection`) — chỉ đổi chữ bên trong tiêu đề, không đổi cấp bậc.
- Hệ thống đánh số tự động của template.
- Preamble, các gói (packages), lệnh tùy biến và style — để biên dịch không lỗi.

Chỉ thêm, gộp hoặc bỏ một mục khi nội dung dự án thực sự đòi hỏi, và phải nằm trong phong cách phân cấp của template. Khi đã chỉnh xong khung mục, đây chính là mục lục bạn phải trình cho người dùng (mục 11).

**Giữ cho LaTeX biên dịch được.**

- Escape đúng các ký tự đặc biệt: `%`, `&`, `_`, `#`, `$`, `{`, `}`.
- Dùng nhãn (`\label`) nhất quán theo tiền tố: `sec:`, `fig:`, `tab:`, `eq:`; tham chiếu chéo bằng `\ref{}` hoặc `\autoref{}` thay vì gõ số cứng.
- Nếu môi trường cho phép, biên dịch thử (pdflatex/xelatex tùy template) và sửa hết lỗi trước khi coi là hoàn tất.

## 3. Hình ảnh, dữ liệu và kiến trúc từ folder dự án

- Đọc folder dự án trước khi viết: liệt kê các ảnh, biểu đồ, sơ đồ kiến trúc, tệp dữ liệu và kết quả có sẵn, rồi viết dựa trên đó.
- Chèn ảnh bằng môi trường `figure` với `\includegraphics` trỏ đúng tới tệp trong folder; kèm `\caption` đủ nghĩa và `\label`. Chèn bảng bằng `table` + `tabular`, cũng có `\caption` và `\label`.
- **Đặt hình/biểu đồ đúng chỗ:** ngay tại điểm logic mà văn bản đề cập tới nó lần đầu, không dồn hết về cuối phần. Mỗi hình phải được dẫn trong văn (ví dụ: "Hình~\ref{fig:...} cho thấy…").
- **Viết lý do cho mỗi hình:** nêu hình thể hiện gì, cách đọc nó, và vì sao nó cần xuất hiện ở đây. Chỉ thêm hình khi nó làm rõ một luận điểm — không trang trí.
- Số liệu trích từ dữ liệu thật trong folder; ghi rõ nguồn/tệp khi cần. Không chế số liệu cho "đẹp".

## 4. Công thức

- Ghi **đầy đủ** công thức. Dùng `equation`/`align` cho công thức tách dòng (có đánh số và `\label` để tham chiếu), `$...$` cho công thức trong dòng.
- Định nghĩa rõ mọi ký hiệu và đơn vị ngay khi xuất hiện lần đầu; giữ ký hiệu nhất quán trong toàn đồ án.
- Khi dẫn lại công thức ở chỗ khác, tham chiếu bằng `\eqref{}`/`\ref{}` thay vì chép lại.
- Mỗi công thức quan trọng cần một câu giải thích ý nghĩa và vai trò của nó trong lập luận.

## 5. Trình bày các giai đoạn và chọn phương án tốt nhất

- Trình bày đầy đủ nội dung từng giai đoạn của dự án, theo đúng dữ liệu và kết quả thật trong folder.
- Khi một giai đoạn có nhiều phiên bản hoặc nhiều lần thử, **chọn phiên bản tốt nhất**. Nêu rõ tiêu chí so sánh và số liệu/kết quả làm căn cứ cho lựa chọn.
- **Giải thích kỹ lý do** của mỗi quyết định: vì sao chọn cách này thay vì cách khác, đánh đổi là gì, lựa chọn ảnh hưởng tới kết quả ra sao. Phần "tại sao" quan trọng ngang phần "làm gì".
- Có thể nhắc ngắn gọn các phiên bản bị loại nếu cần để biện minh cho lựa chọn, nhưng trọng tâm vẫn là phương án được chọn. Đừng sa đà mô tả những thứ không dùng.

## 6. Phân chia và tổ chức nội dung

- Mỗi chương, mỗi mục có một nhiệm vụ rõ ràng; chỉ viết nội dung phục vụ nhiệm vụ đó.
- Phân bổ dung lượng theo tầm quan trọng của nội dung, không chia đều một cách máy móc giữa các mục.
- Sắp xếp theo mạch logic phù hợp với loại đồ án (ví dụ: đặt vấn đề → cơ sở lý thuyết → phương pháp/thiết kế → kết quả → đánh giá → kết luận).
- Mỗi đoạn văn triển khai một ý chính. Câu đầu đoạn nêu ý; các câu sau làm rõ, dẫn chứng hoặc lập luận cho ý đó.
- Liên kết giữa các mục bằng nội dung (ý sau nối tiếp ý trước), không bằng câu nối sáo rỗng.
- Không lặp lại cùng một nội dung ở nhiều chương. Nếu cần nhắc lại, dẫn chiếu ngắn gọn thay vì viết lại.

## 7. Cách dùng từ ngữ

- Dùng văn phong khách quan, trang trọng, đúng chuẩn học thuật.
- Thuật ngữ chuyên ngành phải nhất quán trong toàn bộ đồ án. Lần đầu xuất hiện, viết đầy đủ kèm dạng viết tắt (nếu có); các lần sau dùng thống nhất một dạng.
- Tránh từ cảm tính, khẩu ngữ và ngôn ngữ quảng cáo: "tuyệt vời", "đột phá", "cực kỳ", "vô cùng mạnh mẽ".
- Hạn chế đại từ nhân xưng cá nhân. Ưu tiên cách diễn đạt khách quan: "đồ án này", "nghiên cứu", "hệ thống được đề xuất".
- Viết câu rõ ràng, mỗi câu một ý khi có thể. Tránh câu quá dài với nhiều mệnh đề lồng nhau.
- Thống nhất cách trình bày số liệu, đơn vị đo, ký hiệu và công thức theo một chuẩn duy nhất.

## 8. Sử dụng tài liệu tham khảo

- Đọc tài liệu để hiểu bối cảnh lĩnh vực, nắm thuật ngữ và học cách lập luận đặc thù của ngành — không phải để sao chép.
- Quan sát văn phong trong các tài liệu mẫu tốt (cách mở đầu, cách lập luận, mật độ thuật ngữ, cách dẫn nguồn) và viết theo đúng chuẩn mực đó của lĩnh vực.
- Chỉ đưa vào đồ án những thông tin có căn cứ trong tài liệu. Không suy diễn ngoài dữ liệu, không bịa số liệu hay nguồn.
- Diễn đạt lại bằng lời của mình; không dán nguyên văn. Trích dẫn bằng lệnh `\cite{}` với khóa trong tệp `.bib`, theo đúng kiểu trích dẫn (bibliography style) của template.
- Khi không chắc chắn về một thông tin, ghi rõ mức độ chưa chắc chắn hoặc bỏ qua, tuyệt đối không lấp đầy bằng phỏng đoán.
- Chỉ giữ những chi tiết phục vụ trực tiếp cho luận điểm. Bỏ qua chi tiết bên lề, kể cả khi nó thú vị.
- Khi các nguồn mâu thuẫn, nêu rõ sự khác biệt thay vì chọn bừa một bên.

## 9. Tránh chi tiết thừa

- Kiểm tra từng câu: nếu xóa đi mà luận điểm không đổi, hãy xóa.
- Không thêm bối cảnh chung chung mà người đọc chuyên ngành đã biết.
- Không nhắc lại điều đã trình bày; dùng "như đã nêu" một cách tiết chế.
- Không thêm khuyến nghị, định hướng hay phần mở rộng mà template hoặc đề bài không yêu cầu.
- Độ dài là kết quả của nội dung, không phải mục tiêu. Đừng viết dài để cho có.

## 10. Viết như người, không như AI

Đây là yêu cầu quan trọng nhất. Tránh các dấu hiệu sau của văn bản do AI tạo:

- Đừng lạm dụng từ nối khuôn mẫu: "Hơn nữa", "Bên cạnh đó", "Nhìn chung", "Có thể thấy rằng", "Điều đáng chú ý là", "Tóm lại", "Đầu tiên… Tiếp theo… Cuối cùng".
- Đừng lặp mô hình liệt kê ba thành phần ("A, B và C") ở mọi câu.
- Đa dạng độ dài câu và cách mở đầu đoạn. Không để mọi đoạn bắt đầu bằng cùng một kiểu cấu trúc.
- Đừng kết đoạn hay kết chương bằng câu khái quát rỗng nghĩa kiểu "đóng vai trò quan trọng", "là yếu tố then chốt", "mang lại nhiều lợi ích".
- Đừng dùng cấu trúc đối xứng "một mặt… mặt khác…" một cách máy móc, lặp lại.
- Trong phần văn xuôi của đồ án, hạn chế gạch đầu dòng. Trình bày bằng đoạn văn liền mạch; chỉ liệt kê khi nội dung thực sự là một danh sách.
- Cụ thể thay vì chung chung: nêu con số, ví dụ, trường hợp thật thay cho những phát biểu mơ hồ.
- Bỏ các từ tăng cường rỗng nghĩa khi không cần: "rất", "vô cùng", "hết sức".
- Giữ một giọng văn nhất quán từ đầu đến cuối.
- Không bình luận về quá trình viết hay về chính văn bản (ví dụ: "trong phần này tôi sẽ trình bày…").
- Lập luận phải có mạch nối tự nhiên và chính kiến rõ ràng, không chỉ là ghép nối các mẩu thông tin.

## 11. Quy trình làm việc

1. **Đọc và lập kế hoạch:** Đọc template `.tex`, folder dự án (ảnh, dữ liệu, kiến trúc, kết quả các giai đoạn) và tài liệu tham khảo.
2. **Trình mục lục trước (bắt buộc):** Sửa các đầu mục của template cho khớp dự án và dựng **mục lục đầy đủ**. **Gửi mục lục này cho người dùng và chờ xác nhận trước khi viết nội dung.**
3. **Nêu kế hoạch trước mỗi phần (bắt buộc):** Ngay trước khi viết một phần, trình bày ngắn gọn cho người dùng: phần này sẽ viết nội dung gì, dùng hình/bảng/công thức nào, chọn phiên bản giai đoạn nào và vì sao.
4. **Viết:** Soạn phần đó bằng LaTeX, áp dụng các mục 2–10.
5. **Tự rà soát:** Cắt chi tiết thừa; kiểm tra thuật ngữ và ký hiệu nhất quán; rà các "dấu hiệu AI" ở mục 10 và sửa.
6. **Kiểm tra kỹ thuật:** Đối chiếu định dạng/đánh số với template; biên dịch thử và sửa hết lỗi LaTeX.

## 12. Danh mục tự kiểm trước khi hoàn tất

- [ ] Đã trình mục lục cho người dùng và nêu kế hoạch trước mỗi phần.
- [ ] Tiêu đề/đầu mục đã sửa cho khớp dự án; cấp bậc và đánh số vẫn theo template.
- [ ] Mọi hình/bảng/số liệu lấy từ folder dự án; mỗi hình đặt đúng chỗ, được dẫn trong văn và có lý do.
- [ ] Công thức ghi đầy đủ; ký hiệu định nghĩa rõ và nhất quán.
- [ ] Mỗi giai đoạn đã chọn phiên bản tốt nhất kèm giải thích lý do và tiêu chí.
- [ ] Trích dẫn đúng quy cách (`\cite`/`.bib`); tham chiếu chéo dùng `\ref`/`\eqref`.
- [ ] Không còn câu thừa, chi tiết bên lề hay nội dung lặp.
- [ ] Không còn dấu hiệu văn AI (từ nối khuôn mẫu, kết luận rỗng…).
- [ ] LaTeX biên dịch không lỗi; đã xóa hết placeholder và văn bản hướng dẫn của template.

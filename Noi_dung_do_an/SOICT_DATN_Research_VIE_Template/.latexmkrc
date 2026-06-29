# latexmk config for this thesis (biblatex + backend=bibtex).
#
# pdflatex trả về exit code != 0 cho tài liệu này dù biên dịch thành công
# (chỉ có warning: font size 13, biblatex fall-back backend, thiếu csquotes,
#  option '13pt'/'3p' không dùng). latexmk mặc định coi exit != 0 là lỗi và
#  DỪNG trước khi chạy bibtex -> không giải được cross-reference -> "không build được".
#
# '|| true' ép lệnh pdflatex báo thành công để latexmk chạy đủ chuỗi
# pdflatex -> bibtex -> pdflatex -> pdflatex và kết thúc với exit 0.
# Lỗi LaTeX thật (nếu có) vẫn hiện trong panel "LaTeX Compiler" của LaTeX Workshop.

$pdf_mode    = 1;                       # build PDF bằng pdflatex
$bibtex_use  = 2;                       # luôn chạy bibtex (biblatex backend=bibtex)
$max_repeat  = 7;                       # đủ số pass để ổn định cross-reference
$pdflatex    = 'pdflatex -interaction=nonstopmode -synctex=1 -file-line-error %O %S || true';

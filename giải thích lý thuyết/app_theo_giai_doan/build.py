"""Sinh index.html (mở offline bằng trình duyệt) từ content.html (bản dùng cho Artifact).

content.html cố ý KHÔNG có <html>/<head>/<body> vì Artifact tự bọc khi publish.
Bản local cần thêm doctype + meta charset để tiếng Việt không lỗi font khi mở bằng file://.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
content = (HERE / "content.html").read_text(encoding="utf-8")

page = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
{content}
</body>
</html>
"""
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"Đã sinh: {HERE / 'index.html'}")

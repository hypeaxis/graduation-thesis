from __future__ import annotations

from pathlib import Path

from .models import SectionMeta


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "_theory_hub"

SECTIONS = {
    "A-problem-and-data": SectionMeta(
        key="A-problem-and-data",
        label="A. Nền tảng bài toán & dữ liệu",
        theme="mint",
        description="Khung bài toán IDS, flow và cách dữ liệu được biểu diễn.",
    ),
    "B-ft-transformer": SectionMeta(
        key="B-ft-transformer",
        label="B. FT-Transformer",
        theme="sky",
        description="Ba khối lý thuyết cốt lõi của kiến trúc Transformer cho dữ liệu bảng.",
    ),
    "C-preprocessing": SectionMeta(
        key="C-preprocessing",
        label="C. Tiền xử lý",
        theme="amber",
        description="Biến đổi phân phối và lọc bớt đặc trưng trước khi học.",
    ),
    "D-imbalance-handling": SectionMeta(
        key="D-imbalance-handling",
        label="D. Xử lý mất cân bằng",
        theme="rose",
        description="Các cơ chế làm model học tốt hơn với lớp hiếm và ranh giới khó.",
    ),
    "E-transfer-domain-adaptation": SectionMeta(
        key="E-transfer-domain-adaptation",
        label="E. Thích nghi miền",
        theme="violet",
        description="Lệch phân phối, freezing, surgery và các giới hạn khi chuyển miền.",
    ),
    "F-ensemble-and-system": SectionMeta(
        key="F-ensemble-and-system",
        label="F. Ensemble & hệ thống",
        theme="teal",
        description="Cascade, voting, stacking và lý do phải đa dạng hóa mô hình.",
    ),
    "G-hybrid-and-limits": SectionMeta(
        key="G-hybrid-and-limits",
        label="G. Hệ lai & giới hạn",
        theme="slate",
        description="Hệ lai Snort + FTT, hợp nhất cảnh báo và những giới hạn nguyên lý.",
    ),
}

THEME_ACCENTS = {
    "mint": "#1e7f5c",
    "sky": "#1d5f91",
    "amber": "#9a5b00",
    "rose": "#9f3058",
    "violet": "#6946b6",
    "teal": "#0e7c7b",
    "slate": "#344155",
}
"""Tương thích ngược — giữ lệnh cũ `uvicorn live_replay_server:app`.

Toàn bộ logic đã tách thành package `ids_replay/` (kiến trúc SOLID); composition root ở server.py.
"""
from server import app  # noqa: F401

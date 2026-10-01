"""絵を描く部分の見本（友だちが自分の描き方を作るときのひな形）。

AIを使わず、タイプの色で塗った正方形に丸を描いて返すだけ。料金はかからない。
使うときは .env に  DRAW_FUNC=draw_example:draw  と書いてアプリを起動し直す。
受け取る info と返すものの決まりは drawing.py の先頭に書いてある。
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw


def draw(info: dict) -> bytes:
    size = 1024
    img = Image.new("RGB", (size, size), info.get("color", "#888888"))
    d = ImageDraw.Draw(img)
    d.ellipse((262, 262, 762, 762), fill="#fffdf8")
    d.ellipse((400, 450, 450, 500), fill="#2a2340")
    d.ellipse((574, 450, 624, 500), fill="#2a2340")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

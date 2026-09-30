"""AIの絵のまわりにできる白い「紙のふち」を切り取る。

絵本風にすると、AIが絵の外側に紙の余白を描くことがある（2026-09-30に左右の白い帯で発生）。
ふちを切り取ったあと、中央を正方形に切り出して、カードの枠いっぱいに絵が入るようにする。
"""

from __future__ import annotations

import io

from PIL import Image, ImageStat

MAX_TRIM = 0.25     # 1辺につき最大で幅の25%まで切る（絵そのものを削りすぎないため）
BRIGHT = 200        # これより明るい列・行を「紙のふち」の候補にする
FLAT = 18           # 色のばらつき（標準偏差）がこれ以下なら、無地とみなす


def _is_margin(strip: Image.Image) -> bool:
    stat = ImageStat.Stat(strip)
    return min(stat.mean) >= BRIGHT and max(stat.stddev) <= FLAT


def trim_margins(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    left, top, right, bottom = 0, 0, w, h
    while left < w * MAX_TRIM and _is_margin(img.crop((left, 0, left + 1, h))):
        left += 1
    while w - right < w * MAX_TRIM and _is_margin(img.crop((right - 1, 0, right, h))):
        right -= 1
    while top < h * MAX_TRIM and _is_margin(img.crop((0, top, w, top + 1))):
        top += 1
    while h - bottom < h * MAX_TRIM and _is_margin(img.crop((0, bottom - 1, w, bottom))):
        bottom -= 1
    if (left, top, right, bottom) == (0, 0, w, h):
        return data
    # 境目の色が残らないよう、少し内側まで切る
    pad = 4
    img = img.crop((min(left + pad, w // 2), min(top + pad, h // 2), max(right - pad, w // 2), max(bottom - pad, h // 2)))
    # 中央を正方形に切り出して、元の大きさに戻す
    cw, ch = img.size
    side = min(cw, ch)
    img = img.crop(((cw - side) // 2, (ch - side) // 2, (cw - side) // 2 + side, (ch - side) // 2 + side))
    img = img.resize((w, w), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def edge_color(data: bytes) -> str:
    """絵のふち（外側4%）の平均色。万一すき間ができても、そこを絵と同じ色で埋めるために使う。"""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    b = max(1, int(min(w, h) * 0.04))
    strips = [img.crop((0, 0, w, b)), img.crop((0, h - b, w, h)), img.crop((0, 0, b, h)), img.crop((w - b, 0, w, h))]
    means = [ImageStat.Stat(st).mean for st in strips]
    r, g, bl = (round(sum(m[i] for m in means) / 4) for i in range(3))
    return f"#{r:02x}{g:02x}{bl:02x}"

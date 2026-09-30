"""AIの絵のまわりにできる「紙のふち」を切り取る。

絵本風にすると、AIが「紙の上に描いた絵」として、外側に紙の余白を描くことがある。
2026-09-30に2回起きた：
  - 左右が無地の白い帯になった
  - 左右に紙の余白があり、そこへキャラクターの一部（麺）がはみ出していた
    → 「無地の列を削る」やり方では、はみ出しで止まって余白が残った

なので、四隅の色を「紙の色」とみなし、紙の部分と絵の部分の境目（くっきりした直線）を探す。
境目の外側（ふち）にある紙の色の点を、すぐ内側の背景の色で塗りつぶす（切り取らない）。
「余白が出るなら、そこを背景と同じ色に」（ゆーしんの指示）。はみ出したキャラの一部はそのまま残る。
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageChops, ImageStat

MAX_TRIM = 0.25      # 1辺につき最大で幅の25%まで切る（絵そのものを削りすぎないため）
PAPER_BRIGHT = 190   # 四隅がこれより明るいときだけ「紙のふち」があるとみなす
CORNER_SPREAD = 30   # 四隅の色の差がこれ以内なら、同じ紙の色とみなす
NEAR_PAPER = 28      # 紙の色からこの差以内の点を「紙」とみなす
PAPER_RATIO = 0.55   # 境目より外側の列・行が、平均でこの割合以上紙なら「ふち」とみなす
SHARP_DROP = 0.4     # 境目で、紙の割合がこれ以上一気に下がること
EDGE_RATIO = 0.25    # 紙の割合がこれより下がった列・行を、絵の部分の始まり（境目）とみなす


def _corner_colors(img: Image.Image) -> list[tuple[float, ...]]:
    w, h = img.size
    s = max(4, min(w, h) // 40)
    boxes = [(0, 0, s, s), (w - s, 0, w, s), (0, h - s, s, h), (w - s, h - s, w, h)]
    return [tuple(ImageStat.Stat(img.crop(b)).median) for b in boxes]


def _paper_color(img: Image.Image) -> tuple[int, int, int] | None:
    corners = _corner_colors(img)
    if min(min(c) for c in corners) < PAPER_BRIGHT:
        return None
    for i in range(3):
        vals = [c[i] for c in corners]
        if max(vals) - min(vals) > CORNER_SPREAD:
            return None
    return tuple(round(sum(c[i] for c in corners) / 4) for i in range(3))


def trim_margins(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    paper = _paper_color(img)
    if paper is None:
        return data
    w, h = img.size

    # 紙の色との差が小さい点を白（255）、それ以外を黒（0）にした白黒画像
    diff = ImageChops.difference(img, Image.new("RGB", img.size, paper)).convert("L")
    mask = diff.point(lambda v: 255 if v <= NEAR_PAPER else 0)

    def ratio(box: tuple[int, int, int, int]) -> float:
        return ImageStat.Stat(mask.crop(box)).mean[0] / 255

    # 紙のふちは、絵の部分との境目がくっきりした直線になる（その列から先は、ほぼ全部が紙以外）。
    # 背景が無地で明るいだけの絵は、境目がなく、キャラの上下に背景が残るので、そこまで紙以外にならない。
    # この違いで「本当に紙のふちがあるか」を見分け、ある辺だけを削る。
    def cut(n: int, strip) -> int:
        limit = int(n * MAX_TRIM)
        ratios = [ratio(strip(i)) for i in range(limit)]
        for k, r in enumerate(ratios):
            if r < EDGE_RATIO:
                if k == 0:
                    return 0
                # 境目がくっきりしているか（直前の数ピクセルから一気に紙が減るか）。
                # 白くぼかした背景（ビネット）はゆるやかに減るので、ここで外れる。
                before = ratios[max(0, k - 6):k]
                sharp = sum(before) / len(before) - r >= SHARP_DROP
                return k if sharp and sum(ratios[:k]) / k >= PAPER_RATIO else 0
        return 0

    left = cut(w, lambda i: (i, 0, i + 1, h))
    right = w - cut(w, lambda i: (w - 1 - i, 0, w - i, h))
    top = cut(h, lambda i: (0, i, w, i + 1))
    bottom = h - cut(h, lambda i: (0, h - 1 - i, w, h - i))
    if (left, top, right, bottom) == (0, 0, w, h):
        return data

    # 切り取ると、ふちまではみ出して描かれた頭や足まで切れてしまう（2026-09-30に発生）。
    # なので切らずに、ふちの「紙の色の点」だけを、すぐ内側の背景の色で塗りつぶす。
    # 行ごと・列ごとに境目の少し内側の色を使うので、背景の色の変化もそのまま外へ伸びる。
    px = np.asarray(img).astype(np.float32)
    ref = np.array(paper, dtype=np.float32)
    pad, depth, blur = 8, 24, 161

    def smooth(line: np.ndarray) -> np.ndarray:
        """塗る色を行（列）方向に少しぼかす。ぼかさないと横すじ・縦すじが目立つ。"""
        k = np.ones(blur, dtype=np.float32) / blur
        padded = np.pad(line, ((blur // 2, blur // 2), (0, 0)), mode="edge")
        return np.stack([np.convolve(padded[:, c], k, mode="valid") for c in range(3)], axis=1)

    def fill(arr: np.ndarray, band: np.ndarray, color: np.ndarray) -> None:
        is_paper = np.abs(arr - ref).max(axis=2) <= NEAR_PAPER + 12
        m = band & is_paper
        arr[m] = color[m]

    # 上下を先に塗り、そのあと左右を塗る（角は左右の塗りで埋まる）
    if top:
        src = smooth(px[min(top + pad, h - 1):min(top + pad + depth, h), :].mean(axis=0))
        band = np.zeros((h, w), bool); band[:top + 2, :] = True
        fill(px, band, np.broadcast_to(src[None, :, :], px.shape))
    if bottom < h:
        src = smooth(px[max(bottom - pad - depth, 0):max(bottom - pad, 1), :].mean(axis=0))
        band = np.zeros((h, w), bool); band[bottom - 2:, :] = True
        fill(px, band, np.broadcast_to(src[None, :, :], px.shape))
    if left:
        src = smooth(px[:, min(left + pad, w - 1):min(left + pad + depth, w)].mean(axis=1))
        band = np.zeros((h, w), bool); band[:, :left + 2] = True
        fill(px, band, np.broadcast_to(src[:, None, :], px.shape))
    if right < w:
        src = smooth(px[:, max(right - pad - depth, 0):max(right - pad, 1)].mean(axis=1))
        band = np.zeros((h, w), bool); band[:, right - 2:] = True
        fill(px, band, np.broadcast_to(src[:, None, :], px.shape))
    out = np.clip(px, 0, 255)
    buf = io.BytesIO()
    Image.fromarray(out.astype(np.uint8)).save(buf, format="PNG")
    return buf.getvalue()


def edge_color(data: bytes) -> str:
    """絵のふち（外側4%）の平均色。万一すき間ができても、そこを絵と同じ色で埋めるために使う。"""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    b = max(1, int(min(w, h) * 0.04))
    strips = [img.crop((0, 0, w, b)), img.crop((0, h - b, w, h)), img.crop((0, 0, b, h)), img.crop((w - b, 0, w, h))]
    means = [ImageStat.Stat(st).mean for st in strips]
    r, g, bl = (round(sum(m[i] for m in means) / 4) for i in range(3))
    return f"#{r:02x}{g:02x}{bl:02x}"

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
SHARP_DROP = 0.35    # 境目で、紙の割合がこれ以上一気に下がること
SHADOW_NEAR = 70     # 境目の外側では、紙の色からこの差までの色（紙の上の影など）も埋める
CONTENT_MIN = 0.04   # 紙以外の点がこの割合以上ある列・行を「絵の中身がある」とみなす


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
        for k in range(1, len(ratios)):
            # 境目がぼやけている絵もあるので、12ピクセル手前と比べる
            before = ratios[max(0, k - 12):max(1, k - 9)]
            # 境目：直前の数ピクセルから紙の割合が一気に下がるところ。
            # ふちが広いと、上下の行にも左右のふちの紙が混ざるので、「0に近いか」ではなく「一気に下がったか」で見る。
            # 白くぼかした背景（ビネット）はゆるやかに下がるので、ここで外れる。
            if sum(before) / len(before) - ratios[k] >= SHARP_DROP:
                return k if sum(ratios[:k]) / k >= PAPER_RATIO else 0
        return 0

    left = cut(w, lambda i: (i, 0, i + 1, h))
    right = w - cut(w, lambda i: (w - 1 - i, 0, w - i, h))
    top = cut(h, lambda i: (0, i, w, i + 1))
    bottom = h - cut(h, lambda i: (0, h - 1 - i, w, h - i))
    if (left, top, right, bottom) == (0, 0, w, h):
        return data

    # ① 絵の中身がある範囲（ふちからはみ出したキャラの一部も含む）まで切り詰める。
    #    ふちが広い絵を全部塗ると、たてすじの枠のように見えて汚くなったため（2026-09-30）。
    arr = np.asarray(img).astype(np.float32)
    ref = np.array(paper, dtype=np.float32)
    content = np.abs(arr - ref).max(axis=2) > SHADOW_NEAR
    cols = np.where(content.mean(axis=0) >= CONTENT_MIN)[0]
    rows = np.where(content.mean(axis=1) >= CONTENT_MIN)[0]
    if len(cols) == 0 or len(rows) == 0:
        return data
    x0, x1, y0, y1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1
    px = arr[y0:y1, x0:x1].copy()
    ch, cw = px.shape[:2]
    depth, blur, fringe = 24, 161, 60

    def smooth(line: np.ndarray) -> np.ndarray:
        """塗る色を行（列）方向に大きくぼかす。ぼかさないとすじが目立つ。"""
        k = np.ones(blur, dtype=np.float32) / blur
        padded = np.pad(line, ((blur // 2, blur // 2), (0, 0)), mode="edge")
        return np.stack([np.convolve(padded[:, c], k, mode="valid") for c in range(3)], axis=1)

    # ② 切り詰めたあと、角の丸みなどに残った紙の色だけを、すぐ内側の色で塗る
    near = lambda a: np.abs(a - ref).max(axis=2) <= NEAR_PAPER + 12
    for side in ("top", "bottom", "left", "right"):
        if side in ("top", "bottom") and ch > 2 * fringe + depth:
            sl = slice(fringe, fringe + depth) if side == "top" else slice(ch - fringe - depth, ch - fringe)
            src = np.broadcast_to(smooth(px[sl, :].mean(axis=0))[None, :, :], px.shape)
            band = np.zeros((ch, cw), bool)
            band[:fringe] = side == "top"
            if side == "bottom":
                band[ch - fringe:] = True
        elif side in ("left", "right") and cw > 2 * fringe + depth:
            sl = slice(fringe, fringe + depth) if side == "left" else slice(cw - fringe - depth, cw - fringe)
            src = np.broadcast_to(smooth(px[:, sl].mean(axis=1))[:, None, :], px.shape)
            band = np.zeros((ch, cw), bool)
            if side == "left":
                band[:, :fringe] = True
            else:
                band[:, cw - fringe:] = True
        else:
            continue
        m = band & near(px)
        px[m] = src[m]

    # ③ 正方形にする。足りない分は、端の色をなめらかに伸ばして埋める（絵は切らない）
    side_len = max(ch, cw)
    sq = np.zeros((side_len, side_len, 3), np.float32)
    oy, ox = (side_len - ch) // 2, (side_len - cw) // 2
    sq[oy:oy + ch, ox:ox + cw] = px
    if cw < side_len:
        lcol = smooth(px[:, :depth].mean(axis=1)); rcol = smooth(px[:, -depth:].mean(axis=1))
        sq[oy:oy + ch, :ox] = lcol[:, None, :]
        sq[oy:oy + ch, ox + cw:] = rcol[:, None, :]
    if ch < side_len:
        trow = smooth(sq[oy:oy + depth].mean(axis=0)); brow = smooth(sq[oy + ch - depth:oy + ch].mean(axis=0))
        sq[:oy] = trow[None, :, :]
        sq[oy + ch:] = brow[None, :, :]
    out = Image.fromarray(np.clip(sq, 0, 255).astype(np.uint8)).resize((w, w), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
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

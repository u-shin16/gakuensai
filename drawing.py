"""守り神の絵を描く部分（差し替えできるように、ここだけに分けてある。2026-10-01）。

アプリ（app.py）は、絵を描くときに `draw(info)` を1回呼ぶだけ。
友だちが作った描き方に替えるときは、次のどちらかでいい。
  1. このファイルの draw() の中身を書き換える
  2. 別のファイル（例：friend_draw.py）に同じ形の関数を作り、.env に DRAW_FUNC=friend_draw:draw と書く

draw(info) が受け取る info（dict）
  image_prompt  絵の説明（英語）。文章のAIが、性格と好きなものから書いたもの
  monster       守り神の名前（例：ラメハムタ）
  type_code     性格タイプ（例：ESFJ）
  type_name     タイプ名（例：世話焼きさん）
  motif         タイプの雰囲気（英語）
  hue           タイプの色（英語。例：sunny yellow）
  color         タイプの色（#E8B923 など）
  favorite      好きなもの（例：ラーメン）
  style         "cute"（かわいい）か "cool"（かっこいい）

draw(info) が返すもの
  PNG画像のバイト列（正方形。1024×1024くらい）。
  返したあと、アプリ側で白いふちを切って保存する。失敗したら例外を投げれば、お客さんには「絵を描けませんでした」と出る。
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # 単体で読み込まれても .env が効くように

import base64
import json
import logging
import os

from trim import frame_box, has_bright_edges

log = logging.getLogger("drawing")

API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# 絵柄は「絵本風」に固定（2026-09-30にゆーしんが3案から選んだ）。
# つやつやしたAIっぽい絵にも、平たすぎるちゃちな絵にもならないようにする。
STYLES = {
    "cute": ("Warm Japanese picture-book illustration, gouache and colored pencil texture, hand-painted brush strokes, "
             "soft natural shading. CUTE: chibi proportions with a big round head, big round sparkling eyes, "
             "soft rounded shapes, gentle smiling expression"),
    "cool": ("Warm Japanese picture-book illustration, gouache and colored pencil texture, hand-painted brush strokes, "
             "soft natural shading. COOL: a noble, strong guardian beast with tall heroic proportions "
             "(not chibi), sharp confident eyes, a dignified serious expression, dynamic powerful pose, bold silhouette, "
             "deeper and richer colors, dramatic composition. It must not look cute or babyish, no big round eyes"),
}
IMAGE_COMMON = ("Single character, full body, centered, facing the viewer. "
                "Behind the character, a gentle picture-book background scene with a few small props and scenery related to the subject, "
                "in clearly colored medium tones of {hue} (never a white or pale background); not busy, the character stays the clear focus. "
                "The guardian must not look like a human person: it is a creature or a living object. "
                "Full-bleed composition like a full-page spread in a picture book: the background scene is painted all the way to every edge "
                "and continues beyond the frame, no white border, no margin, no paper edge, no inner panel or rounded frame, "
                "no vignette, no fading to white at the edges, not a picture drawn on a sheet of paper. "
                "Absolutely no text, no letters, no numbers, no signature, no stamp, no logo, no brand marks (no sports brand stripes or swooshes), no real team uniforms, no frame. "
                "Not glossy, not 3D, not resembling any existing franchise character. ")

MARGIN_CHECK_PROMPT = (
    "Look only at the outer edges and corners of this square illustration. "
    "Answer margin=true if ANY of these is visible: a white, cream or pale border or margin; an inner panel or frame "
    "(rounded or square) with a different color outside it; edges or corners that fade to white or to a pale wash (vignette); "
    "a paper edge; or the painted scene not reaching all four edges. "
    "Answer margin=false only if the painted scene clearly continues right up to all four edges with no frame."
)
MARGIN_SCHEMA = {"type": "object", "properties": {"margin": {"type": "boolean"}, "where": {"type": "string"}},
                 "required": ["margin", "where"]}


def ai_has_margin(data: bytes) -> bool:
    """絵に余白・枠・白いぼかしがあるかをAIに見て答えさせる（2026-10-01）。
    プログラムの判定では、角の丸い内側の枠や、うっすら明るいふちを見つけられなかったため。"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=TEXT_MODEL,
        contents=[types.Part.from_bytes(data=data, mime_type="image/png"), MARGIN_CHECK_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=MARGIN_SCHEMA, temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    r = json.loads(resp.text)
    if r.get("margin"):
        log.info("余白あり：%s", r.get("where"))
    return bool(r.get("margin"))


RETRY_NOTE = (" IMPORTANT: the previous attempt had a border or pale edges. The background scenery must be painted in "
              "clearly colored medium tones all the way to all four edges and corners: no white, no pale vignette, "
              "no inner panel or frame.")
MAX_IMAGE_TRIES = 3


def image_without_margin(prompt: str, style: str, hue: str) -> str:
    """余白のない絵ができるまで描き直す（最大3回）。ゆーしん「余白は絶対にやめて」（2026-10-01）。
    毎回、プログラムの判定とAIの目視の両方で確かめる。3回とも余白があれば、保存時の zoom_to_clean で切って仕上げる。"""
    uri = ""
    for i in range(MAX_IMAGE_TRIES):
        uri = ai_image(prompt + (RETRY_NOTE if i else ""), style, hue)
        data = base64.b64decode(uri.split(",", 1)[1])
        try:
            margin = has_bright_edges(data) or frame_box(data) is not None or ai_has_margin(data)
        except Exception:
            log.exception("余白の確認に失敗（この絵を使う）")
            return uri
        if not margin:
            if i:
                log.info("描き直して%d回目で余白のない絵になった", i + 1)
            return uri
    log.info("%d回描いても余白が残った（保存時に切って仕上げる）", MAX_IMAGE_TRIES)
    return uri


def ai_image(prompt: str, style: str, hue: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=IMAGE_MODEL,
        # 絵柄の指定は最初と最後の両方に置く（途中の説明に引っぱられて「かわいい」寄りになるのを防ぐ）
        contents=f"{STYLES[style]}. {IMAGE_COMMON.format(hue=hue)}Subject: {prompt}. Style reminder: {STYLES[style]}",
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )
    for part in resp.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            data = part.inline_data.data
            if isinstance(data, str):
                data = base64.b64decode(data)
            mime = part.inline_data.mime_type or "image/png"
            return f"data:{mime};base64," + base64.b64encode(data).decode()
    raise RuntimeError("絵が返ってきませんでした")


def draw(info: dict) -> bytes:
    """今の描き方：Gemini で絵本風に描き、余白があれば描き直す（最大3回）。"""
    uri = image_without_margin(info["image_prompt"], info["style"], info["hue"])
    return base64.b64decode(uri.split(",", 1)[1])

"""学園祭（2026-11-21）の模擬店「質問に答えると、自分だけのモンスターカードができる」の試作。

流れ：
  1. 2択の質問8問に答える → オリジナルの16タイプのどれかに決まる
  2. 好きなものを1つと、絵柄（かわいい／かっこいい）を選ぶ
  3. Geminiが、タイプと好きなものを混ぜた守り神モンスターの名前・あるある・恋愛や金運などの言葉を作り、絵を描く
  5. カードのQRコードから、その人だけの結果ページ（/r/<ランダムな文字列>）で詳しい占いと相性を見られる
     URLは連番にしない（番号を変えるだけで他人の結果が見えないようにするため）
  6. 2人のカード番号から相性を出せる

GEMINI_API_KEY が無いときは「お試しモード」で、ダミーの中身と仮の絵を返す。

作ったカードと相性を見た記録は data/log.jsonl に残す。
タイプ・好きなもの・日時だけで、名前などの個人情報は取らない。
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import re
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import qrcode
import qrcode.image.svg
from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session

from trim import edge_color, frame_box, has_bright_edges, trim_margins, zoom_to_clean
from types_data import ADVICE, AXIS_WORDS, CREATURES, QUESTIONS, TYPES, axis_profile, best_partners, decide_type, match, rival

load_dotenv()

app = Flask(__name__)
# 管理者のログイン状態をクッキーに入れるための鍵。本番では .env の SECRET_KEY を使う
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("PUBLIC_BASE_URL", "").startswith("https"))

# 管理者画面にログインできるGoogleアカウント（.env の ADMIN_EMAILS にカンマ区切り）。
# 登録したアカウントだけが入れる（ゆーしんの決まり、2026-10-01）。登録の方法はミーティングで決める
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}

API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

DATA_DIR = Path(__file__).parent / "data"
LOG_PATH = DATA_DIR / "log.jsonl"
RESULT_DIR = DATA_DIR / "results"   # 結果ページ用。1人1ファイル（JSON＋絵）
# QRコードに入れるURLの頭。未設定なら開いているアドレスを使う（スマホで試すときはLANのアドレスで開く）
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16}$")
_lock = threading.Lock()

# 実在キャラ・有名作品は作らない（著作権）。AIの判定より先に、ここで確実に弾く。
BLOCKED_WORDS = [
    "ピカチュウ", "ポケモン", "ポケットモンスター", "マリオ", "ルイージ", "カービィ", "ゼルダ",
    "ドラえもん", "アンパンマン", "ミッキー", "ミニー", "ディズニー", "キティ", "サンリオ",
    "ちいかわ", "ハチワレ", "スヌーピー", "ドラゴンボール", "悟空", "ワンピース", "ルフィ",
    "鬼滅", "炭治郎", "ナルト", "呪術", "コナン", "しんちゃん", "ドラクエ", "ガンダム",
    "ゴジラ", "ウルトラマン", "仮面ライダー", "プリキュア",
]

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

CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "allowed": {"type": "boolean"},
        "reason": {"type": "string"},
        "monster": {"type": "string"},
        "message": {"type": "string"},
        "love": {"type": "string"},
        "friend": {"type": "string"},
        "study": {"type": "string"},
        "money": {"type": "string"},
        "image_prompt": {"type": "string"},
    },
    "required": ["allowed", "reason", "monster", "message", "love", "friend", "study", "money", "image_prompt"],
}

CARD_PROMPT = """あなたは学園祭の模擬店で、お客さんの性格診断の結果と好きなものから、
その人だけの診断カードを書く係です。カードには、その人を守るオリジナルモンスター（守り神）が描かれます。
お客さんは小学生から大人まで。


性格タイプ：{type_name}（{type_desc}）
強み：{strong}／弱点：{weak}
この人だけの傾き：{profile}
（同じタイプの人はたくさんいる。「少し」の軸は反対の面も持っている人なので、そのギャップを文に生かして、この人だけの結果にする）
属性：{element}
好きなもの：「{favorite}」
絵柄：{style}

好きなものが次にあたるときは allowed=false にして、reason に子どもにも分かるやさしい言葉で
「好きなものをちがう言い方にしてね」と伝える（例も1つ添える）。
- 実在するアニメ・ゲーム・漫画のキャラクターや作品名
- 実在する有名人・政治家など特定の人物
- 暴力・性的・差別・いじめにつながる内容
それ以外は allowed=true で reason は空文字。

allowed=true のとき：
- monster：性格と好きなものを混ぜた、この人の守り神モンスターの名前。カタカナ中心で8文字以内。
  次の名前はもう使われているので、同じ名前・よく似た名前にしない：{used_names}
- message：守り神からこの人への「ひとこと」。カードに大きく載る。次の決まりを必ず守る。
  - 2文で書く。1文目でこの人のいいところを1つほめ、2文目では、そのいいところが好きなもの「{favorite}」の場面でどう活きるかを言う。
    1文目と2文目は必ず意味がつながること。2文目だけ別の話（「〜を見に行こう」「一緒に〜しよう」など）にしない
  - 形の例（中身は写さない）：「〇〇できるところが、きみのいいところだね。その力があれば、△△でもきっと〇〇できるよ。」
  - 45文字以内（句読点も数える）
  - 小学生が読んでも意味がすぐ分かる、ふつうの話し言葉の日本語にする。声に出して読んで不自然な文にしない
  - たとえ話・詩的な言い回しは使わない（「心の〇〇」「〇〇の世界」「〇〇を奏でる」「輝き」など）
  - 一人称は「ぼく」。相手は「きみ」。命令や説教にしない。「見守っている」「そばにいる」「大好き」は使わない
- love（恋愛）・friend（友情）・study（勉強・仕事）・money（お金）：占いの結果の文。実在の占い（動物キャラ占い・星座占いなど）と同じ書き方にする。
  - です・ます調でそろえる。「◎」「〜ね」「〜よ」「〜してみて」「〜しよう」は使わない
  - 2文で書く。1文目は25文字以内、2文目は25文字以内
  - 1文目：この項目での傾向を言い切る。「〇〇な傾向があります」「〇〇です」「ついつい〇〇してしまうことも」のどれかの形
  - 2文目：命令にせず、「〇〇すると、〇〇でしょう」「〇〇となら、〇〇できます」のように、条件と良い結果で書く
  - 「少し」の軸がある人は、1文目か2文目にその反対の面（ギャップ）を入れて、この人だけの内容にする
  - 好きなものは入れない。項目の話題から外れない（勉強・仕事は勉強か仕事の場面のまま）
  - 下はこのタイプの傾向の例。そのまま写さない
    恋愛「{love}」／友情「{friend}」／勉強・仕事「{study}」／お金「{money}」
- image_prompt：絵を描くための英語の説明。守り神のもとになるものは「{creature}」（生き物とは限らない。物・植物・自然・精霊などのこともある）。その姿に、性格の雰囲気「{motif}」と、好きなもの「{favorite}」の要素を目に見える形で混ぜたオリジナルの守り神1体。
  もとになるものは、持ち物ではなく体そのものの形にする（例：ちょうちんなら、体がちょうちんでできている）。ふつうの人間の姿にはしない。
  ドラゴン・トカゲ・ヘビの姿にはしない（好きなものがそれ自体の場合だけ例外）。既存キャラに似せない。文字は入れない
  絵柄が「かっこいい」なら、強くて凛々しい姿（ちびキャラ・赤ちゃんっぽい姿にしない）として書く。「かわいい」なら、まるっこくて愛らしい姿として書く
"""


def read_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    return [json.loads(l) for l in LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_log(entry: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    entry["at"] = datetime.now().isoformat(timespec="seconds")
    with _lock, LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def blocked(text: str) -> bool:
    return any(w.lower() in text.lower() for w in BLOCKED_WORDS)


def ai_card(code: str, favorite: str, style: str, profile: list[str], used_names: list[str]) -> dict:
    t = TYPES[code]
    love, friend, study, money = ADVICE[code]
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    prompt = CARD_PROMPT.format(
        type_name=t["name"], type_desc=t["desc"], strong=t["strong"], weak=t["weak"],
        element=t["element"], favorite=favorite, motif=t["motif"], creature=random.choice(CREATURES),
        love=love, friend=friend, study=study, money=money,
        profile="、".join(profile), used_names="、".join(used_names) or "（まだなし）",
        style="かわいい" if style == "cute" else "かっこいい",
    )
    resp = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CARD_SCHEMA,
            temperature=1.0,
            # 考える時間を切る。入れたままだと文章だけで約10秒かかり、行列が止まる（2026-09-30に実測）
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return json.loads(resp.text)


MESSAGE_PROMPT = """あなたは、ある人を守る守り神です。その人にカードで渡す「ひとこと」を書きます。
読むのは小学生から大人まで。

その人の性格：{type_name}（{type_desc}）
いいところ：{strong}
この人だけの傾き：{profile}
好きなもの：「{favorite}」

決まり：
- 2文で書く。1文目でいいところを1つ、具体的にほめる。2文目では、そのいいところが「{favorite}」の場面でどう活きるかを書く
- 1文目と2文目の意味が、読んだ人が「なるほど」と思えるほど自然につながること。つながりが弱い組み合わせ（例：人の気持ちが分かる → 電車の乗り換えが上手）は使わない
- 好きなもの「{favorite}」は、その言葉をそのまま文に入れる（「一杯」「あれ」などに言い換えない）
- ほめる中身は具体的にする（「ステキなもの」「いろいろ」のようなぼんやりした言葉は使わない）
- 合わせて45文字以内（句読点も数える）
- 一人称は「ぼく」、相手は「きみ」。やさしい話し言葉。命令や説教、たとえ話、詩的な言い回しは使わない
- 「見守っている」「そばにいる」「大好き」は使わない
- 書いたあと、声に出して読んで不自然なところがないか確かめ、あれば直してから答える

ひとことの文だけを答える（かぎかっこは付けない）。"""


PROOF_PROMPT = """次の文は、守り神が小学生から大人までの人に渡すカードに書く「ひとこと」です。
好きなもの：「{favorite}」
文：「{text}」

次の点を1つずつ確かめる。
1. 日本語として自然か（助詞・語順・言い回しがおかしくないか。声に出して読んで引っかからないか）
2. 1文目と2文目の意味が自然につながっているか
3. 好きなもの「{favorite}」がそのままの言葉で入っていて、使い方が自然か
4. 何のことか分からない言葉やぼんやりした言葉（「ステキなもの」「一杯」など）がないか
5. 45文字以内か。一人称「ぼく」、相手「きみ」、命令・説教・たとえ話がないか

1つでも問題があれば、意味を保ったまま、小学生でもすぐ分かる自然な日本語に書き直す。問題がなければそのまま返す。"""

PROOF_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}, "problem": {"type": "string"}, "text": {"type": "string"}},
    "required": ["ok", "problem", "text"],
}


def proofread(text: str, favorite: str) -> str:
    """ひとことを別の係がチェックして、不自然なら直す（2026-09-30、ゆーしん「絶対に変な日本語にならないように」）。"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=TEXT_MODEL,
        contents=PROOF_PROMPT.format(text=text, favorite=favorite),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PROOF_SCHEMA,
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        ),
    )
    r = json.loads(resp.text)
    if not r.get("ok"):
        app.logger.info("ひとことを直した：%s → %s（%s）", text, r.get("text"), r.get("problem"))
    return "".join((r.get("text") or text).split()).strip("「」")


def ai_message(code: str, favorite: str, profile: list[str]) -> str:
    """守り神のひとことだけを、考える時間つきで作る。1文目と2文目のつながりを良くするため（2026-09-30）。"""
    from google import genai
    from google.genai import types

    t = TYPES[code]
    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=TEXT_MODEL,
        contents=MESSAGE_PROMPT.format(type_name=t["name"], type_desc=t["desc"], strong=t["strong"],
                                       profile="、".join(profile), favorite=favorite),
        config=types.GenerateContentConfig(
            temperature=0.9,
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        ),
    )
    draft = "".join((resp.text or "").split()).strip("「」")  # 改行や空白が入ることがあるので詰める
    return proofread(draft, favorite)


EXTEND_PROMPT = ("Edit this illustration: the background must fill the whole square to every edge. "
                 "Repaint every white, cream, or very pale area near the edges and corners (borders, paper margins, inner frames, "
                 "white vignettes, fading to white) with clearly colored background scenery in medium tones of {hue}, "
                 "in the same painting style. Keep the character exactly the same, same size and position. No text.")


def extend_background(data: bytes, mime: str, hue: str) -> bytes:
    """ふちや白い四隅が出た絵を、AIに背景を端まで描き足してもらう（2026-09-30）。"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[types.Part.from_bytes(data=data, mime_type=mime), EXTEND_PROMPT.format(hue=hue)],
        config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")),
    )
    for part in resp.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            d = part.inline_data.data
            return base64.b64decode(d) if isinstance(d, str) else d
    return data


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
        app.logger.info("余白あり：%s", r.get("where"))
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
            app.logger.exception("余白の確認に失敗（この絵を使う）")
            return uri
        if not margin:
            if i:
                app.logger.info("描き直して%d回目で余白のない絵になった", i + 1)
            return uri
    app.logger.info("%d回描いても余白が残った（保存時に切って仕上げる）", MAX_IMAGE_TRIES)
    return uri


def fill_to_edges(image_uri: str, hue: str) -> str:
    """余白を絶対に出さない（ゆーしんの指示）。
    ① 紙のふちや白い四隅があれば、AIに背景を端まで描き足してもらう（ふちの線がある絵はこれでほぼ消える）
    ② それでも残ったふちは、保存するときに zoom_to_clean が中心に向かって少し拡大して切る"""
    header, b64 = image_uri.split(",", 1)
    data = base64.b64decode(b64)
    if not (has_bright_edges(data) or trim_margins(data) != data):
        return image_uri
    try:
        data = extend_background(data, header.split(":")[1].split(";")[0], hue)
        app.logger.info("余白があったので、背景を描き足した（残り：白い四隅=%s）", has_bright_edges(data))
    except Exception:
        app.logger.exception("背景の描き足しに失敗（元の絵のまま、保存時の処理で埋める）")
        return image_uri
    return "data:image/png;base64," + base64.b64encode(data).decode()


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


def save_result(result: dict, image_data_uri: str) -> str:
    """結果と絵を保存して、推測されないトークンを返す。"""
    token = secrets.token_urlsafe(12)  # 16文字
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    header, b64 = image_data_uri.split(",", 1)
    ext = "svg" if "svg" in header else "png"
    raw = base64.b64decode(b64)
    if ext == "png":
        # 描き足しても残った紙のふち・白い四隅は、中心に向かって少し拡大して切る（塗らない。塗ると跡が見えたため）
        raw = zoom_to_clean(raw)
    (RESULT_DIR / f"{token}.{ext}").write_bytes(raw)
    art_bg = edge_color(raw) if ext == "png" else ""
    result = {**result, "image_file": f"{token}.{ext}", "art_bg": art_bg, "created_at": datetime.now().isoformat(timespec="seconds")}
    (RESULT_DIR / f"{token}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return token


def used_monster_names() -> list[str]:
    """これまでに作った守り神の名前（古い順）。"""
    if not RESULT_DIR.exists():
        return []
    rows = []
    for path in RESULT_DIR.glob("*.json"):
        try:
            r = json.loads(path.read_text(encoding="utf-8"))
            rows.append((r.get("created_at", ""), r.get("monster", "")))
        except ValueError:
            continue
    return [name for _, name in sorted(rows) if name]


def load_result(token: str) -> dict:
    if not TOKEN_RE.match(token):
        abort(404)
    path = RESULT_DIR / f"{token}.json"
    if not path.exists():
        abort(404)
    return json.loads(path.read_text(encoding="utf-8"))


def qr_svg(url: str) -> str:
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=1)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


def result_payload(r: dict, token: str) -> dict:
    """保存した結果に、タイプの説明など固定の中身を足して返す。"""
    t = TYPES[r["type_code"]]
    return {
        **r,
        "token": token,
        "type_name": t["name"],
        "type_kana": t["kana"],
        "color": t["color"],
        "type_desc": t["desc"],
        "aruaru": t["aruaru"],
        "axes": [AXIS_WORDS[c] for c in r["type_code"]],
        "strong": t["strong"],
        "weak": t["weak"],
        "partners": best_partners(r["type_code"]),
        "rival": rival(r["type_code"]),
        "image": f"/img/{r['image_file']}",
    }


def ai_error_reason(e: Exception, what: str) -> str:
    """AIのエラーを、お店で読んで分かる言葉にする。
    月の利用上限（429 RESOURCE_EXHAUSTED）は、もう一度押しても直らないのでスタッフに知らせる（2026-10-01に発生）。"""
    text = str(e)
    if "RESOURCE_EXHAUSTED" in text or "spending cap" in text:
        return f"{what}。AIの今月の利用上限に達しています（スタッフの人へ：ai.studio/spend で上限を確認してください）"
    return f"{what}（{type(e).__name__}）。もう一度試してね"


@app.route("/")
def index():
    questions = [{"q": q["q"], "a": q["a"], "b": q["b"]} for q in QUESTIONS]
    return render_template("index.html", questions=questions)


@app.post("/api/card")
def make_card():
    body = request.get_json(silent=True) or {}
    if str(body.get("shop", "")).strip() != shop_code():
        return jsonify({"ok": False, "reason": "お店のあいことばがちがうよ。お店の人に聞いてね", "shop": True}), 403
    answers = body.get("answers") or []
    favorite = str(body.get("favorite", "")).strip()
    style = body.get("style") if body.get("style") in STYLES else "cute"

    if len(answers) != len(QUESTIONS) or any(
        pick not in (q["a"][1], q["b"][1]) for q, pick in zip(QUESTIONS, answers)
    ):
        return jsonify({"ok": False, "reason": "質問にぜんぶ答えてね"}), 400
    if not favorite:
        return jsonify({"ok": False, "reason": "好きなものを入れてね"}), 400
    if len(favorite) > 20:
        return jsonify({"ok": False, "reason": "好きなものは20文字までにしてね"}), 400
    if blocked(favorite):
        write_log({"event": "refused", "favorite": favorite, "by": "list"})
        return jsonify({"ok": False, "reason": "ごめんね、アニメやゲームにいるキャラクターはカードにできないんだ。"
                                           "ほかの好きなものを入れてみて！（例：カレー、ねこ、サッカー）"})

    if not API_KEY:
        return jsonify({"ok": False, "reason": "Geminiのキーが入っていないので、カードを作れません（スタッフの人へ：.env を確認してください）"}), 500
    code = decide_type(answers)
    t = TYPES[code]
    profile = axis_profile(answers)
    used = used_monster_names()
    pool = ThreadPoolExecutor(max_workers=2)
    # 守り神のひとこと（作る→チェックして直す、で約10秒）は、ほかに頼らないので最初に始めておく。
    # 文章→絵（合わせて約10秒）と並行して進むので、待ち時間は増えない。
    f_msg = pool.submit(ai_message, code, favorite, profile)
    try:
        try:
            card = ai_card(code, favorite, style, profile, used[-150:])
            # 守り神の名前がほかの人とかぶったら、1回だけ作り直す（人とかぶらないことを一番大事にする）
            if card.get("allowed") and card.get("monster") in used:
                card = ai_card(code, favorite, style, profile, used[-150:] + [card["monster"]])
        except Exception as e:
            app.logger.exception("カードの中身の生成に失敗")
            return jsonify({"ok": False, "reason": ai_error_reason(e, "カードを作れませんでした")}), 502

        if not card.get("allowed"):
            write_log({"event": "refused", "favorite": favorite, "by": "ai"})
            return jsonify({"ok": False, "reason": card.get("reason") or "その好きなものはカードにできないんだ。ほかのものにしてね"})

        try:
            image = image_without_margin(card["image_prompt"], style, t["hue"])
        except Exception as e:
            app.logger.exception("絵の生成に失敗")
            return jsonify({"ok": False, "reason": ai_error_reason(e, "絵を描けませんでした")}), 502

        try:
            card["message"] = f_msg.result() or card["message"]
        except Exception:
            app.logger.exception("ひとことの作成に失敗（最初の文章の係が書いた文を使う）")
    finally:
        pool.shutdown(wait=False)

    with _lock:
        serial = sum(1 for r in read_log() if r["event"] == "card") + 1
    result = {
        "serial": serial, "type_code": code, "favorite": favorite, "style": style,
        **{k: card[k] for k in ("monster", "message", "love", "friend", "study", "money")},
    }
    token = save_result(result, image)
    write_log({"event": "card", "serial": serial, "token": token, "type": code, "favorite": favorite,
               "style": style})
    url = f"{PUBLIC_BASE_URL or request.host_url.rstrip('/')}/r/{token}"
    return jsonify({"ok": True, **result_payload(load_result(token), token), "url": url, "qr": qr_svg(url)})


# ===== 守り神の広場（2026-10-01） =====
# 店の画面（まずはこのパソコン）に広場を映し、結果ページで「あいことば」を入れた人の守り神が現れて歩き回る。
# あいことばは広場の画面に大きく出す（店の前にいる人だけが入れられるようにするため）。
PLAZA_PATH = DATA_DIR / "plaza.json"
# 入った守り神は全員ずっと広場に残る（ゆーしん「1つの大きい広場に全員がたまる」2026-10-01）。
# 数が増えたら、広場の画面のほうで守り神を小さくして全員を収める。


def load_plaza() -> dict:
    try:
        return json.loads(PLAZA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"code": "", "members": []}


def save_plaza(p: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    PLAZA_PATH.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")


def plaza_code(p: dict) -> str:
    if not p.get("code"):
        p["code"] = f"{secrets.randbelow(10000):04d}"
        save_plaza(p)
    return p["code"]


@app.get("/plaza")
def plaza_page():
    with _lock:
        code = plaza_code(load_plaza())
    return render_template("plaza.html", code=code)


# ===== お店のあいことば（2026-10-01） =====
# 本番に置くと、URLを知っている人ならだれでもカードを作れてしまい、AI代がゆーしんに請求される。
# チケットの仕組みができるまでは、お店で教える4けたの「お店のあいことば」がないとカードを作れないようにする。
SETTINGS_PATH = DATA_DIR / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def shop_code() -> str:
    st = load_settings()
    if not st.get("shop_code"):
        st["shop_code"] = f"{secrets.randbelow(10000):04d}"
        DATA_DIR.mkdir(exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return st["shop_code"]


@app.post("/api/shop/check")
def shop_check():
    """診断を始める前に、お店のあいことばが合っているかを確かめる。"""
    ok = str((request.get_json(silent=True) or {}).get("code", "")).strip() == shop_code()
    return jsonify({"ok": ok})


@app.post("/api/shop/newcode")
def shop_newcode():
    staff_only()
    with _lock:
        st = load_settings()
        st["shop_code"] = ""
        SETTINGS_PATH.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        code = shop_code()
    return jsonify({"ok": True, "code": code})


@app.get("/admin")
def admin_home():
    """管理者画面の入口。お客さんの画面とは分ける（2026-10-01）。
    いまは「アプリを動かしているパソコンからだけ開ける」で守る。Googleログインは、管理者の決め方が決まってから付ける。"""
    staff_only()
    p = load_plaza()
    cards = sum(1 for _ in RESULT_DIR.glob("*.png")) if RESULT_DIR.exists() else 0  # ダミーの仮の絵（svg）は数えない
    return render_template("admin/home.html", code=p.get("code", ""), plaza=len(p.get("members", [])), cards=cards,
                           shop=shop_code(), email=session.get("admin_email", ""))


@app.get("/plaza/admin")
@app.get("/characters")
def old_admin_urls():
    """前のアドレスから、管理者画面の新しいアドレスへ案内する。"""
    return redirect("/admin/plaza" if request.path.startswith("/plaza") else "/admin/characters")


def is_admin() -> bool:
    """管理者として入れるか。
    ① 登録したGoogleアカウントでログインしている
    ② または、このパソコンで直接動かしている（手元での開発用。Nginxを通ると X-Forwarded-For が付くので本番では効かない）"""
    if session.get("admin_email") in ADMIN_EMAILS:
        return True
    return request.remote_addr in ("127.0.0.1", "::1") and not request.headers.get("X-Forwarded-For")


def staff_only() -> None:
    """管理者画面・管理用の操作の入口。入れないときは、画面ならログインへ、操作なら403。"""
    if is_admin():
        return
    if request.method == "GET" and not request.path.startswith("/api/"):
        abort(redirect("/admin/login"))
    abort(403)


@app.get("/admin/login")
def admin_login():
    return render_template("admin/login.html", client_id=GOOGLE_CLIENT_ID, error=request.args.get("error", ""))


@app.post("/admin/login")
def admin_login_post():
    """Googleのログインボタンから受け取ったIDトークンを確かめ、登録したアカウントなら管理者として入れる。"""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    if not GOOGLE_CLIENT_ID:
        return redirect("/admin/login?error=setup")
    try:
        info = id_token.verify_oauth2_token(request.form.get("credential", ""), google_requests.Request(), GOOGLE_CLIENT_ID)
    except ValueError:
        return redirect("/admin/login?error=invalid")
    email = (info.get("email") or "").lower()
    if not info.get("email_verified") or email not in ADMIN_EMAILS:
        write_log({"event": "admin_denied"})
        return redirect("/admin/login?error=denied")
    session.clear()
    session["admin_email"] = email
    return redirect("/admin")


@app.get("/admin/logout")
def admin_logout():
    session.pop("admin_email", None)
    return redirect("/admin/login")


@app.get("/admin/plaza")
def plaza_admin():
    """広場の管理画面（スタッフ用）。あいことば・広場にいる守り神の一覧・広場から出す。"""
    staff_only()
    with _lock:
        code = plaza_code(load_plaza())
    return render_template("admin/plaza.html", code=code)


@app.post("/api/plaza/kick")
def plaza_kick():
    """管理画面から、守り神を広場から出す。all=true なら全員。"""
    staff_only()
    body = request.get_json(silent=True) or {}
    with _lock:
        p = load_plaza()
        before = len(p["members"])
        if body.get("all"):
            p["members"] = []
        else:
            p["members"] = [m for m in p["members"] if m["token"] != body.get("token")]
        save_plaza(p)
    return jsonify({"ok": True, "removed": before - len(p["members"])})


@app.post("/api/plaza/leave")
def plaza_leave():
    """結果ページから、自分の守り神を広場から出す。トークンは推測できないので、本人だけが出せる。"""
    token = str((request.get_json(silent=True) or {}).get("token", ""))
    load_result(token)  # 無いトークンは404
    with _lock:
        p = load_plaza()
        p["members"] = [m for m in p["members"] if m["token"] != token]
        save_plaza(p)
    return jsonify({"ok": True})


@app.post("/api/plaza/newcode")
def plaza_newcode():
    """あいことばを変える（管理画面から。スタッフ用）。"""
    staff_only()
    with _lock:
        p = load_plaza()
        p["code"] = ""
        code = plaza_code(p)
    return jsonify({"ok": True, "code": code})


@app.post("/api/plaza/join")
def plaza_join():
    body = request.get_json(silent=True) or {}
    token = str(body.get("token", ""))
    code = str(body.get("code", "")).strip()
    r = load_result(token)  # 無いトークンは404
    with _lock:
        p = load_plaza()
        if code != plaza_code(p):
            return jsonify({"ok": False, "reason": "あいことばがちがうよ。広場の画面に出ている4けたの数字を入れてね"}), 400
        if any(m["token"] == token for m in p["members"]):
            return jsonify({"ok": True, "already": True})
        p["members"].append({"token": token, "joined_at": datetime.now().isoformat(timespec="seconds")})
        save_plaza(p)
    write_log({"event": "plaza", "serial": r.get("serial")})
    return jsonify({"ok": True})


@app.get("/api/plaza")
def plaza_members():
    """広場にいる守り神（入った全員）。映すのは絵・名前・番号・タイプだけ。"""
    p = load_plaza()
    out = []
    for m in p["members"]:
        path = RESULT_DIR / f"{m['token']}.json"
        if not path.exists():
            continue
        r = json.loads(path.read_text(encoding="utf-8"))
        t = TYPES.get(r.get("type_code"), {})
        out.append({"id": m["token"], "serial": r.get("serial"), "monster": r.get("monster", ""),
                    "type_name": t.get("name", ""), "color": t.get("color", "#888888"),
                    "image": f"/img/{r['image_file']}", "joined_at": m["joined_at"]})
    return jsonify({"members": out, "total": len(p["members"]), "code": p.get("code", "")})


@app.get("/admin/characters")
def characters():
    """これまでに作った守り神の一覧（スタッフ・ゆーしんの確認用）。
    ダミー機能は2026-10-01に消した。それまでにダミーで作った仮の絵（svg）は出さない。"""
    staff_only()  # 好きなものが出るので、このパソコンからだけ開ける
    show_dummy = False
    rows = []
    if RESULT_DIR.exists():
        for path in RESULT_DIR.glob("*.json"):
            try:
                r = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            is_dummy = r.get("image_file", "").endswith(".svg")
            if is_dummy and not show_dummy:
                continue
            t = TYPES.get(r.get("type_code"), {})
            rows.append({
                "token": path.stem,
                "serial": r.get("serial", 0),
                "monster": r.get("monster", ""),
                "type_name": t.get("name", ""),
                "color": t.get("color", "#888888"),
                "style": "かっこいい" if r.get("style") == "cool" else "かわいい",
                "favorite": r.get("favorite", ""),
                "message": r.get("message", ""),
                "created_at": r.get("created_at", "")[:16].replace("T", " "),
                "image": f"/img/{r['image_file']}",
                "dummy": is_dummy,
            })
    rows.sort(key=lambda x: x["serial"], reverse=True)
    return render_template("admin/characters.html", rows=rows, show_dummy=show_dummy)


@app.get("/r/<token>")
def result_page(token: str):
    """カードのQRコードから開く、その人だけの結果ページ。"""
    in_plaza = any(m["token"] == token for m in load_plaza().get("members", []))
    return render_template("result.html", r=result_payload(load_result(token), token), in_plaza=in_plaza)


@app.get("/img/<name>")
def result_image(name: str):
    if not re.match(r"^[A-Za-z0-9_-]{16}\.(png|svg)$", name):
        abort(404)
    return send_from_directory(RESULT_DIR, name, max_age=86400)


@app.post("/api/match")
def match_cards():
    """2枚のカード番号から相性を出す。家族や友だちで見せ合う用。"""
    body = request.get_json(silent=True) or {}
    cards = {r["serial"]: r for r in read_log() if r["event"] == "card"}
    try:
        a, b = cards[int(body.get("a"))], cards[int(body.get("b"))]
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "reason": "そのカード番号は見つからないよ"}), 404
    if a["serial"] == b["serial"]:
        return jsonify({"ok": False, "reason": "ちがうカードの番号を入れてね"}), 400
    m = match(a["type"], b["type"])
    write_log({"event": "match", "a": a["serial"], "b": b["serial"], "score": m["score"]})
    return jsonify({"ok": True, "a": TYPES[a["type"]]["name"], "b": TYPES[b["type"]]["name"], **m})


@app.get("/api/stats")
def stats():
    """試してもらった結果のまとめ。お試しモードで作ったカードは数えない。"""
    staff_only()
    rows = read_log()
    return jsonify({
        "cards": sum(1 for r in rows if r["event"] == "card" and not r.get("mock")),  # 2026-10-01まではダミーで作った分に mock が付いている
        "refused": sum(1 for r in rows if r["event"] == "refused"),
        "matches": sum(1 for r in rows if r["event"] == "match"),
    })


if __name__ == "__main__":
    print(f"AI：{TEXT_MODEL} / {IMAGE_MODEL}" if API_KEY else "Geminiのキーがありません（.env を確認）")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8120)), debug=False)

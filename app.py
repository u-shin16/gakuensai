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
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import qrcode
import qrcode.image.svg
from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from trim import edge_color, trim_margins
from types_data import ADVICE, AXIS_WORDS, CREATURES, QUESTIONS, TYPES, axis_profile, best_partners, decide_type, match, rival

load_dotenv()

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

DATA_DIR_EARLY = Path(__file__).parent / "data"
MODE_PATH = DATA_DIR_EARLY / "mode.json"


def is_mock() -> bool:
    """ダミーモード（AIを使わない・0円）か。キーが無ければ必ずダミー。
    実戦モード（Geminiを使う・1枚約6円）は画面の切り替えで選ぶ。既定はダミー。"""
    if not API_KEY or os.environ.get("MOCK") == "1":
        return True
    try:
        return json.loads(MODE_PATH.read_text(encoding="utf-8")).get("mode") != "real"
    except (FileNotFoundError, ValueError):
        return True

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
             "visible paper grain, soft natural shading. CUTE: chibi proportions with a big round head, big round sparkling eyes, "
             "soft rounded shapes, gentle smiling expression"),
    "cool": ("Warm Japanese picture-book illustration, gouache and colored pencil texture, hand-painted brush strokes, "
             "visible paper grain, soft natural shading. COOL: a noble, strong guardian beast with tall heroic proportions "
             "(not chibi), sharp confident eyes, a dignified serious expression, dynamic powerful pose, bold silhouette, "
             "deeper and richer colors, dramatic composition. It must not look cute or babyish, no big round eyes"),
}
IMAGE_COMMON = ("Single character, full body, centered, facing the viewer. "
                "Behind the character, a gentle picture-book background scene with a few small props and scenery related to the subject, "
                "in soft tones of {hue}; not busy, the character stays the clear focus. "
                "Full-bleed: the painting fills the whole square edge to edge, no white border, no margin, no paper edge, "
                "no vignette, no fading to white at the edges, not a picture drawn on a sheet of paper. "
                "Absolutely no text, no letters, no numbers, no signature, no stamp, no logo, no frame. "
                "Not glossy, not 3D, not resembling any existing franchise character. ")

CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "allowed": {"type": "boolean"},
        "reason": {"type": "string"},
        "monster": {"type": "string"},
        "catch": {"type": "string"},
        "message": {"type": "string"},
        "love": {"type": "string"},
        "friend": {"type": "string"},
        "study": {"type": "string"},
        "money": {"type": "string"},
        "image_prompt": {"type": "string"},
    },
    "required": ["allowed", "reason", "monster", "catch", "message", "love", "friend", "study", "money", "image_prompt"],
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
- catch：この人の「あるある」を1文で（40文字以内）。好きなものを自然に混ぜ、大人が読んでも「わかる、当たってる」と思える内容にする。悪口にしない
- message：守り神からこの人への「ひとこと」。カードに大きく載る。次の決まりを必ず守る。
  - 形は「（この人のいいところを1つ、具体的にほめる）＋（好きなもの「{favorite}」にからめた、次にやってみたいこと）」の2文
  - 40文字以内（句読点も数える）
  - ほめ方は「すごいね」に頼らず、「〇〇できるのは、きみのいいところだね」「〇〇なきみに、ぼくはいつも助けられているよ」など言い方を変える
  - 小学生が読んでも意味がすぐ分かる、ふつうの話し言葉の日本語にする。声に出して読んで不自然な文にしない
  - たとえ話・詩的な言い回しは使わない（「心の〇〇」「〇〇の世界」「〇〇を奏でる」「輝き」など）
  - 好きなものは、実際にするこうどうや物として出す（例：ラーメンなら「ラーメンを食べに行く」、ねこなら「ねこと遊ぶ」）
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
- image_prompt：絵を描くための英語の説明。もとになる生き物は「{creature}」。その姿に、性格の雰囲気「{motif}」と、好きなもの「{favorite}」の要素を目に見える形で混ぜたオリジナルの守り神1体。
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


def mock_card(code: str, favorite: str) -> dict:
    t = TYPES[code]
    love, friend, study, money = ADVICE[code]
    return {
        "allowed": True, "reason": "",
        "monster": f"{favorite[:4]}モン",
        "catch": "（ダミー）キーを入れると、AIがあなたのあるあるを書いてくれる。",
        "message": "（ダミー）ぼくがずっと、きみを見守っているよ。",
        "love": love, "friend": friend, "study": study, "money": money,
        "image_prompt": t["motif"],
    }


def mock_image(c: str) -> str:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
           f'<rect width="200" height="200" fill="{c}"/>'
           f'<circle cx="100" cy="110" r="55" fill="#fff" opacity=".85"/>'
           f'<circle cx="80" cy="100" r="8"/><circle cx="120" cy="100" r="8"/>'
           f'<path d="M80 130 Q100 145 120 130" stroke="#000" stroke-width="5" fill="none"/></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


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
        raw = trim_margins(raw)  # AIが描いた白い紙のふちを切り取る
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
        "axes": [AXIS_WORDS[c] for c in r["type_code"]],
        "strong": t["strong"],
        "weak": t["weak"],
        "partners": best_partners(r["type_code"]),
        "rival": rival(r["type_code"]),
        "image": f"/img/{r['image_file']}",
    }


@app.route("/")
def index():
    questions = [{"q": q["q"], "a": q["a"], "b": q["b"]} for q in QUESTIONS]
    return render_template("index.html", mock=is_mock(), has_key=bool(API_KEY), questions=questions)


@app.post("/api/card")
def make_card():
    body = request.get_json(silent=True) or {}
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

    mock = is_mock()
    code = decide_type(answers)
    t = TYPES[code]
    profile = axis_profile(answers)
    used = used_monster_names()
    try:
        if mock:
            card = mock_card(code, favorite)
        else:
            card = ai_card(code, favorite, style, profile, used[-150:])
            # 守り神の名前がほかの人とかぶったら、1回だけ作り直す（人とかぶらないことを一番大事にする）
            if card.get("allowed") and card.get("monster") in used:
                card = ai_card(code, favorite, style, profile, used[-150:] + [card["monster"]])
    except Exception as e:
        app.logger.exception("カードの中身の生成に失敗")
        return jsonify({"ok": False, "reason": f"カードを作れませんでした（{type(e).__name__}）。もう一度試してね"}), 502

    if not card.get("allowed"):
        write_log({"event": "refused", "favorite": favorite, "by": "ai"})
        return jsonify({"ok": False, "reason": card.get("reason") or "その好きなものはカードにできないんだ。ほかのものにしてね"})

    try:
        image = mock_image(t["color"]) if mock else ai_image(card["image_prompt"], style, t["hue"])
    except Exception as e:
        app.logger.exception("絵の生成に失敗")
        return jsonify({"ok": False, "reason": f"絵を描けませんでした（{type(e).__name__}）。もう一度試してね"}), 502


    with _lock:
        serial = sum(1 for r in read_log() if r["event"] == "card") + 1
    result = {
        "serial": serial, "type_code": code, "favorite": favorite, "style": style,
        **{k: card[k] for k in ("monster", "catch", "message", "love", "friend", "study", "money")},
    }
    token = save_result(result, image)
    write_log({"event": "card", "serial": serial, "token": token, "type": code, "favorite": favorite,
               "style": style, "mock": mock})
    url = f"{PUBLIC_BASE_URL or request.host_url.rstrip('/')}/r/{token}"
    return jsonify({"ok": True, **result_payload(load_result(token), token), "url": url, "qr": qr_svg(url)})


@app.post("/api/mode")
def set_mode():
    """ダミー／実戦の切り替え。"""
    mode = (request.get_json(silent=True) or {}).get("mode")
    if mode not in ("dummy", "real"):
        return jsonify({"ok": False}), 400
    if mode == "real" and not API_KEY:
        return jsonify({"ok": False, "reason": "Geminiのキーが入っていないので実戦モードにできません"}), 400
    MODE_PATH.parent.mkdir(exist_ok=True)
    MODE_PATH.write_text(json.dumps({"mode": mode}), encoding="utf-8")
    return jsonify({"ok": True, "mode": mode})


@app.get("/r/<token>")
def result_page(token: str):
    """カードのQRコードから開く、その人だけの結果ページ。"""
    return render_template("result.html", r=result_payload(load_result(token), token))


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
    rows = read_log()
    return jsonify({
        "cards": sum(1 for r in rows if r["event"] == "card" and not r.get("mock")),
        "refused": sum(1 for r in rows if r["event"] == "refused"),
        "matches": sum(1 for r in rows if r["event"] == "match"),
    })


if __name__ == "__main__":
    print("ダミーモード" if is_mock() else f"実戦モード：{TEXT_MODEL} / {IMAGE_MODEL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8120)), debug=False)

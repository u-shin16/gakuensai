"""学園祭（2026-11-21）の模擬店「質問に答えると、自分だけのモンスターカードができる」の試作。

流れ：
  1. 2択の質問8問に答える → オリジナルの16タイプのどれかに決まる
  2. 好きなものを1つと、絵柄（かわいい／かっこいい）を選ぶ
  3. Geminiが、タイプと好きなものを混ぜた守り神モンスターの名前・あるある・恋愛や金運などの言葉を作り、絵を描く
  4. 運勢（大吉〜末吉）はサーバー側で抽選し、AIはその運勢に合わせておみくじの言葉を書く
  5. カードのQRコードから、その人だけの結果ページ（/r/<ランダムな文字列>）で詳しい占いと相性を見られる
     URLは連番にしない（番号を変えるだけで他人の結果が見えないようにするため）
  6. 2人のカード番号から相性を出せる

GEMINI_API_KEY が無いときは「お試しモード」で、ダミーの中身と仮の絵を返す。

試してもらった人の反応（いくらなら買うか）は data/log.jsonl に残す。
タイプ・好きなもの・運勢・答えた値段・日時だけで、名前などの個人情報は取らない。
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

from types_data import AXIS_WORDS, QUESTIONS, TYPES, best_partners, decide_type, match, rival

load_dotenv()

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
MOCK = not API_KEY or os.environ.get("MOCK") == "1"

DATA_DIR = Path(__file__).parent / "data"
LOG_PATH = DATA_DIR / "log.jsonl"
RESULT_DIR = DATA_DIR / "results"   # 結果ページ用。1人1ファイル（JSON＋絵）
# QRコードに入れるURLの頭。未設定なら開いているアドレスを使う（スマホで試すときはLANのアドレスで開く）
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16}$")
_lock = threading.Lock()

# 運勢の抽選。凶は入れない（子ども連れが多いため）。合計100。
# 大吉は枠が金色になる。「もう1回」の理由になるので、出すぎないようにしている。
FORTUNES = [("大吉", 10), ("中吉", 20), ("小吉", 25), ("吉", 30), ("末吉", 15)]

# 実在キャラ・有名作品は作らない（著作権）。AIの判定より先に、ここで確実に弾く。
BLOCKED_WORDS = [
    "ピカチュウ", "ポケモン", "ポケットモンスター", "マリオ", "ルイージ", "カービィ", "ゼルダ",
    "ドラえもん", "アンパンマン", "ミッキー", "ミニー", "ディズニー", "キティ", "サンリオ",
    "ちいかわ", "ハチワレ", "スヌーピー", "ドラゴンボール", "悟空", "ワンピース", "ルフィ",
    "鬼滅", "炭治郎", "ナルト", "呪術", "コナン", "しんちゃん", "ドラクエ", "ガンダム",
    "ゴジラ", "ウルトラマン", "仮面ライダー", "プリキュア",
]

STYLES = {
    "cute": ("Cute chibi original monster, round soft shapes, big sparkling eyes, pastel and bright colors, "
             "cheerful expression, soft cel shading, simple radial background"),
    "cool": ("Cool majestic original creature, dynamic heroic pose, sharp elegant design, dramatic rim lighting, "
             "rich detailed fantasy illustration, epic atmospheric background"),
}
IMAGE_COMMON = ("single character, full body, centered, trading card game art, "
                "no text, no letters, no logos, no frame, not resembling any existing franchise character. ")

CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "allowed": {"type": "boolean"},
        "reason": {"type": "string"},
        "monster": {"type": "string"},
        "catch": {"type": "string"},
        "love": {"type": "string"},
        "friend": {"type": "string"},
        "study": {"type": "string"},
        "money": {"type": "string"},
        "lucky": {"type": "string"},
        "image_prompt": {"type": "string"},
    },
    "required": ["allowed", "reason", "monster", "catch", "love", "friend", "study", "money", "lucky", "image_prompt"],
}

CARD_PROMPT = """あなたは学園祭の模擬店で、お客さんの性格診断の結果と好きなものから、
その人だけのおみくじを書く係です。おみくじには、その人を守るオリジナルモンスター（守り神）が描かれます。
お客さんは小学生から大人まで。

運勢：{fortune}

性格タイプ：{type_name}（{type_desc}）
強み：{strong}／弱点：{weak}
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
- monster：性格と好きなものを混ぜた、この人の守り神モンスターの名前。カタカナ中心で8文字以内（例：「メンドラゴ」）
- catch：この人の「あるある」を1文で（40文字以内）。好きなものを自然に混ぜ、大人が読んでも「わかる、当たってる」と思える内容にする。悪口にしない
- love（恋愛）・friend（友情）・study（勉強・仕事）・money（金運）：それぞれ20文字以内のおみくじの言葉。
  運勢の良さに合わせ、性格にちなんだ具体的なアドバイスにする。末吉でも前向きに。大人も子どもも読める言葉で
- lucky：ラッキーアイテムを1つ（10文字以内）。好きなものに少し関係するもの
- image_prompt：絵を描くための英語の説明。モチーフ「{motif}」に、好きなもの「{favorite}」の要素を目に見える形で混ぜたオリジナルモンスター1体。既存キャラに似せない。文字は入れない
"""


def draw_fortune() -> str:
    names, weights = zip(*FORTUNES)
    return random.choices(names, weights=weights, k=1)[0]


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


def mock_card(t: dict, favorite: str) -> dict:
    return {
        "allowed": True, "reason": "",
        "monster": f"{favorite[:4]}モン",
        "catch": "お試しモード：キーを入れると、AIがあなたのあるあるを書いてくれる。",
        "love": "思い切って話しかけると吉", "friend": "約束は早めに決めると吉",
        "study": "朝のうちに片づけると吉", "money": "寄り道をがまんすると吉",
        "lucky": favorite[:10],
        "image_prompt": t["motif"],
    }


def mock_image(element: str) -> str:
    colors = {"ほのお": "#ff7a45", "みず": "#40a9ff", "くさ": "#73d13d", "でんき": "#fadb14",
              "こおり": "#87e8de", "やみ": "#9254de", "ひかり": "#ffe58f", "かぜ": "#b7eb8f"}
    c = colors.get(element, "#ccc")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
           f'<rect width="200" height="200" fill="{c}"/>'
           f'<circle cx="100" cy="110" r="55" fill="#fff" opacity=".85"/>'
           f'<circle cx="80" cy="100" r="8"/><circle cx="120" cy="100" r="8"/>'
           f'<path d="M80 130 Q100 145 120 130" stroke="#000" stroke-width="5" fill="none"/></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def ai_card(t: dict, favorite: str, style: str, fortune: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    prompt = CARD_PROMPT.format(
        type_name=t["name"], type_desc=t["desc"], strong=t["strong"], weak=t["weak"],
        element=t["element"], favorite=favorite, motif=t["motif"], fortune=fortune,
        style="かわいい" if style == "cute" else "かっこいい",
    )
    resp = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CARD_SCHEMA,
            temperature=1.0,
        ),
    )
    return json.loads(resp.text)


def ai_image(prompt: str, style: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=f"{STYLES[style]}, {IMAGE_COMMON}Subject: {prompt}",
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
    (RESULT_DIR / f"{token}.{ext}").write_bytes(base64.b64decode(b64))
    result = {**result, "image_file": f"{token}.{ext}", "created_at": datetime.now().isoformat(timespec="seconds")}
    (RESULT_DIR / f"{token}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return token


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
    return render_template("index.html", mock=MOCK, questions=questions)


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

    code = decide_type(answers)
    t = TYPES[code]
    fortune = draw_fortune()
    try:
        card = mock_card(t, favorite) if MOCK else ai_card(t, favorite, style, fortune)
    except Exception as e:
        app.logger.exception("カードの中身の生成に失敗")
        return jsonify({"ok": False, "reason": f"カードを作れませんでした（{type(e).__name__}）。もう一度試してね"}), 502

    if not card.get("allowed"):
        write_log({"event": "refused", "favorite": favorite, "by": "ai"})
        return jsonify({"ok": False, "reason": card.get("reason") or "その好きなものはカードにできないんだ。ほかのものにしてね"})

    try:
        image = mock_image(t["element"]) if MOCK else ai_image(card["image_prompt"], style)
    except Exception as e:
        app.logger.exception("絵の生成に失敗")
        return jsonify({"ok": False, "reason": f"絵を描けませんでした（{type(e).__name__}）。もう一度試してね"}), 502


    with _lock:
        serial = sum(1 for r in read_log() if r["event"] == "card") + 1
    result = {
        "serial": serial, "fortune": fortune, "type_code": code, "favorite": favorite, "style": style,
        **{k: card[k] for k in ("monster", "catch", "love", "friend", "study", "money", "lucky")},
    }
    token = save_result(result, image)
    write_log({"event": "card", "serial": serial, "token": token, "type": code, "favorite": favorite,
               "style": style, "fortune": fortune, "mock": MOCK})
    url = f"{PUBLIC_BASE_URL or request.host_url.rstrip('/')}/r/{token}"
    return jsonify({"ok": True, **result_payload(load_result(token), token), "url": url, "qr": qr_svg(url)})


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


@app.post("/api/feedback")
def feedback():
    body = request.get_json(silent=True) or {}
    price = body.get("price")
    if price not in (0, 100, 200, 300, 400, 500, 700, 1000):
        return jsonify({"ok": False}), 400
    write_log({"event": "feedback", "serial": body.get("serial"), "price": price,
               "again": bool(body.get("again"))})
    return jsonify({"ok": True})


@app.get("/api/stats")
def stats():
    """試してもらった結果のまとめ。企画書に使う。お試しモードで作ったカードは数えない。"""
    rows = read_log()
    real = {r["serial"] for r in rows if r["event"] == "card" and not r.get("mock")}
    fb = [r for r in rows if r["event"] == "feedback" and r.get("serial") in real]
    prices = [r["price"] for r in fb]
    return jsonify({
        "cards": len(real),
        "refused": sum(1 for r in rows if r["event"] == "refused"),
        "matches": sum(1 for r in rows if r["event"] == "match"),
        "answers": len(fb),
        "want_again": sum(1 for r in fb if r.get("again")),
        "avg_price": round(sum(prices) / len(prices)) if prices else None,
        "would_pay_300_or_more": sum(1 for p in prices if p >= 300),
    })


if __name__ == "__main__":
    print("お試しモード（キー無し）" if MOCK else f"AIモード：{TEXT_MODEL} / {IMAGE_MODEL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8120)), debug=False)

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

load_dotenv()  # store・drawing が読み込まれる前に .env を読む（後だと FIRESTORE_PREFIX などが効かない）

import qrcode
import qrcode.image.svg
from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session

from trim import edge_color, zoom_to_clean
import drawing
import store
from types_data import ADVICE, AXIS_WORDS, CREATURES, QUESTIONS, TYPES, axis_profile, best_partners, decide_type, match, rival

app = Flask(__name__)
# 管理者のログイン状態をクッキーに入れるための鍵。本番では .env の SECRET_KEY を使う
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("PUBLIC_BASE_URL", "").startswith("https"))

# 管理者画面にログインできるGoogleアカウント（.env の ADMIN_EMAILS にカンマ区切り）。
# 登録したアカウントだけが入れる（ゆーしんの決まり、2026-10-01）。登録の方法はミーティングで決める
# ログインは Firebase Authentication の Google ログイン（2026-10-01）。ウェブ用の設定は公開してよい値
FIREBASE_WEB = {"apiKey": os.environ.get("FIREBASE_API_KEY", ""),
                "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
                "projectId": os.environ.get("FIREBASE_PROJECT_ID", "")}
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}

API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")


def load_drawer():
    """絵を描く関数。.env の DRAW_FUNC=モジュール名:関数名 で差し替えられる（既定は drawing.draw）。"""
    import importlib
    mod, _, fn = os.environ.get("DRAW_FUNC", "drawing:draw").partition(":")
    return getattr(importlib.import_module(mod), fn or "draw")


DRAW = load_drawer()

DATA_DIR = Path(__file__).parent / "data"
RESULT_DIR = DATA_DIR / "results"   # 守り神の絵の置き場所（結果などのデータは Firestore。store.py）
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


def write_log(entry: dict) -> None:
    """記録は Firestore の events に残す。記録に失敗しても、お客さんの操作は止めない。"""
    try:
        store.log(entry)
    except Exception:
        app.logger.exception("記録の保存に失敗")


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


def save_result(result: dict, png: bytes) -> str:
    """絵をサーバーに、結果を Firestore に保存して、推測されないトークンを返す。"""
    token = secrets.token_urlsafe(12)  # 16文字
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    raw = png
    # 描き直しても残った紙のふち・白い四隅は、中心に向かって少し拡大して切る（塗らない。塗ると跡が見えたため）
    raw = zoom_to_clean(raw)
    (RESULT_DIR / f"{token}.png").write_bytes(raw)
    store.save_result(token, {**result, "image_file": f"{token}.png", "art_bg": edge_color(raw),
                              "created_at": datetime.now().isoformat(timespec="seconds")})
    return token


def load_result(token: str) -> dict:
    if not TOKEN_RE.match(token):
        abort(404)
    r = store.get_result(token)
    if r is None:
        abort(404)
    return r


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
    style = body.get("style") if body.get("style") in drawing.STYLES else "cute"

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
    used = list(reversed(store.recent_monster_names(150)))
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
            image = DRAW({"image_prompt": card["image_prompt"], "monster": card.get("monster", ""), "type_code": code,
                          "type_name": t["name"], "motif": t["motif"], "hue": t["hue"], "color": t["color"],
                          "favorite": favorite, "style": style})
        except Exception as e:
            app.logger.exception("絵の生成に失敗")
            return jsonify({"ok": False, "reason": ai_error_reason(e, "絵を描けませんでした")}), 502

        try:
            card["message"] = f_msg.result() or card["message"]
        except Exception:
            app.logger.exception("ひとことの作成に失敗（最初の文章の係が書いた文を使う）")
    finally:
        pool.shutdown(wait=False)

    serial = store.next_serial()
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
# 店の画面に広場を映し、結果ページで「あいことば」を入れた人の守り神が現れて歩き回る。
# 入った守り神は全員ずっと広場に残る（ゆーしん「1つの大きい広場に全員がたまる」）。数が増えたら画面のほうで小さくする。

@app.get("/plaza")
def plaza_page():
    return render_template("plaza.html", code=store.plaza_code())


# ===== お店のあいことば（2026-10-01） =====
# 本番に置くと、URLを知っている人ならだれでもカードを作れてしまい、AI代がゆーしんに請求される。
# チケットの仕組みができるまでは、お店で教える4けたの「お店のあいことば」がないとカードを作れないようにする。

def shop_code() -> str:
    return store.shop_code()


@app.post("/api/shop/check")
def shop_check():
    """診断を始める前に、お店のあいことばが合っているかを確かめる。"""
    ok = str((request.get_json(silent=True) or {}).get("code", "")).strip() == shop_code()
    return jsonify({"ok": ok})


@app.post("/api/shop/newcode")
def shop_newcode():
    staff_only()
    return jsonify({"ok": True, "code": store.shop_code(renew=True)})


# ===== 管理者画面（2026-10-01） =====
# 登録したGoogleアカウント（ADMIN_EMAILS）だけが入れる。ログインは Firebase Authentication。

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


@app.get("/admin")
def admin_home():
    staff_only()
    return render_template("admin/home.html", code=store.plaza_code(), plaza=len(store.plaza_members()),
                           cards=store.count_results(), shop=shop_code(), email=session.get("admin_email", ""))


@app.get("/plaza/admin")
@app.get("/characters")
def old_admin_urls():
    """前のアドレスから、管理者画面の新しいアドレスへ案内する。"""
    return redirect("/admin/plaza" if request.path.startswith("/plaza") else "/admin/characters")


@app.get("/admin/login")
def admin_login():
    return render_template("admin/login.html", fb=FIREBASE_WEB, error=request.args.get("error", ""))


@app.post("/admin/login")
def admin_login_post():
    """FirebaseのGoogleログインで受け取ったIDトークンを確かめ、登録したアカウントなら管理者として入れる。"""
    from firebase_admin import auth

    store.db()  # Firebase を初期化しておく
    try:
        info = auth.verify_id_token(str((request.get_json(silent=True) or {}).get("idToken", "")))
    except Exception:
        return jsonify({"ok": False, "error": "invalid"}), 401
    email = (info.get("email") or "").lower()
    if not info.get("email_verified") or email not in ADMIN_EMAILS:
        write_log({"event": "admin_denied"})
        return jsonify({"ok": False, "error": "denied"}), 403
    session.clear()
    session["admin_email"] = email
    return jsonify({"ok": True})


@app.get("/admin/logout")
def admin_logout():
    session.pop("admin_email", None)
    return redirect("/admin/login")


@app.get("/admin/plaza")
def plaza_admin():
    """広場の管理画面。あいことば・広場にいる守り神の一覧・広場から出す。"""
    staff_only()
    return render_template("admin/plaza.html", code=store.plaza_code())


@app.post("/api/plaza/kick")
def plaza_kick():
    """管理画面から、守り神を広場から出す。all=true なら全員。"""
    staff_only()
    body = request.get_json(silent=True) or {}
    if body.get("all"):
        return jsonify({"ok": True, "removed": store.plaza_clear()})
    store.plaza_leave(str(body.get("token", "")))
    return jsonify({"ok": True})


@app.post("/api/plaza/leave")
def plaza_leave():
    """結果ページから、自分の守り神を広場から出す。トークンは推測できないので、本人だけが出せる。"""
    token = str((request.get_json(silent=True) or {}).get("token", ""))
    load_result(token)  # 無いトークンは404
    store.plaza_leave(token)
    return jsonify({"ok": True})


@app.post("/api/plaza/newcode")
def plaza_newcode():
    staff_only()
    return jsonify({"ok": True, "code": store.plaza_code(renew=True)})


@app.post("/api/plaza/join")
def plaza_join():
    body = request.get_json(silent=True) or {}
    token = str(body.get("token", ""))
    code = str(body.get("code", "")).strip()
    r = load_result(token)  # 無いトークンは404
    if code != store.plaza_code():
        return jsonify({"ok": False, "reason": "あいことばがちがうよ。広場の画面に出ている4けたの数字を入れてね"}), 400
    if not store.plaza_join(token):
        return jsonify({"ok": True, "already": True})
    write_log({"event": "plaza", "serial": r.get("serial")})
    return jsonify({"ok": True})


@app.get("/api/plaza")
def plaza_members():
    """広場にいる守り神（入った全員）。映すのは絵・名前・番号・タイプだけ。"""
    out = []
    for token, joined_at in store.plaza_members():
        r = store.get_result(token)
        if not r:
            continue
        t = TYPES.get(r.get("type_code"), {})
        out.append({"id": token, "serial": r.get("serial"), "monster": r.get("monster", ""),
                    "type_name": t.get("name", ""), "color": t.get("color", "#888888"),
                    "image": f"/img/{r['image_file']}", "joined_at": joined_at})
    return jsonify({"members": out, "total": len(out), "code": store.plaza_code()})


@app.get("/admin/characters")
def characters():
    """これまでに作った守り神の一覧（スタッフ用。好きなものも出る）。"""
    staff_only()
    rows = []
    for token, r in store.list_results():
        t = TYPES.get(r.get("type_code"), {})
        rows.append({
            "token": token,
            "serial": r.get("serial", 0),
            "monster": r.get("monster", ""),
            "type_name": t.get("name", ""),
            "color": t.get("color", "#888888"),
            "style": "かっこいい" if r.get("style") == "cool" else "かわいい",
            "favorite": r.get("favorite", ""),
            "message": r.get("message", ""),
            "created_at": r.get("created_at", "")[:16].replace("T", " "),
            "image": f"/img/{r['image_file']}",
            "dummy": False,
        })
    rows.sort(key=lambda x: x["serial"], reverse=True)
    return render_template("admin/characters.html", rows=rows, show_dummy=False)


@app.get("/r/<token>")
def result_page(token: str):
    """カードのQRコードから開く、その人だけの結果ページ。"""
    r = load_result(token)
    return render_template("result.html", r=result_payload(r, token), in_plaza=store.in_plaza(token))


@app.get("/img/<name>")
def result_image(name: str):
    if not re.match(r"^[A-Za-z0-9_-]{16}\.png$", name):
        abort(404)
    return send_from_directory(RESULT_DIR, name, max_age=86400)


@app.post("/api/match")
def match_cards():
    """2枚のカード番号から相性を出す。家族や友だちで見せ合う用。"""
    body = request.get_json(silent=True) or {}
    try:
        a, b = store.find_by_serial(int(body.get("a"))), store.find_by_serial(int(body.get("b")))
    except (TypeError, ValueError):
        a = b = None
    if not a or not b:
        return jsonify({"ok": False, "reason": "そのカード番号は見つからないよ"}), 404
    (_, ra), (_, rb) = a, b
    if ra["serial"] == rb["serial"]:
        return jsonify({"ok": False, "reason": "ちがうカードの番号を入れてね"}), 400
    m = match(ra["type_code"], rb["type_code"])
    write_log({"event": "match", "a": ra["serial"], "b": rb["serial"], "score": m["score"]})
    return jsonify({"ok": True, "a": TYPES[ra["type_code"]]["name"], "b": TYPES[rb["type_code"]]["name"], **m})


@app.get("/api/stats")
def stats():
    """試してもらった結果のまとめ。"""
    staff_only()
    return jsonify({"cards": store.count_results(), "refused": store.count_events("refused"),
                    "matches": store.count_events("match")})


if __name__ == "__main__":
    print(f"AI：{TEXT_MODEL} / {IMAGE_MODEL}" if API_KEY else "Geminiのキーがありません（.env を確認）")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8120)), debug=False)

"""学園祭（2026-11-21）の模擬店「質問に答えると、自分だけのモンスターカードができる」の試作。

流れ：
  1. 2択の質問8問に答える → オリジナルの16タイプのどれかに決まる
  2. 好きなものを1つと、絵柄（かわいい／かっこいい）を選ぶ
  3. Geminiが、タイプと好きなものを混ぜた案内アニマルの名前・あるある・恋愛や金運などの言葉を作り、絵を描く
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
from types_data import ADVICE, AXIS_WORDS, TYPES, best_partners, match, rival
import battle_data as bd


def type_info(code: str) -> dict:
    """タイプの中身。2026-10-02からは動物バトル診断の5タイプ（ネコ科など）。それより前のカードは16タイプ（ESTJなど）。"""
    if code in bd.ANIMAL_TYPES:
        return bd.ANIMAL_TYPES[code]
    t = TYPES.get(code)
    return {**t, "advice": ADVICE[code]} if t else {}

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
# カード・チケットを消すときのパスワード（.env の DELETE_PASSWORD。値はコードにもGitHubにも書かない。2026-10-02）
DELETE_PASSWORD = os.environ.get("DELETE_PASSWORD", "")
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
RESULT_DIR = DATA_DIR / "results"   # 案内アニマルの絵の置き場所（結果などのデータは Firestore。store.py）
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
その人だけの診断カードを書く係です。カードには、動物王国でその人を案内するオリジナルの動物（案内アニマル）が描かれます。
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
- monster：性格と好きなものを混ぜた、この人の案内アニマルの名前。カタカナ中心で8文字以内。
  次の名前はもう使われているので、同じ名前・よく似た名前にしない：{used_names}
- message：案内アニマルからこの人への「ひとこと」。カードに大きく載る。次の決まりを必ず守る。
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
- image_prompt：絵を描くための英語の説明。案内アニマルのもとになる動物は「{creature}」。だれが見てもその動物だと分かる姿をはっきり残したまま、性格の雰囲気「{motif}」と、好きなもの「{favorite}」の要素を、模様・色・身につけた物・まわりの小物として目に見える形で混ぜたオリジナルの案内アニマル1体。
  ふつうの人間の姿にはしない。ドラゴンの姿にはしない。既存キャラに似せない。文字は入れない
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


# ===== ダミーモード（2026-10-01 作り直し） =====
# Geminiを使わずにカードを作る（0円）。AIの上限に達したときや、画面の流れを試すとき用。
# 切り替えは管理者画面（/admin）だけ。キーが無いとき・.env に MOCK=1 のときは必ずダミー。

def is_mock() -> bool:
    if not API_KEY or os.environ.get("MOCK") == "1":
        return True
    return store.ai_mode() == "dummy"


def mock_card(code: str, favorite: str) -> dict:
    love, friend, study, money = type_info(code)["advice"]
    return {
        "allowed": True, "reason": "",
        "monster": favorite[:4] + random.choice(["モン", "まる", "りん", "ぼう", "ドン", "ぴょん"]),
        "message": f"（ダミー）きみのいいところは、{favorite}の時間にもきっと活きるよ。",
        "love": love, "friend": friend, "study": study, "money": money,
        "image_prompt": type_info(code)["motif"],
    }


def mock_draw(info: dict) -> bytes:
    import draw_example
    return draw_example.draw(info)


def ai_card(code: str, favorite: str, style: str, profile: list[str], used_names: list[str], creature: str) -> dict:
    t = type_info(code)
    love, friend, study, money = t["advice"]
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    prompt = CARD_PROMPT.format(
        type_name=t["name"], type_desc=t["desc"], strong=t["strong"], weak=t["weak"],
        element=t["element"], favorite=favorite, motif=t["motif"], creature=creature,
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


MESSAGE_PROMPT = """あなたは、動物王国でお客さんを案内する案内アニマルです。その人にカードで渡す「ひとこと」を書きます。
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


PROOF_PROMPT = """次の文は、案内アニマルが小学生から大人までの人に渡すカードに書く「ひとこと」です。
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
    """案内アニマルのひとことだけを、考える時間つきで作る。1文目と2文目のつながりを良くするため（2026-09-30）。"""
    from google import genai
    from google.genai import types

    t = type_info(code)
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
    t = type_info(r["type_code"])
    out = {
        **r,
        "token": token,
        "type_name": t["name"],
        "type_kana": t["kana"],
        "color": t["color"],
        "type_desc": t["desc"],
        "aruaru": t["aruaru"],
        "strong": t["strong"],
        "weak": t["weak"],
        "image": f"/img/{r['image_file']}",
    }
    b = r.get("battle")
    if b:   # 動物バトル診断のカード
        out["axes"] = [f"{b['statUp']} +10%", f"{b['statDown']} −10%", f"{r['month']}月生まれ"]
        out["battle_skills"] = (
            [{"slot": "攻撃", "name": b["attack"], "note": bd.SKILL_NOTES[b["attack"]]}]
            + [{"slot": "技", "name": n, "note": bd.SKILL_NOTES[n]} for n in b["others"]]
            + [{"slot": "タイプ", "name": bd.TYPE_SKILLS[b["type"]], "note": f"{t['name']}だけの技"},
               {"slot": f"{r['month']}月", "name": bd.MONTH_SKILLS[r["month"] - 1], "note": "誕生月の技"}])
    else:   # 2026-10-01までの16タイプのカード
        out["axes"] = [AXIS_WORDS[c] for c in r["type_code"]]
        out["partners"] = best_partners(r["type_code"])
        out["rival"] = rival(r["type_code"])
    return out


def ai_error_reason(e: Exception, what: str) -> str:
    """AIのエラーを、お店で読んで分かる言葉にする。
    月の利用上限（429 RESOURCE_EXHAUSTED）は、もう一度押しても直らないのでスタッフに知らせる（2026-10-01に発生）。"""
    text = str(e)
    if "RESOURCE_EXHAUSTED" in text or "spending cap" in text:
        return f"{what}。AIの今月の利用上限に達しています（スタッフの人へ：ai.studio/spend で上限を確認してください）"
    return f"{what}（{type(e).__name__}）。もう一度試してね"


@app.route("/")
def index():
    questions = bd.questions_for_page()
    return render_template("index.html", questions=questions, mock=is_mock())


@app.post("/api/card")
def make_card():
    body = request.get_json(silent=True) or {}
    ticket = None
    if body.get("ticket"):
        ticket = parse_ticket(str(body["ticket"]))
        if not ticket:
            return jsonify({"ok": False, "reason": "このチケットは使えません。お店の人に見せてね"}), 403
        if ticket["status"] != "unused":
            return jsonify({"ok": False, "reason": "このチケットはもう使われています", "used": True}), 409
    elif str(body.get("shop", "")).strip() != shop_code():
        return jsonify({"ok": False, "reason": "お店のあいことばがちがうよ。お店の人に聞いてね", "shop": True}), 403
    answers = body.get("answers") or []
    favorite = str(body.get("favorite", "")).strip()
    style = body.get("style") if body.get("style") in drawing.STYLES else "cute"
    try:
        month = int(body.get("month"))
        judged = bd.judge([int(a) for a in answers])
    except (TypeError, ValueError):
        return jsonify({"ok": False, "reason": "誕生月と質問にぜんぶ答えてね"}), 400
    if not 1 <= month <= 12:
        return jsonify({"ok": False, "reason": "誕生月をえらんでね"}), 400
    if not favorite:
        return jsonify({"ok": False, "reason": "好きなものを入れてね"}), 400
    if len(favorite) > 20:
        return jsonify({"ok": False, "reason": "好きなものは20文字までにしてね"}), 400
    if blocked(favorite):
        write_log({"event": "refused", "favorite": favorite, "by": "list"})
        return jsonify({"ok": False, "reason": "ごめんね、アニメやゲームにいるキャラクターはカードにできないんだ。"
                                           "ほかの好きなものを入れてみて！（例：カレー、ねこ、サッカー）"})

    mock = is_mock()
    # 動物バトル診断（2026-10-02 案2）：誕生月と6問から、動物タイプ・ステータス・技が決まる
    code = judged["type"]
    t = type_info(code)
    profile = [f"{judged['statUp']}が高め", f"{judged['statDown']}が低め", f"得意技は{judged['attack']}"]
    creature = random.choice(t["animals"])
    used = list(reversed(store.recent_monster_names(150)))
    pool = ThreadPoolExecutor(max_workers=2)
    # 案内アニマルのひとこと（作る→チェックして直す、で約10秒）は、ほかに頼らないので最初に始めておく。
    # 文章→絵（合わせて約10秒）と並行して進むので、待ち時間は増えない。
    f_msg = None if mock else pool.submit(ai_message, code, favorite, profile)
    try:
        try:
            if mock:
                card = mock_card(code, favorite)
            else:
                card = ai_card(code, favorite, style, profile, used[-150:], creature)
                # 案内アニマルの名前がほかの人とかぶったら、1回だけ作り直す（人とかぶらないことを一番大事にする）
                if card.get("allowed") and card.get("monster") in used:
                    card = ai_card(code, favorite, style, profile, used[-150:] + [card["monster"]], creature)
        except Exception as e:
            app.logger.exception("カードの中身の生成に失敗")
            return jsonify({"ok": False, "reason": ai_error_reason(e, "カードを作れませんでした")}), 502

        if not card.get("allowed"):
            write_log({"event": "refused", "favorite": favorite, "by": "ai"})
            return jsonify({"ok": False, "reason": card.get("reason") or "その好きなものはカードにできないんだ。ほかのものにしてね"})

        try:
            image = (mock_draw if mock else DRAW)({"image_prompt": card["image_prompt"], "monster": card.get("monster", ""), "type_code": code,
                          "type_name": t["name"], "motif": t["motif"], "hue": t["hue"], "color": t["color"],
                          "favorite": favorite, "style": style})
        except Exception as e:
            app.logger.exception("絵の生成に失敗")
            return jsonify({"ok": False, "reason": ai_error_reason(e, "絵を描けませんでした")}), 502

        if f_msg is not None:
            try:
                card["message"] = f_msg.result() or card["message"]
            except Exception:
                app.logger.exception("ひとことの作成に失敗（最初の文章の係が書いた文を使う）")
    finally:
        pool.shutdown(wait=False)

    serial = store.next_serial()
    result = {
        "serial": serial, "type_code": code, "favorite": favorite, "style": style,
        "month": month, "answers": [int(a) for a in answers], "battle": judged, "creature": creature,
        **{k: card[k] for k in ("monster", "message", "love", "friend", "study", "money")},
        **({"mock": True} if mock else {}),
    }
    token = save_result(result, image)
    write_log({"event": "card", "serial": serial, "token": token, "type": code, "favorite": favorite,
               "style": style, **({"mock": True} if mock else {})})
    url = f"{PUBLIC_BASE_URL or request.host_url.rstrip('/')}/r/{token}"
    pickup = ""
    if ticket:
        claimed = store.claim_ticket(ticket["number"], ticket["secret"], token, serial)
        if claimed is None:  # 同じチケットで2つの画面から同時に作ったとき。先に終わったほうを正とする
            claimed = store.get_ticket(ticket["number"])
        pickup = slot_label(claimed.get("slot", ""))
        write_log({"event": "ticket", "number": ticket["number"], "token": token, "slot": claimed.get("slot")})
        # チケットのお客さんには、カードの中身を渡さない（受け取ったカードのQRを読むまで見せない。2026-10-01 ゆーしん）
        return jsonify({"ok": True, "pickup": pickup, "number": ticket["number"]})
    return jsonify({"ok": True, **result_payload(load_result(token), token), "url": url, "qr": qr_svg(url),
                    "pickup": pickup})


# ===== チケット（2026-10-01） =====
# 代金をもらったらチケットを渡す。チケットのQRを読むと、そのチケット専用のページ（/12-K7QP）が開いて診断できる。
# 番号の後ろの4文字はQRにだけ入っているので、番号を変えて他人のチケットを開くことはできない。1枚1回だけ。
# 答え終わると「○時○分に取りに来てね」が出る（受け取りの枠は store.slot_settings。2026-10-02のミーティングで決める）。

TICKET_RE = re.compile(r"^(\d{1,5})-([A-Z0-9]{4})$")


def parse_ticket(text: str) -> dict | None:
    """「12-K7QP」が本物のチケットなら中身を返す。番号だけ・合言葉ちがいは None。"""
    m = TICKET_RE.match(text.strip().upper())
    if not m:
        return None
    t = store.get_ticket(int(m.group(1)))
    if not t or not secrets.compare_digest(t["secret"], m.group(2)):
        return None
    return t


def slot_label(slot: str) -> str:
    """"2026-11-21 13:40" → "13時40分"。"""
    if not slot:
        return ""
    hh, mm = slot[-5:].split(":")
    return f"{int(hh)}時{mm}分"


def ticket_url(t: dict) -> str:
    return f"{PUBLIC_BASE_URL or request.host_url.rstrip('/')}/{t['number']}-{t['secret']}"


@app.get("/<int:num>-<code>")
def ticket_page(num: int, code: str):
    t = parse_ticket(f"{num}-{code}")
    if not t:
        return render_template("ticket_bad.html"), 404
    if t["status"] != "unused":
        return render_template("ticket_used.html", t=t, pickup=slot_label(t.get("slot", "")))
    questions = bd.questions_for_page()
    return render_template("index.html", questions=questions, ticket=f"{t['number']}-{t['secret']}", number=t["number"],
                           mock=is_mock())


@app.get("/<int:num>")
def ticket_number_only(num: int):
    return render_template("ticket_bad.html"), 404


@app.get("/admin/tickets")
def admin_tickets():
    staff_only()
    tickets = store.list_tickets()
    for t in tickets:
        t["url"] = ticket_url(t)
        t["pickup"] = slot_label(t.get("slot", ""))
    return render_template("admin/tickets.html", tickets=tickets, slots=store.slot_settings())


@app.get("/admin/tickets/print")
def admin_tickets_print():
    staff_only()
    # ?n=1,2,3 なら選んだチケットだけ（使用済みも含む）、なければまだ使っていないチケットぜんぶ
    picked = {int(x) for x in request.args.get("n", "").split(",") if x.strip().isdigit()}
    tickets = [t for t in store.list_tickets() if (t["number"] in picked if picked else t["status"] == "unused")]
    for t in tickets:
        t["qr"] = qr_svg(ticket_url(t))
    return render_template("admin/tickets_print.html", tickets=tickets)


@app.get("/admin/card/<token>")
def admin_card(token: str):
    """スタッフがカードを印刷する画面。お客さんの画面と同じカードを出して、画像で保存できる。"""
    staff_only()
    url = f"{PUBLIC_BASE_URL or request.host_url.rstrip('/')}/r/{token}"
    card = {**result_payload(load_result(token), token), "url": url, "qr": qr_svg(url)}
    questions = bd.questions_for_page()
    return render_template("index.html", questions=questions, preset=card, mock=False)


@app.post("/api/tickets/manage")
def tickets_manage():
    """チケットを消す・未使用に戻す（管理者だけ・削除用パスワードが要る。2026-10-02）。"""
    staff_only()
    body = request.get_json(silent=True) or {}
    if not DELETE_PASSWORD:
        return jsonify({"ok": False, "reason": "削除用のパスワードが設定されていません（.env の DELETE_PASSWORD）"}), 500
    if not secrets.compare_digest(str(body.get("password", "")), DELETE_PASSWORD):
        write_log({"event": "ticket_manage_refused", "by": session.get("admin_email", "local")})
        return jsonify({"ok": False, "reason": "パスワードがちがいます"}), 403
    action = body.get("action")
    numbers = [int(n) for n in (body.get("numbers") or []) if str(n).isdigit()]
    if action == "delete" and body.get("all"):
        n = store.delete_all_tickets()
    elif action == "delete" and numbers:
        n = store.delete_tickets(numbers)
    elif action == "reset" and numbers:
        n = store.reset_tickets(numbers)
    else:
        return jsonify({"ok": False, "reason": "チケットが選ばれていません"}), 400
    write_log({"event": f"ticket_{action}", "count": n, "all": bool(body.get("all")), "by": session.get("admin_email", "local")})
    return jsonify({"ok": True, "count": n})


@app.post("/api/tickets/create")
def tickets_create():
    staff_only()
    n = int((request.get_json(silent=True) or {}).get("n", 10))
    if not 1 <= n <= 500:
        return jsonify({"ok": False, "reason": "1〜500枚で指定してね"}), 400
    made = store.create_tickets(n)
    return jsonify({"ok": True, "from": made[0]["number"], "to": made[-1]["number"]})


# ===== 案内アニマルの広場（2026-10-01） =====
# 店の画面に広場を映し、結果ページで「あいことば」を入れた人の案内アニマルが現れて歩き回る。
# 入った案内アニマルは全員ずっと広場に残る（ゆーしん「1つの大きい広場に全員がたまる」）。数が増えたら画面のほうで小さくする。

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
                           cards=store.count_cards(), shop=shop_code(), email=session.get("admin_email", ""),
                           mock=is_mock(), has_key=bool(API_KEY), forced=os.environ.get("MOCK") == "1")


@app.post("/api/mode")
def set_mode():
    """ダミー／本物の切り替え（管理者だけ）。"""
    staff_only()
    mode = (request.get_json(silent=True) or {}).get("mode")
    if mode not in ("dummy", "real"):
        return jsonify({"ok": False}), 400
    if mode == "real" and not API_KEY:
        return jsonify({"ok": False, "reason": "Geminiのキーが入っていないので本物にできません"}), 400
    store.set_ai_mode(mode)
    write_log({"event": "mode", "mode": mode, "by": session.get("admin_email", "local")})
    return jsonify({"ok": True, "mode": mode})


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
    """広場の管理画面。あいことば・広場にいる案内アニマルの一覧・広場から出す。"""
    staff_only()
    return render_template("admin/plaza.html", code=store.plaza_code())


@app.post("/api/plaza/kick")
def plaza_kick():
    """管理画面から、案内アニマルを広場から出す。all=true なら全員。"""
    staff_only()
    body = request.get_json(silent=True) or {}
    if body.get("all"):
        return jsonify({"ok": True, "removed": store.plaza_clear()})
    store.plaza_leave(str(body.get("token", "")))
    return jsonify({"ok": True})


@app.post("/api/plaza/leave")
def plaza_leave():
    """結果ページから、自分の案内アニマルを広場から出す。トークンは推測できないので、本人だけが出せる。"""
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
    """広場にいる案内アニマル（入った全員）。映すのは絵・名前・番号・タイプだけ。"""
    out = []
    for token, joined_at in store.plaza_members():
        r = store.get_result(token)
        if not r:
            continue
        t = type_info(r.get("type_code", ""))
        out.append({"id": token, "serial": r.get("serial"), "monster": r.get("monster", ""),
                    "type_name": t.get("name", ""), "color": t.get("color", "#888888"),
                    "image": f"/img/{r['image_file']}", "joined_at": joined_at})
    return jsonify({"members": out, "total": len(out), "code": store.plaza_code()})


@app.get("/admin/characters")
def characters():
    """これまでに作った案内アニマルの一覧（スタッフ用。好きなものも出る）。"""
    staff_only()
    rows = []
    for token, r in store.list_results():
        t = type_info(r.get("type_code", ""))
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
            "dummy": bool(r.get("mock")),
        })
    rows.sort(key=lambda x: x["serial"], reverse=True)
    return render_template("admin/characters.html", rows=rows, show_dummy=False)


# ===== カードの削除（2026-10-02） =====
# 管理者画面の「これまでの案内アニマル」から、選んだカード・すべてのカードを消せる。
# 消すときは削除用のパスワードが要る（DELETE_PASSWORD。上の設定のところで読む）。


@app.post("/api/cards/delete")
def cards_delete():
    staff_only()
    body = request.get_json(silent=True) or {}
    if not DELETE_PASSWORD:
        return jsonify({"ok": False, "reason": "削除用のパスワードが設定されていません（.env の DELETE_PASSWORD）"}), 500
    if not secrets.compare_digest(str(body.get("password", "")), DELETE_PASSWORD):
        write_log({"event": "delete_refused", "by": session.get("admin_email", "local")})
        return jsonify({"ok": False, "reason": "パスワードがちがいます"}), 403
    if body.get("all"):
        tokens = [t for t, _ in store.list_results()]
    else:
        tokens = [t for t in (body.get("tokens") or []) if isinstance(t, str) and TOKEN_RE.match(t)]
    if not tokens:
        return jsonify({"ok": False, "reason": "消すカードが選ばれていません"}), 400
    n = 0
    for token in tokens:
        r = store.delete_result(token)
        if r is None:
            continue
        img = RESULT_DIR / r.get("image_file", f"{token}.png")
        if img.parent == RESULT_DIR and img.exists():
            img.unlink()
        n += 1
    if body.get("all"):
        store.reset_serial()   # すべて消したら、次のカードは No.0001 から（2026-10-02 ゆーしん）
    write_log({"event": "delete", "count": n, "all": bool(body.get("all")), "by": session.get("admin_email", "local")})
    return jsonify({"ok": True, "deleted": n})


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
    if ra["type_code"] not in TYPES or rb["type_code"] not in TYPES:
        return jsonify({"ok": False, "reason": "このカードは相性ではなく、バトルで遊べるよ"}), 400
    m = match(ra["type_code"], rb["type_code"])
    write_log({"event": "match", "a": ra["serial"], "b": rb["serial"], "score": m["score"]})
    return jsonify({"ok": True, "a": TYPES[ra["type_code"]]["name"], "b": TYPES[rb["type_code"]]["name"], **m})


# ===== バトル（2026-10-02 案2）=====
# パスポート（結果ページ）から、メンバーが作った動物バトルで戦う。中身は static/battle/ の quiz.js・battle.js をそのまま使う。
# 相手はコンピューター（ランダム）か、友だちのパスポート番号（?vs=番号）。

@app.get("/battle/<token>")
def battle_page(token: str):
    r = load_result(token)
    if not r.get("battle"):
        abort(404)
    enemy = None
    vs = request.args.get("vs", "")
    if vs:
        found = store.find_by_serial(int(vs)) if vs.isdigit() else None
        if not found or not found[1].get("battle"):
            return render_template("battle.html", r=r, token=token, enemy=None,
                                   error=f"No.{vs} のパスポートは見つからないよ。番号をたしかめてね"), 404
        e = found[1]
        if e["serial"] == r["serial"]:
            return render_template("battle.html", r=r, token=token, enemy=None,
                                   error="自分の番号が入っているよ。友だちのパスポートの番号を入れてね"), 400
        enemy = {"result": e["battle"], "month": e["month"], "serial": e["serial"], "monster": e.get("monster", ""),
                 "image_file": e.get("image_file", "")}
    else:
        write_log({"event": "battle", "serial": r["serial"], "vs": "cpu"})
    return render_template("battle.html", r=r, token=token, enemy=enemy, error="")


@app.post("/api/battle/wait")
def battle_wait():
    """友人戦の待ち合わせ（2026-10-02 ゆーしん「お互い正しいときだけマッチが始まる」）。
    2人とも相手の番号を入れて待っているときだけ ready=true。待っている間、画面から2秒ごとに呼ばれる。"""
    body = request.get_json(silent=True) or {}
    token = str(body.get("token", ""))
    r = store.get_result(token) if TOKEN_RE.match(token) else None
    try:
        vs = int(body.get("vs"))
    except (TypeError, ValueError):
        vs = 0
    if not r or not vs or vs == r["serial"]:
        return jsonify({"ok": False}), 400
    if body.get("leave"):
        store.battle_leave(r["serial"])
        return jsonify({"ok": True})
    store.battle_wait(r["serial"], vs)
    ready = store.battle_waiting_for(vs) == r["serial"]
    if not ready:
        return jsonify({"ok": True, "ready": False})
    m = store.pvp_start(r["serial"], vs)
    write_log({"event": "battle", "serial": r["serial"], "vs": vs, "match": m["id"]})
    return jsonify({"ok": True, "ready": True, "match": m["id"], "seed": m["seed"],
                    "side": "lo" if r["serial"] == m["lo"] else "hi"})


def _pvp_side(body_or_args) -> tuple[str, str] | None:
    """試合IDとトークンから、その人が lo と hi のどちらかを返す（その試合の2人だけが書きこめる）。"""
    mid, token = str(body_or_args.get("match", "")), str(body_or_args.get("token", ""))
    r = store.get_result(token) if TOKEN_RE.match(token) else None
    m = store.pvp_get(mid) if re.match(r"^[0-9a-f]{16}$", mid) else None
    if not r or not m or r["serial"] not in (m["lo"], m["hi"]):
        return None
    return mid, ("lo" if r["serial"] == m["lo"] else "hi")


@app.post("/api/pvp/act")
def pvp_act():
    """友人戦：選んだ技（pick）・タイミングの結果（qte）・終わり（done）を送る。"""
    body = request.get_json(silent=True) or {}
    who = _pvp_side(body)
    if not who:
        return jsonify({"ok": False}), 403
    mid, side = who
    kind = body.get("kind")
    try:
        rnd = int(body.get("round", 0))
        if kind == "pick":
            store.pvp_set(mid, {"picks": {str(rnd): {side: int(body["value"])}}})
        elif kind == "qte":
            store.pvp_set(mid, {"qte": {f"{rnd}-{int(body['step'])}": float(body["value"])}})
        elif kind == "done":
            store.pvp_set(mid, {"done": True})
        else:
            return jsonify({"ok": False}), 400
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False}), 400
    return jsonify({"ok": True})


@app.get("/api/pvp/state")
def pvp_state():
    """友人戦：いまの試合の状態（2人の技・タイミングの結果）。画面から短い間隔で呼ばれる。"""
    who = _pvp_side(request.args)
    if not who:
        return jsonify({"ok": False}), 403
    m = store.pvp_get(who[0])
    return jsonify({"ok": True, "picks": m.get("picks", {}), "qte": m.get("qte", {}), "done": m.get("done", False)})


@app.get("/api/stats")
def stats():
    """試してもらった結果のまとめ。"""
    staff_only()
    return jsonify({"cards": store.count_results(), "refused": store.count_events("refused"),
                    "matches": store.count_events("match")})


if __name__ == "__main__":
    print("ダミーモード（AIを使わない）" if is_mock() else f"AI：{TEXT_MODEL} / {IMAGE_MODEL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8120)), debug=False)

"""データの保存先（Firestore）。2026-10-01にファイル保存からFirebaseへ切り替えた（ゆーしん「データベースはfirebaseで」）。

案内アニマルの絵だけは、今までどおりサーバーの data/results/ に保存する
（Firebase Storageは新しいプロジェクトだと従量課金プランが必要なため）。

コレクション（FIRESTORE_PREFIX を頭に付ける。手元で試すときは "dev_" にして本番と混ぜない）
  results/{token}        カード1枚ごとの結果（タイプ・案内アニマル・ひとこと・運勢・絵のファイル名など）
  plaza_members/{token}  広場にいる案内アニマル（入った時刻）
  settings/plaza         広場のあいことば
  settings/shop          お店のあいことば
  counters/cards         カードの通し番号
  events/{自動}          作った・断った・相性・広場などの記録
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # 単体で読み込まれても .env が効くように

import os
import secrets
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore

_db = None
PREFIX = os.environ.get("FIRESTORE_PREFIX", "")


def db():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            key = os.environ.get("FIREBASE_KEY_PATH", "")
            cred = credentials.Certificate(os.path.expanduser(key)) if key else credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db


def col(name: str):
    return db().collection(PREFIX + name)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ===== カード =====

def next_serial() -> int:
    """カードの通し番号を1つ進めて返す（同時に作られても重ならないようトランザクションで）。"""
    ref = col("counters").document("cards")

    @firestore.transactional
    def bump(tx):
        snap = ref.get(transaction=tx)
        n = (snap.to_dict() or {}).get("n", 0) + 1 if snap.exists else 1
        tx.set(ref, {"n": n})
        return n

    return bump(db().transaction())


def save_result(token: str, result: dict) -> None:
    col("results").document(token).set(result)


def get_result(token: str) -> dict | None:
    snap = col("results").document(token).get()
    return snap.to_dict() if snap.exists else None


def list_results() -> list[tuple[str, dict]]:
    return [(s.id, s.to_dict()) for s in col("results").stream()]


def find_by_serial(serial: int) -> tuple[str, dict] | None:
    for s in col("results").where("serial", "==", serial).limit(1).stream():
        return s.id, s.to_dict()
    return None


def recent_monster_names(limit: int = 150) -> list[str]:
    q = col("results").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
    return [n for n in ((s.to_dict() or {}).get("monster") for s in q.stream()) if n]


def count_results() -> int:
    snap = col("counters").document("cards").get()
    return (snap.to_dict() or {}).get("n", 0) if snap.exists else 0


# ===== あいことば =====

def _code(doc: str, renew: bool = False) -> str:
    ref = col("settings").document(doc)
    snap = ref.get()
    code = (snap.to_dict() or {}).get("code", "") if snap.exists else ""
    if renew or not code:
        code = f"{secrets.randbelow(10000):04d}"
        ref.set({"code": code, "updated_at": now()})
    return code


def plaza_code(renew: bool = False) -> str:
    return _code("plaza", renew)


def shop_code(renew: bool = False) -> str:
    return _code("shop", renew)


# ===== 広場 =====

def plaza_members() -> list[tuple[str, str]]:
    """(token, 入った時刻) を入った順に。"""
    rows = [(s.id, (s.to_dict() or {}).get("joined_at", "")) for s in col("plaza_members").stream()]
    return sorted(rows, key=lambda r: r[1])


def in_plaza(token: str) -> bool:
    return col("plaza_members").document(token).get().exists


def plaza_join(token: str) -> bool:
    """入れたら True、もういたら False。"""
    ref = col("plaza_members").document(token)
    if ref.get().exists:
        return False
    ref.set({"joined_at": now()})
    return True


def plaza_leave(token: str) -> None:
    col("plaza_members").document(token).delete()


def plaza_clear() -> int:
    n = 0
    for s in col("plaza_members").stream():
        s.reference.delete()
        n += 1
    return n


# ===== 記録 =====

def log(entry: dict) -> None:
    col("events").add({**entry, "at": now()})


def count_events(event: str) -> int:
    return sum(1 for _ in col("events").where("event", "==", event).stream())


# ===== チケット（2026-10-01） =====
# チケット1枚に1つのページ（/12-K7QP の形）。番号の後ろの4文字は推測できない合言葉で、QRにだけ入っている。
# 1枚1回だけ使える。答え終わったら受け取りの時間の枠を決めて保存する。
import random  # noqa: E402

TICKET_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 見まちがえやすい 0 O 1 I は使わない


def create_tickets(n: int) -> list[dict]:
    """チケットを n 枚作る。番号は今までの続きから。"""
    ref = col("counters").document("tickets")
    snap = ref.get()
    start = ((snap.to_dict() or {}).get("n", 0) if snap.exists else 0) + 1
    out = []
    batch = db().batch()
    rng = random.SystemRandom()
    for num in range(start, start + n):
        t = {"number": num, "secret": "".join(rng.choice(TICKET_CHARS) for _ in range(4)),
             "status": "unused", "created_at": now()}
        batch.set(col("tickets").document(str(num)), t)
        out.append(t)
    batch.set(ref, {"n": start + n - 1})
    batch.commit()
    return out


def get_ticket(num: int) -> dict | None:
    snap = col("tickets").document(str(num)).get()
    return snap.to_dict() if snap.exists else None


def list_tickets() -> list[dict]:
    return sorted((s.to_dict() for s in col("tickets").stream()), key=lambda t: t["number"])


def slot_settings() -> dict:
    """受け取りの枠の決まり。仮に10分ごとに10人まで（2026-10-02のミーティングで決め直す）。"""
    snap = col("settings").document("slots").get()
    d = snap.to_dict() if snap.exists else {}
    return {"minutes": d.get("minutes", 10), "capacity": d.get("capacity", 10), "lead": d.get("lead", 5)}


def claim_ticket(num: int, secret: str, token: str, serial: int) -> dict | None:
    """答え終わったチケットを「使った」にして、受け取りの枠を決める。もう使われていたら None。"""
    from datetime import timedelta

    tref = col("tickets").document(str(num))
    sref = col("counters").document("slots")
    st = slot_settings()

    @firestore.transactional
    def run(tx):
        t = tref.get(transaction=tx).to_dict()
        if not t or t["secret"] != secret or t["status"] != "unused":
            return None
        counts = sref.get(transaction=tx).to_dict() or {}
        # 今から lead 分後より後の、空きのある最初の枠
        base = datetime.now() + timedelta(minutes=st["lead"])
        m = st["minutes"]
        slot = base.replace(second=0, microsecond=0) + timedelta(minutes=(m - base.minute % m) % m)
        while counts.get(slot.strftime("%Y-%m-%d %H:%M"), 0) >= st["capacity"]:
            slot += timedelta(minutes=m)
        key = slot.strftime("%Y-%m-%d %H:%M")
        counts[key] = counts.get(key, 0) + 1
        tx.set(sref, counts)
        upd = {"status": "used", "token": token, "serial": serial, "slot": key, "used_at": now()}
        tx.update(tref, upd)
        return {**t, **upd}

    return run(db().transaction())


# ===== ダミーモード（2026-10-01） =====

def ai_mode() -> str:
    """"real"（Geminiで作る）か "dummy"（AIを使わない・0円）。既定は real。"""
    snap = col("settings").document("mode").get()
    return (snap.to_dict() or {}).get("mode", "real") if snap.exists else "real"


def set_ai_mode(mode: str) -> None:
    col("settings").document("mode").set({"mode": mode, "updated_at": now()})


# ===== カードの削除（2026-10-02） =====

def delete_result(token: str) -> dict | None:
    """カード1枚の記録を消す（広場にいれば広場からも出す）。消した記録を返す（絵のファイル名を知るため）。"""
    ref = col("results").document(token)
    snap = ref.get()
    if not snap.exists:
        return None
    ref.delete()
    col("plaza_members").document(token).delete()
    return snap.to_dict()


# ===== チケットの管理（2026-10-02） =====

def _release_slots(tickets: list[dict]) -> None:
    """使用済みチケットを消す・戻すときに、受け取り枠の人数を減らす。"""
    keys = [t["slot"] for t in tickets if t.get("slot")]
    if not keys:
        return
    ref = col("counters").document("slots")
    snap = ref.get()
    counts = (snap.to_dict() or {}) if snap.exists else {}
    for k in keys:
        if counts.get(k, 0) > 0:
            counts[k] -= 1
    ref.set({k: v for k, v in counts.items() if v > 0})


def delete_tickets(numbers: list[int]) -> int:
    found = [t for t in (get_ticket(n) for n in numbers) if t]
    for t in found:
        col("tickets").document(str(t["number"])).delete()
    _release_slots(found)
    return len(found)


def delete_all_tickets() -> int:
    """チケットを全部消して、番号を1から振り直せるようにする（受け取り枠の人数も0に）。"""
    n = 0
    for s in col("tickets").stream():
        s.reference.delete()
        n += 1
    col("counters").document("tickets").delete()
    col("counters").document("slots").delete()
    return n


def reset_tickets(numbers: list[int]) -> int:
    """使用済みのチケットを未使用に戻す（同じQRでもう一度診断できる）。作ったカードは消さない。"""
    from google.cloud.firestore_v1 import DELETE_FIELD
    used = [t for t in (get_ticket(n) for n in numbers) if t and t["status"] != "unused"]
    for t in used:
        col("tickets").document(str(t["number"])).update(
            {"status": "unused", "token": DELETE_FIELD, "serial": DELETE_FIELD, "slot": DELETE_FIELD, "used_at": DELETE_FIELD})
    _release_slots(used)
    return len(used)


def count_cards() -> int:
    """いま残っているカードの数（消したカードは数えない）。"""
    return sum(1 for _ in col("results").select([]).stream())


def reset_serial() -> None:
    """カードの通し番号を0に戻す（すべてのカードを消したとき。次のカードは No.0001 から）。"""
    col("counters").document("cards").delete()


# ===== 友人戦の待ち合わせ（2026-10-02） =====
# battle_wait/{自分の番号} = {vs: 相手の番号, at: 最後に待っていた時刻（秒）}。待っている間は2秒ごとに時刻を更新する。

def battle_wait(serial: int, vs: int) -> None:
    import time
    col("battle_wait").document(str(serial)).set({"vs": vs, "at": time.time()})


def battle_waiting_for(serial: int, max_age: float = 12.0) -> int | None:
    """その番号の人が、いま（max_age秒以内）だれを待っているか。待っていなければ None。"""
    import time
    snap = col("battle_wait").document(str(serial)).get()
    d = snap.to_dict() if snap.exists else None
    if not d or time.time() - d.get("at", 0) > max_age:
        return None
    return d.get("vs")


def battle_leave(serial: int) -> None:
    col("battle_wait").document(str(serial)).delete()


# ===== 友人戦の対戦（2026-10-02 ゆーしん「ポケモンバトルみたいに、相手と自分のやってることが合うように」） =====
# pvp/{試合ID} = {lo, hi（番号の小さい方・大きい方）, seed（乱数のたね）, created, done, picks: {"1": {"lo": 技, "hi": 技}}, qte: {"1-0": 倍率}}
# pvp_current/{lo}-{hi} = いまの試合ID。2人が同時に待ち合わせに成功しても、同じ試合に入るようにする。

def pvp_start(a: int, b: int, fresh: float = 120.0) -> dict:
    """2人の試合を始める（もう始まっていれば同じ試合を返す）。"""
    import time
    lo, hi = sorted((a, b))
    cur = col("pvp_current").document(f"{lo}-{hi}")

    @firestore.transactional
    def run(tx):
        snap = cur.get(transaction=tx)
        d = snap.to_dict() if snap.exists else None
        if d:
            m = col("pvp").document(d["id"]).get(transaction=tx).to_dict()
            if m and not m.get("done") and time.time() - m.get("created", 0) < fresh:
                return {**m, "id": d["id"]}
        mid = secrets.token_hex(8)
        m = {"lo": lo, "hi": hi, "seed": secrets.randbelow(2**31), "created": time.time(), "done": False, "picks": {}, "qte": {}}
        tx.set(col("pvp").document(mid), m)
        tx.set(cur, {"id": mid})
        return {**m, "id": mid}

    return run(db().transaction())


def pvp_get(mid: str) -> dict | None:
    snap = col("pvp").document(mid).get()
    return snap.to_dict() if snap.exists else None


def pvp_set(mid: str, data: dict) -> None:
    """入れ子のまま足しこむ（キーに数字や「-」が入るので、"a.b" の形の更新は使わない）。"""
    col("pvp").document(mid).set(data, merge=True)

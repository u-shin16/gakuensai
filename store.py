"""データの保存先（Firestore）。2026-10-01にファイル保存からFirebaseへ切り替えた（ゆーしん「データベースはfirebaseで」）。

守り神の絵だけは、今までどおりサーバーの data/results/ に保存する
（Firebase Storageは新しいプロジェクトだと従量課金プランが必要なため）。

コレクション（FIRESTORE_PREFIX を頭に付ける。手元で試すときは "dev_" にして本番と混ぜない）
  results/{token}        カード1枚ごとの結果（タイプ・守り神・ひとこと・運勢・絵のファイル名など）
  plaza_members/{token}  広場にいる守り神（入った時刻）
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

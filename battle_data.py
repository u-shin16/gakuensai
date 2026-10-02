"""動物バトル診断（メンバー作）の質問と判定を、サーバー側でも使えるように Python に写したもの。2026-10-02

元は static/battle/quiz.js（https://github.com/kd1427248-create/animal-battle-quiz ef25461）。
誕生月と6問（4択）から、動物タイプ5種・ステータスの上下・技が決まる。乱数は使わない（同じ答えなら同じ結果）。
quiz.js を写し直したら `python3 battle_data.py --check` で全4096通りが一致するか確かめる。
"""

from __future__ import annotations

import random

TYPE_ORDER = ["ネコ科", "イヌ科", "大型", "鳥類", "爬虫類"]
STAT_ORDER = ["攻撃", "守備", "HP"]
ATTACK_SKILLS = ["強打", "連撃", "急所狙い", "吸収", "貫通"]
SKILL_ORDER = ["強打", "連撃", "急所狙い", "吸収", "貫通", "ガード", "気合", "硬化", "毒", "弱体", "反撃"]


def _o(label, type2, type1, stat, attack, support):
    return {"label": label, "type2": type2, "type1": type1, "stat": stat, "attack": attack, "support": support}


QUESTIONS = [
    {"prompt": "宝箱を見つけた！どうする？", "options": [
        _o("すぐに開ける", "ネコ科", "イヌ科", "攻撃", "急所狙い", "気合"),
        _o("罠を調べてから開ける", "鳥類", "爬虫類", "守備", "貫通", "ガード"),
        _o("仲間と相談して開ける", "イヌ科", "大型", "HP", "吸収", "硬化"),
        _o("見張りを立てて様子見", "大型", "鳥類", "守備", "強打", "反撃")]},
    {"prompt": "ライバルに勝負を挑まれた！", "options": [
        _o("受けて立つ", "ネコ科", "大型", "攻撃", "強打", "気合"),
        _o("作戦を練ってから", "爬虫類", "鳥類", "攻撃", "連撃", "反撃"),
        _o("ルールを確認する", "鳥類", "イヌ科", "守備", "貫通", "弱体"),
        _o("みんなの動きを見て合わせる", "イヌ科", "大型", "守備", "吸収", "硬化")]},
    {"prompt": "長い道のりを行くなら？", "options": [
        _o("全力で駆け抜ける", "ネコ科", "鳥類", "攻撃", "連撃", "気合"),
        _o("ペースを守って進む", "イヌ科", "大型", "HP", "吸収", "ガード"),
        _o("近道や裏道を探す", "爬虫類", "ネコ科", "守備", "急所狙い", "毒"),
        _o("重い荷物も背負って行く", "大型", "イヌ科", "守備", "強打", "硬化")]},
    {"prompt": "みんなで鍋を囲む。あなたは？", "options": [
        _o("具材を取り合う", "ネコ科", "爬虫類", "攻撃", "急所狙い", "弱体"),
        _o("みんなに取り分ける", "イヌ科", "大型", "HP", "吸収", "反撃"),
        _o("こっそり好物を確保", "爬虫類", "鳥類", "守備", "連撃", "毒"),
        _o("全体を見て火加減を調整", "鳥類", "イヌ科", "HP", "貫通", "弱体")]},
    {"prompt": "苦手な相手が現れたら？", "options": [
        _o("正面からぶつかる", "大型", "ネコ科", "攻撃", "強打", "反撃"),
        _o("距離をとって観察", "鳥類", "爬虫類", "HP", "貫通", "弱体"),
        _o("軽くかわして逃げる", "ネコ科", "鳥類", "HP", "急所狙い", "ガード"),
        _o("弱点を探って仕掛ける", "爬虫類", "イヌ科", "攻撃", "連撃", "毒")]},
    {"prompt": "理想の勝ち方は？", "options": [
        _o("一撃で決める", "大型", "ネコ科", "攻撃", "急所狙い", "気合"),
        _o("じわじわ追い詰める", "爬虫類", "大型", "HP", "連撃", "毒"),
        _o("無傷で勝つ", "鳥類", "ネコ科", "守備", "貫通", "ガード"),
        _o("最後まで立っていた者が勝ち", "イヌ科", "大型", "HP", "吸収", "硬化")]},
]

SKILL_NOTES = {
    "強打": "タイミングよく押すと最大1.8倍", "連撃": "3回当たる", "急所狙い": "会心が出やすいが外れやすい",
    "吸収": "与えたダメージの3割を回復", "貫通": "相手の守備を半分無視", "ガード": "次に受けるダメージを65%軽減",
    "気合": "2ターン、威力+45%", "硬化": "3ターン、守備+70%", "毒": "3ターン、少しずつダメージ",
    "弱体": "2ターン、相手の攻撃−20%", "反撃": "次に受けたダメージの55%を返す",
}
TYPE_SKILLS = {"ネコ科": "身かわし", "イヌ科": "遠吠え", "大型": "根を張る", "鳥類": "追い風", "爬虫類": "封じ"}
MONTH_SKILLS = ["初日の出", "雪化粧", "桜吹雪", "春風", "新緑", "梅雨", "夏祭り", "入道雲", "月見", "紅葉", "木枯らし", "冬至"]


def _rotate(order, shift):
    n = shift % len(order)
    return order[n:] + order[:n]


def _pick_by_score(scores, order, shift):
    target = max(scores[k] for k in order)
    return next(k for k in _rotate(order, shift) if scores[k] == target)


def _pick_top(scores, order, shift, count):
    rank = {k: i for i, k in enumerate(_rotate(order, shift))}
    return sorted(order, key=lambda k: (-scores[k], rank[k]))[:count]


def judge(answers: list[int]) -> dict:
    """quiz.js の judge() と同じ。answers は6問ぶんの 0〜3。"""
    if len(answers) != len(QUESTIONS) or any(a not in (0, 1, 2, 3) for a in answers):
        raise ValueError("回答は6問ぶん（0〜3）必要です")
    shift = sum(answers)
    types = {k: 0 for k in TYPE_ORDER}
    stats = {k: 0 for k in STAT_ORDER}
    skills = {k: 0 for k in SKILL_ORDER}
    for qi, choice in enumerate(answers):
        o = QUESTIONS[qi]["options"][choice]
        types[o["type2"]] += 2
        types[o["type1"]] += 1
        stats[o["stat"]] += 1
        skills[o["attack"]] += 1
        skills[o["support"]] += 1
    typ = _pick_by_score(types, TYPE_ORDER, shift)
    stat_up = _pick_by_score(stats, STAT_ORDER, shift)
    rest = [k for k in STAT_ORDER if k != stat_up]
    stat_down = next(k for k in _rotate(STAT_ORDER, shift) if k in rest and all(stats[k] <= stats[o] for o in rest))
    attack = _pick_by_score(skills, ATTACK_SKILLS, shift)
    others = _pick_top(skills, [k for k in SKILL_ORDER if k != attack], shift, 2)
    return {"type": typ, "statUp": stat_up, "statDown": stat_down,
            "statFlat": next(k for k in STAT_ORDER if k not in (stat_up, stat_down)),
            "attack": attack, "others": others, "skills": [attack, *others]}


def questions_for_page() -> list[dict]:
    return [{"q": q["prompt"], "options": [o["label"] for o in q["options"]]} for q in QUESTIONS]


def random_answers() -> list[int]:
    return [random.randrange(4) for _ in QUESTIONS]


if __name__ == "__main__":
    import itertools
    import json
    import subprocess
    import sys
    from pathlib import Path

    if "--check" in sys.argv:
        js = Path(__file__).parent / "static" / "battle" / "quiz.js"
        combos = [list(c) for c in itertools.product(range(4), repeat=len(QUESTIONS))]
        code = (f"const Q=require({json.dumps(str(js))});const out=[];"
                f"for(const a of {json.dumps(combos)}){{const r=Q.judge(a);out.push([r.type,r.statUp,r.statDown,r.attack,...r.others]);}}"
                "console.log(JSON.stringify(out));")
        out = json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)
        bad = 0
        for a, j in zip(combos, out):
            r = judge(a)
            if [r["type"], r["statUp"], r["statDown"], r["attack"], *r["others"]] != j:
                bad += 1
        print(f"{len(combos)}通り中 {len(combos) - bad} 通り一致、不一致 {bad}")


# ===== 5つの動物タイプのカード・結果ページ用の中身（2026-10-02） =====
# 16タイプの性格診断のかわり。運勢はタイプごとの決まった文（AIが書く運勢の手本になる）。
# animals は、AIが描く動物のもと。同じタイプでも人とかぶらないよう、ここからランダムに選ぶ。
ANIMAL_TYPES = {
    "ネコ科": {
        "name": "ネコ科タイプ", "kana": "ねこか", "color": "#d9822b", "hue": "warm orange and amber",
        "motif": "swift, sharp-eyed and graceful", "element": "ひかり",
        "desc": "思い立ったらすぐ動ける、すばやい行動派。ここぞという場面で一気に決める。",
        "strong": "チャンスを見のがさない", "weak": "あきっぽいところがある",
        "aruaru": "気づいたら、もう走り出している。",
        "animals": ["ライオン", "トラ", "チーター", "ヒョウ", "ユキヒョウ", "オセロット", "サーバル", "ジャガー", "オオヤマネコ", "スナネコ"],
        "advice": ("気になる相手には、自分から声をかける傾向があります。思い切って誘うと、楽しい時間が過ごせるでしょう。",
                   "一緒にいると場が明るくなる、頼れる存在です。相手の話を最後まで聞くと、信頼がさらに深まるでしょう。",
                   "集中したときの速さはだれにも負けません。短い時間で区切ってとり組むと、結果が出やすいでしょう。",
                   "ほしい物を見つけると、すぐ手に入れたくなることも。一晩おいて考えると、むだづかいが減るでしょう。"),
    },
    "イヌ科": {
        "name": "イヌ科タイプ", "kana": "いぬか", "color": "#b5651d", "hue": "warm brown and cream",
        "motif": "loyal, friendly and dependable", "element": "だいち",
        "desc": "仲間を大切にする、頼れるチームプレイヤー。みんなで力を合わせるのが得意。",
        "strong": "まわりと息を合わせられる", "weak": "ひとりで決めるのが苦手",
        "aruaru": "グループの連絡は、だいたい自分が回している。",
        "animals": ["オオカミ", "キツネ", "フェネック", "シバイヌ", "ゴールデンレトリバー", "ホッキョクギツネ", "タヌキ", "リカオン", "コヨーテ", "ハスキー"],
        "advice": ("一度好きになると、まっすぐ大切にする傾向があります。素直な気持ちを伝えると、関係が深まるでしょう。",
                   "困っている人を放っておけない、面倒見のよい人です。ときには頼ってみると、もっと仲良くなれるでしょう。",
                   "みんなと一緒だと力が出るタイプです。仲間と教え合うと、苦手なこともぐんと進むでしょう。",
                   "人のためにお金を使うことが多いようです。自分へのごほうびも決めておくと、満足度が上がるでしょう。"),
    },
    "大型": {
        "name": "大型どうぶつタイプ", "kana": "おおがた", "color": "#6b7f3a", "hue": "deep olive green and earthy brown",
        "motif": "mighty, calm and steady", "element": "もり",
        "desc": "どっしり構えた、ゆるがない安心感の持ち主。最後まであきらめずに立っている。",
        "strong": "ねばり強くて、頼りがいがある", "weak": "動き出すまでに時間がかかる",
        "aruaru": "みんながあわてていても、なぜか落ち着いている。",
        "animals": ["ゾウ", "サイ", "カバ", "ゴリラ", "ヒグマ", "バイソン", "キリン", "ホッキョクグマ", "ヘラジカ", "マンモス"],
        "advice": ("ゆっくり時間をかけて、信頼を育てる傾向があります。小さな約束を守り続けると、気持ちが伝わるでしょう。",
                   "いるだけで安心される、みんなの支えです。自分から話しかけると、新しい友だちが増えるでしょう。",
                   "コツコツ続ける力は、だれよりも強いです。毎日同じ時間にとり組むと、大きな成果になるでしょう。",
                   "大きな買い物の前に、しっかり考える傾向があります。少しずつためると、ほしい物に手が届くでしょう。"),
    },
    "鳥類": {
        "name": "鳥類タイプ", "kana": "ちょうるい", "color": "#2f7fb8", "hue": "sky blue and white",
        "motif": "free, perceptive and far-seeing", "element": "かぜ",
        "desc": "高いところから全体を見わたす、観察の名人。先を読んで動ける。",
        "strong": "全体を見て、先を読める", "weak": "考えすぎて動けないことがある",
        "aruaru": "みんなが気づく前に、もう気づいている。",
        "animals": ["ワシ", "フクロウ", "ペンギン", "フラミンゴ", "コンゴウインコ", "ハヤブサ", "オオハシ", "クジャク", "ハクチョウ", "シマエナガ"],
        "advice": ("相手の気持ちの変化に、すぐ気づく傾向があります。気づいたことを言葉にすると、距離が縮まるでしょう。",
                   "ほどよい距離で、みんなを見守るタイプです。ときには輪の真ん中に入ると、もっと楽しくなるでしょう。",
                   "計画を立てるのがとても上手です。先に全体の流れを決めておくと、迷わず進められるでしょう。",
                   "値段をよく比べる、かしこい買い物上手です。本当にほしい物を決めておくと、満足できるでしょう。"),
    },
    "爬虫類": {
        "name": "爬虫類タイプ", "kana": "はちゅうるい", "color": "#3f8f6b", "hue": "emerald green and teal",
        "motif": "patient, clever and mysterious", "element": "みず",
        "desc": "じっと機会を待てる、作戦上手。ここぞという時に、じわじわ効いてくる。",
        "strong": "落ち着いて作戦を立てられる", "weak": "本音を見せるのに時間がかかる",
        "aruaru": "あとになって「実はあれ、作戦だった」と言う。",
        "animals": ["カメ", "ワニ", "カメレオン", "イグアナ", "ヤモリ", "コモドオオトカゲ", "リクガメ", "ウミガメ", "エリマキトカゲ", "ボールパイソン"],
        "advice": ("仲良くなるまで、少し時間がかかる傾向があります。自分のことを少しずつ話すと、ぐっと近づけるでしょう。",
                   "深く長く付き合える、信頼される友だちです。好きな話題を共有すると、話が止まらなくなるでしょう。",
                   "よく考えてから進める、作戦タイプです。最初に作戦を紙に書き出すと、効率よく進むでしょう。",
                   "お金の使い方が堅実な傾向があります。目標の金額を決めてためると、楽しみが増えるでしょう。"),
    },
}

"""アニマル性格診断と、2人の相性診断。2026-11-10

学園祭企画まとめ（PDF）の「パスポートで遊べるコンテンツ」のうち、
  ・アニマルMBTI：動物で例えるなら、あなたは何か（レーダーチャートで見せる）
  ・相性診断：友だちのパスポートのQRを読むと、2人の相性がわかる
をパスポート（結果ページ /r/<token>）の中で遊べるようにしたもの。発行の質問（誕生月＋6問）とは別に、発行後に答える。

画面には「MBTI」の名前を出さない（商標。16タイプのときと同じ方針）。名前は「アニマル性格診断」。
質問・動物・文はすべてオリジナル。

質問は16タイプ版（types_data.QUESTIONS）の10問に2問足した12問。4つの軸に3問ずつで、多数決なので引き分けにならない。
相性の点数は types_data.match（理由つき）をそのまま使う。
"""

from __future__ import annotations

import math

from types_data import AXIS_WORDS, QUESTIONS as BASE_QUESTIONS, match

AXES = ("EI", "SN", "TF", "JP")

QUESTIONS = [
    *[{"axis": q["axis"], "q": q["q"], "a": q["a"], "b": q["b"]} for q in BASE_QUESTIONS],
    {"axis": "TF", "q": "友だちが描いた絵、正直いまいち。なんて言う？",
     "a": ("直すといいところを言う", "T"), "b": ("いいところをほめる", "F")},
    {"axis": "JP", "q": "宿題や課題は、いつやる？",
     "a": ("早めに終わらせる", "J"), "b": ("ぎりぎりで一気にやる", "P")},
]
# 1軸3問ずつになっているか（足し忘れ・消し忘れの確認）
assert all(sum(q["axis"] == ax for q in QUESTIONS) == 3 for ax in AXES)

# emoji：絵のかわり（どの端末でも出る絵文字だけ）
# catch：ひとことで言うと
ANIMALS = {
    "ESTJ": {"animal": "ライオン", "emoji": "🦁", "catch": "群れをまとめる王さま",
             "desc": "やると決めたら、みんなを引っぱってゴールまで連れていく。まわりからいつも頼られている。",
             "aruaru": "グループで何か決めるとき、気づけば司会をしている。", "strong": "決めたことをやり切る", "weak": "予定がくずれるとイライラ"},
    "ESTP": {"animal": "チーター", "emoji": "🐆", "catch": "考えるより先に走りだす",
             "desc": "チャンスを見つけたら一瞬でスタート。体を動かしながら考えるタイプ。",
             "aruaru": "説明の途中で、もうやり始めている。", "strong": "ピンチに強い", "weak": "飽きるのも速い"},
    "ESFJ": {"animal": "イヌ", "emoji": "🐕", "catch": "みんなのそばにいる世話役",
             "desc": "まわりの人がうれしそうだと、自分もうれしい。困っている人に真っ先に気づく。",
             "aruaru": "みんなの分の飲み物を、気づけば配っている。", "strong": "気くばり", "weak": "頼まれると断れない"},
    "ESFP": {"animal": "イルカ", "emoji": "🐬", "catch": "その場を楽しくするムードメーカー",
             "desc": "いるだけで場が明るくなる。楽しいことを見つける天才。",
             "aruaru": "写真を撮るとき、いつも真ん中にいる。", "strong": "盛り上げ上手", "weak": "楽しいとお金と時間を使いすぎる"},
    "ENTJ": {"animal": "ワシ", "emoji": "🦅", "catch": "高いところからゴールをねらう",
             "desc": "大きな目標を決めて、最短ルートで向かう。勝負ごとには本気。",
             "aruaru": "ゲームでも、やるからには1位をねらう。", "strong": "決めるのが速い", "weak": "人にもきびしくなりがち"},
    "ENTP": {"animal": "キツネ", "emoji": "🦊", "catch": "アイデアいっぱいのいたずら名人",
             "desc": "「こうしたらおもしろくない？」が止まらない。ふつうのやり方だと物足りない。",
             "aruaru": "話しているうちに、話題がどんどん変わっていく。", "strong": "発想力", "weak": "最後まで仕上げるのが苦手"},
    "ENFJ": {"animal": "ゾウ", "emoji": "🐘", "catch": "群れを守るやさしい力持ち",
             "desc": "人のいいところを見つけて、のばすのが得意。みんなの気持ちを一つにする。",
             "aruaru": "落ちこんでいる人を見ると、放っておけない。", "strong": "人をやる気にさせる", "weak": "ひとりで抱えこむ"},
    "ENFP": {"animal": "カワウソ", "emoji": "🦦", "catch": "好奇心でできている",
             "desc": "気になったら、もう動いている。だれとでもすぐ仲良くなれる。",
             "aruaru": "おもしろそうなものを見つけると、予定を忘れる。", "strong": "だれとでも仲良くなれる", "weak": "興味が次々変わる"},
    "ISTJ": {"animal": "ビーバー", "emoji": "🦫", "catch": "こつこつ積み上げる建築家",
             "desc": "毎日の小さな積み重ねで、気づけば大きなものを作っている。約束は必ず守る。",
             "aruaru": "一度決めた習慣は、雨の日でも続ける。", "strong": "信頼される", "weak": "急な変更が苦手"},
    "ISFJ": {"animal": "ペンギン", "emoji": "🐧", "catch": "仲間をそっとあたためる",
             "desc": "目立たないところで、みんなを支えている。小さな変化によく気づく。",
             "aruaru": "友だちの髪型が変わったら、すぐ気づく。", "strong": "思いやり", "weak": "自分のことを後回しにする"},
    "ISTP": {"animal": "ネコ", "emoji": "🐈", "catch": "器用なマイペース",
             "desc": "口数は少ないけど、手を動かせばだれより器用。自分のペースは崩さない。",
             "aruaru": "説明書より、さわって仕組みを確かめたい。", "strong": "いつも冷静", "weak": "気持ちを言葉にするのが苦手"},
    "ISFP": {"animal": "パンダ", "emoji": "🐼", "catch": "のんびりアーティスト",
             "desc": "自分の「好き」をなにより大事にする。いっしょにいると落ちつくと言われる。",
             "aruaru": "好きな景色や音楽の前で、時間を忘れる。", "strong": "センスがいい", "weak": "もめごとが苦手でだまりがち"},
    "INTJ": {"animal": "フクロウ", "emoji": "🦉", "catch": "夜の森の作戦家",
             "desc": "先の先まで読んでから動く。ひとりで考える時間が大事。",
             "aruaru": "始める前に、頭の中で何通りも試している。", "strong": "計画力", "weak": "説明をはぶきがち"},
    "INTP": {"animal": "タコ", "emoji": "🐙", "catch": "なぜなぜ研究家",
             "desc": "気になったことは、とことん考えぬく。頭の中はいつも実験中。",
             "aruaru": "「なんで？」が気になると、夜ふかししてでも調べる。", "strong": "分析力", "weak": "考えすぎて動けない"},
    "INFJ": {"animal": "クジラ", "emoji": "🐋", "catch": "深い海の聞き上手",
             "desc": "人の気持ちを深く読みとる。静かだけど、心の中には大きな思いがある。",
             "aruaru": "なぜか相談ごとが集まってくる。", "strong": "見ぬく力", "weak": "ひとりで疲れやすい"},
    "INFP": {"animal": "ウサギ", "emoji": "🐰", "catch": "夢見るロマンチスト",
             "desc": "心の中に大きな世界をもっている。やさしくて、人の痛みがわかる。",
             "aruaru": "考えごとをしていると、話しかけられても気づかない。", "strong": "想像力", "weak": "傷つきやすい"},
}
assert len(ANIMALS) == 16


def questions_for_page() -> list[dict]:
    """画面に出す質問。答えは "a" か "b" で返してもらう。"""
    return [{"q": q["q"], "a": q["a"][0], "b": q["b"][0]} for q in QUESTIONS]


def judge(answers: list[str]) -> dict:
    """12問の答え（"a"/"b"）から、4文字のコードと各側の点（0〜3）を出す。"""
    if len(answers) != len(QUESTIONS) or any(a not in ("a", "b") for a in answers):
        raise ValueError("12問ぶん a か b で答えてね")
    score = {c: 0 for c in "EISNTFJP"}
    for q, pick in zip(QUESTIONS, answers):
        score[q[pick][1]] += 1
    code = "".join(a if score[a] > score[b] else b for a, b in AXES)
    return {"code": code, "score": score}


# レーダーチャートの8本の線。向かい合う線が反対の性格になるように並べる（上がにぎやか、下がマイペース）
RADAR_ORDER = ["E", "S", "T", "J", "I", "N", "F", "P"]


def radar(score: dict, size: int = 300) -> dict:
    """レーダーチャートの点（SVG用）。0点でも真ん中につぶれないよう、半径の2割から始める。"""
    c, rmax = size / 2, size / 2 - 52
    pts, labels, grid = [], [], []
    for i, k in enumerate(RADAR_ORDER):
        ang = math.radians(-90 + 45 * i)
        v = score.get(k, 0) / 3
        r = rmax * (0.2 + 0.8 * v)
        pts.append(f"{c + r * math.cos(ang):.1f},{c + r * math.sin(ang):.1f}")
        lx, ly = c + (rmax + 26) * math.cos(ang), c + (rmax + 26) * math.sin(ang)
        labels.append({"x": round(lx, 1), "y": round(ly, 1), "text": AXIS_WORDS[k], "pt": score.get(k, 0),
                       "ex": round(c + rmax * math.cos(ang), 1), "ey": round(c + rmax * math.sin(ang), 1)})
    for f in (0.2, 0.4667, 0.7333, 1.0):   # 0点・1点・2点・3点の目もり
        grid.append(" ".join(f"{c + rmax * f * math.cos(math.radians(-90 + 45 * i)):.1f},"
                             f"{c + rmax * f * math.sin(math.radians(-90 + 45 * i)):.1f}" for i in range(8)))
    return {"size": size, "c": c, "points": " ".join(pts), "labels": labels, "grid": grid}


def best_partners(code: str, n: int = 2) -> list[dict]:
    ranked = sorted((c for c in ANIMALS if c != code), key=lambda c: (-match(code, c)["score"], c))
    return [ANIMALS[c] for c in ranked[:n]]


def payload(saved: dict) -> dict:
    """保存した {"code", "score"} に、画面に出す中身を足す。"""
    code = saved["code"]
    return {**ANIMALS[code], "code": code, "radar": radar(saved["score"]),
            "axes": [AXIS_WORDS[ch] for ch in code], "partners": best_partners(code)}


def pair(a: dict, b: dict) -> dict:
    """2人の相性。a・b は保存した {"code", "score"}。"""
    m = match(a["code"], b["code"])
    return {**m, "a": {k: ANIMALS[a["code"]][k] for k in ("animal", "emoji")},
            "b": {k: ANIMALS[b["code"]][k] for k in ("animal", "emoji")}}

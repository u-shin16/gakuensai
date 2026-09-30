"""質問・16タイプ・相性の中身。

4つの軸（それぞれ2問）で16タイプに分ける。
「MBTI」「16Personalities」の名前・質問文・タイプ名は使わない（商標）。すべてオリジナル。

軸：
  E/I  にぎやか ↔ マイペース
  S/N  じっさい ↔ ひらめき
  T/F  りくつ   ↔ きもち
  J/P  けいかく ↔ きまま
各軸の1問目を2点、2問目を1点にして、同点が起きないようにしている。
"""

QUESTIONS = [
    {"axis": "EI", "weight": 2, "q": "予定のない休みの日。どうする？",
     "a": ("だれかを誘って出かける", "E"), "b": ("家で好きなことをしてのんびり", "I")},
    {"axis": "SN", "weight": 2, "q": "新しいゲームや道具を手に入れたら？",
     "a": ("説明やルールを先に読む", "S"), "b": ("とりあえず触ってみる", "N")},
    {"axis": "TF", "weight": 2, "q": "友だちが落ちこんでいる。まずどうする？",
     "a": ("どうすれば解決するか一緒に考える", "T"), "b": ("とにかく話を聞いて気持ちに寄りそう", "F")},
    {"axis": "JP", "weight": 2, "q": "旅行に行くなら？",
     "a": ("行く場所と時間をしっかり決めておく", "J"), "b": ("行ってから気分で決める", "P")},
    {"axis": "EI", "weight": 1, "q": "初めて会う人が多い集まりでは？",
     "a": ("自分から話しかける", "E"), "b": ("話しかけられるのを待つ", "I")},
    {"axis": "SN", "weight": 1, "q": "聞いていて楽しいのは？",
     "a": ("本当にあった話", "S"), "b": ("「もしも〜だったら」の話", "N")},
    {"axis": "TF", "weight": 1, "q": "何かを決めるとき大事なのは？",
     "a": ("筋が通っているか", "T"), "b": ("みんなが気持ちよくいられるか", "F")},
    {"axis": "JP", "weight": 1, "q": "やらなきゃいけないことがあるとき",
     "a": ("早めに片づけて安心したい", "J"), "b": ("ギリギリで本気を出す", "P")},
]

AXIS_WORDS = {"E": "にぎやか", "I": "マイペース", "S": "じっさい", "N": "ひらめき",
              "T": "りくつ", "F": "きもち", "J": "けいかく", "P": "きまま"}

# motif：絵を描くAIに渡す、そのタイプらしさ（英語）
TYPES = {
    "ESTJ": {"name": "てきぱき隊長", "element": "ほのお", "motif": "commanding armored dragon knight",
             "desc": "決めたことをきっちりやり切る、頼れるまとめ役。", "strong": "段取りがうまい", "weak": "予定がくずれるとイライラしがち"},
    "ESTP": {"name": "スリル冒険家", "element": "でんき", "motif": "agile lightning fox",
             "desc": "考えるより先に体が動く行動派。", "strong": "ピンチに強い", "weak": "あきっぽい"},
    "ESFJ": {"name": "みんなのお世話係", "element": "ひかり", "motif": "warm glowing bird guardian",
             "desc": "まわりが笑顔だと自分もうれしくなる。", "strong": "気くばり", "weak": "頼まれると断れない"},
    "ESFP": {"name": "ムードメーカー", "element": "かぜ", "motif": "festive dancing wind sprite",
             "desc": "その場を一瞬で楽しくしてしまう。", "strong": "盛り上げ上手", "weak": "お金と時間を使いすぎる"},
    "ENTJ": {"name": "野望の司令官", "element": "やみ", "motif": "majestic shadow lion",
             "desc": "大きな目標に向かって一直線に進む。", "strong": "決めるのが速い", "weak": "人にもきびしくなりがち"},
    "ENTP": {"name": "ひらめき発明家", "element": "でんき", "motif": "mischievous inventor creature with gadgets",
             "desc": "新しいアイデアが次々とわいてくる。", "strong": "発想力", "weak": "最後まで仕上げるのが苦手"},
    "ENFJ": {"name": "熱血応援団長", "element": "ほのお", "motif": "radiant phoenix",
             "desc": "人のいいところを見つけて伸ばすのが得意。", "strong": "人をやる気にさせる", "weak": "ひとりで抱えこみすぎる"},
    "ENFP": {"name": "わくわく探検家", "element": "ひかり", "motif": "curious sparkling long-eared creature",
             "desc": "好奇心のかたまり。気になったらもう動いている。", "strong": "だれとでも仲良くなれる", "weak": "興味が次々変わる"},
    "ISTJ": {"name": "こつこつ職人", "element": "くさ", "motif": "sturdy ancient tree turtle",
             "desc": "決めたことをまじめに積み上げる。", "strong": "信頼される", "weak": "急な変更が苦手"},
    "ISFJ": {"name": "やさしい支え役", "element": "くさ", "motif": "gentle forest deer guardian",
             "desc": "気づかれないところで人を支えている。", "strong": "思いやり", "weak": "自分のことを後回しにする"},
    "ISTP": {"name": "クールな技術者", "element": "こおり", "motif": "sleek ice wolf with crystal blades",
             "desc": "口数は少ないけど、手を動かせばだれより器用。", "strong": "いつも冷静", "weak": "気持ちを言葉にするのが苦手"},
    "ISFP": {"name": "気ままなアーティスト", "element": "かぜ", "motif": "graceful feathered wind cat",
             "desc": "自分の「好き」をなにより大切にする。", "strong": "センスがいい", "weak": "もめごとが苦手でだまりがち"},
    "INTJ": {"name": "孤高の軍師", "element": "やみ", "motif": "mysterious owl strategist with glowing runes",
             "desc": "先の先まで読んでから動く。", "strong": "計画力", "weak": "説明をはぶきがち"},
    "INTP": {"name": "なぜなぜ博士", "element": "こおり", "motif": "curious crystal axolotl scholar",
             "desc": "気になったことはとことん考えぬく。", "strong": "分析力", "weak": "考えすぎて動けない"},
    "INFJ": {"name": "静かな予言者", "element": "みず", "motif": "serene water serpent oracle",
             "desc": "人の気持ちを深く読みとる。", "strong": "見ぬく力", "weak": "ひとりで疲れやすい"},
    "INFP": {"name": "夢見る詩人", "element": "みず", "motif": "dreamy jellyfish fairy",
             "desc": "心の中に大きな世界をもっている。", "strong": "想像力", "weak": "傷つきやすい"},
}


def decide_type(answers: list[str]) -> str:
    """answers は各質問で選んだ文字（'E' や 'I'）の並び。"""
    score = {c: 0 for c in "EISNTFJP"}
    for q, pick in zip(QUESTIONS, answers):
        score[pick] += q["weight"]
    return "".join(a if score[a] > score[b] else b for a, b in ("EI", "SN", "TF", "JP"))



def match(a: str, b: str) -> dict:
    """2タイプの相性。理由が説明できるように、足した点ごとに一言つける。"""
    score, reasons = 60, []
    if a[1] == b[1]:
        score += 12
        reasons.append("見ているものが同じで、話がかみ合う")
    if a[0] != b[0]:
        score += 8
        reasons.append("にぎやかとマイペースで、おたがいを補える")
    if a[2] == b[2]:
        score += 8
        reasons.append("大事にしているものが同じ")
    if a[3] != b[3]:
        score += 7
        reasons.append("けいかく派ときまま派で、ちょうどいいバランス")
    if not reasons:
        reasons.append("ちがうところだらけだから、いっしょにいると刺激になる")
    if score >= 90:
        title = "最強コンビ"
    elif score >= 80:
        title = "息ぴったり"
    elif score >= 70:
        title = "いいチーム"
    else:
        title = "刺激しあうライバル"
    return {"score": score, "title": title, "reasons": reasons}


def best_partners(code: str, n: int = 2) -> list[str]:
    ranked = sorted((c for c in TYPES if c != code), key=lambda c: -match(code, c)["score"])
    return [TYPES[c]["name"] for c in ranked[:n]]


def rival(code: str) -> str:
    """いちばん点が低い相手。悪く書かず「刺激しあう相手」として出す。"""
    return TYPES[min((c for c in TYPES if c != code), key=lambda c: match(code, c)["score"])]["name"]

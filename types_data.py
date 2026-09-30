"""質問・16タイプ・相性の中身。

4つの軸（それぞれ2問）で16タイプに分ける。
「MBTI」「16Personalities」の名前・質問文・タイプ名は使わない（商標）。すべてオリジナル。
タイプ名は子どもでも分かる単語を漢字で書き、kana（読みがな）を上に小さく出す（2026-09-30）。

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

# color：タイプのテーマ色（カードの枠に使う）
# hue：同じ色を英語の言葉で（絵を描くAIに渡す。色番号を渡すと絵に文字として描いてしまうため）
# motif：絵を描くAIに渡す、そのタイプらしさ（英語）。生き物の種類は書かない（ドラゴンばかりになったため。種類は CREATURES から毎回選ぶ）
TYPES = {
    "ESTJ": {"hue": "warm vermilion red", "color": "#D9483B", "name": "しっかり者", "kana": "しっかりもの", "element": "ほのお", "motif": "orderly and commanding, neat polished armor, carries a banner",
             "desc": "決めたことをきっちりやり切る、頼れるまとめ役。", "strong": "段取りがうまい", "weak": "予定がくずれるとイライラしがち"},
    "ESTP": {"hue": "bright orange", "color": "#F29E1F", "name": "行動派", "kana": "こうどうは", "element": "でんき", "motif": "agile and daring, always mid-leap, crackling with energy",
             "desc": "考えるより先に体が動く行動派。", "strong": "ピンチに強い", "weak": "あきっぽい"},
    "ESFJ": {"hue": "sunny yellow", "color": "#E8B923", "name": "世話焼きさん", "kana": "せわやきさん", "element": "ひかり", "motif": "warm and caring, carries a basket of gifts, gentle glow",
             "desc": "まわりが笑顔だと自分もうれしくなる。", "strong": "気くばり", "weak": "頼まれると断れない"},
    "ESFP": {"hue": "soft pink", "color": "#EE7FA8", "name": "盛り上げ役", "kana": "もりあげやく", "element": "かぜ", "motif": "festive and cheerful, dancing pose, ribbons and confetti",
             "desc": "その場を一瞬で楽しくしてしまう。", "strong": "盛り上げ上手", "weak": "お金と時間を使いすぎる"},
    "ENTJ": {"hue": "royal purple", "color": "#6C4AB6", "name": "負けず嫌い", "kana": "まけずぎらい", "element": "やみ", "motif": "ambitious and majestic, confident stance, royal cape",
             "desc": "大きな目標に向かって一直線に進む。", "strong": "決めるのが速い", "weak": "人にもきびしくなりがち"},
    "ENTP": {"hue": "teal", "color": "#1FA99E", "name": "ひらめき王", "kana": "ひらめきおう", "element": "でんき", "motif": "mischievous inventor, goggles and handmade gadgets",
             "desc": "新しいアイデアが次々とわいてくる。", "strong": "発想力", "weak": "最後まで仕上げるのが苦手"},
    "ENFJ": {"hue": "coral", "color": "#FF7A59", "name": "応援団長", "kana": "おうえんだんちょう", "element": "ほのお", "motif": "passionate cheerleader, raising a flag, radiant warm aura",
             "desc": "人のいいところを見つけて伸ばすのが得意。", "strong": "人をやる気にさせる", "weak": "ひとりで抱えこみすぎる"},
    "ENFP": {"hue": "apricot", "color": "#F5A623", "name": "知りたがり屋", "kana": "しりたがりや", "element": "ひかり", "motif": "curious explorer, backpack and magnifying glass, sparkling eyes",
             "desc": "好奇心のかたまり。気になったらもう動いている。", "strong": "だれとでも仲良くなれる", "weak": "興味が次々変わる"},
    "ISTJ": {"hue": "forest green", "color": "#4F8A4B", "name": "努力家", "kana": "どりょくか", "element": "くさ", "motif": "steady and hardworking, sturdy build, carries tools and a notebook",
             "desc": "決めたことをまじめに積み上げる。", "strong": "信頼される", "weak": "急な変更が苦手"},
    "ISFJ": {"hue": "mint green", "color": "#6DB38F", "name": "見守り役", "kana": "みまもりやく", "element": "くさ", "motif": "gentle protector, soft calm eyes, holding a lantern",
             "desc": "気づかれないところで人を支えている。", "strong": "思いやり", "weak": "自分のことを後回しにする"},
    "ISTP": {"hue": "cobalt blue", "color": "#3F86C2", "name": "器用な職人", "kana": "きようなしょくにん", "element": "こおり", "motif": "cool skilled craftsman, tool belt, precise and calm",
             "desc": "口数は少ないけど、手を動かせばだれより器用。", "strong": "いつも冷静", "weak": "気持ちを言葉にするのが苦手"},
    "ISFP": {"hue": "lavender", "color": "#B07CC6", "name": "のんびり屋", "kana": "のんびりや", "element": "かぜ", "motif": "easygoing artist, paintbrush and flowers, relaxed pose",
             "desc": "自分の「好き」をなにより大切にする。", "strong": "センスがいい", "weak": "もめごとが苦手でだまりがち"},
    "INTJ": {"hue": "deep indigo", "color": "#3D3B8E", "name": "作戦名人", "kana": "さくせんめいじん", "element": "やみ", "motif": "mysterious strategist, map and chess pieces, thoughtful gaze",
             "desc": "先の先まで読んでから動く。", "strong": "計画力", "weak": "説明をはぶきがち"},
    "INTP": {"hue": "sky blue", "color": "#5FA8D8", "name": "なぜなぜ博士", "kana": "なぜなぜはかせ", "element": "こおり", "motif": "curious scholar, stacks of books and a question-mark lamp",
             "desc": "気になったことはとことん考えぬく。", "strong": "分析力", "weak": "考えすぎて動けない"},
    "INFJ": {"hue": "navy blue", "color": "#2F6690", "name": "聞き上手", "kana": "ききじょうず", "element": "みず", "motif": "serene good listener, calm smile, soft ripples of water",
             "desc": "人の気持ちを深く読みとる。", "strong": "見ぬく力", "weak": "ひとりで疲れやすい"},
    "INFP": {"hue": "lilac", "color": "#9A86DB", "name": "夢見る人", "kana": "ゆめみるひと", "element": "みず", "motif": "dreamy storyteller, floating stars and a small book",
             "desc": "心の中に大きな世界をもっている。", "strong": "想像力", "weak": "傷つきやすい"},
}


def decide_type(answers: list[str]) -> str:
    """answers は各質問で選んだ文字（'E' や 'I'）の並び。"""
    score = {c: 0 for c in "EISNTFJP"}
    for q, pick in zip(QUESTIONS, answers):
        score[pick] += q["weight"]
    return "".join(a if score[a] > score[b] else b for a, b in ("EI", "SN", "TF", "JP"))


def axis_profile(answers: list[str]) -> list[str]:
    """同じタイプでも一人ひとり違う「傾きの強さ」。2問とも同じ側なら「はっきり」、分かれたら「少し」。
    少しの軸は、反対側の面も持っている（＝ギャップ）として文章に使う。"""
    score = {c: 0 for c in "EISNTFJP"}
    for q, pick in zip(QUESTIONS, answers):
        score[pick] += q["weight"]
    out = []
    for a, b in ("EI", "SN", "TF", "JP"):
        win, lose = (a, b) if score[a] > score[b] else (b, a)
        if score[lose] == 0:
            out.append(f"{AXIS_WORDS[win]}（はっきり）")
        else:
            out.append(f"{AXIS_WORDS[win]}（少し。{AXIS_WORDS[lose]}な面もある）")
    return out



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


# 占いのひとこと（恋愛・友情・勉強や仕事・お金）の元になる文。タイプごとに4つ。
# AIはこれを元に、好きなものは入れずに言い方だけ少し変える（全員同じ文にならないように。2026-09-30）。
# 2026-09-30：AIに一から書かせると「誰にでも当てはまる文」が混ざるため、元の文はこちらで決める。
ADVICE = {
    "ESTJ": ["デートの計画は完璧。でも寄り道も楽しんで", "集合場所を決めるのは、いつもあなた",
             "予定表どおりに進むと、気分がいい", "使い道はきっちり。ご褒美も予定に入れよう"],
    "ESTP": ["気になったら即声かけ。スピードが武器", "「今から行こう」で友達を連れ出す係",
             "本番に強いけど、準備はもう少しだけ", "欲しい！と思った瞬間がいちばん危ない"],
    "ESFJ": ["相手の好きなもの、ちゃんと覚えてる", "みんなの飲み物、気づけば配っている",
             "教えるのがうまい。自分の分も忘れずに", "人へのプレゼントには、つい奮発しがち"],
    "ESFP": ["一緒に笑える人が、いちばんの相手", "あなたがいると、その場が明るくなる",
             "楽しくなると一気に進むタイプ", "楽しいことへの出費は、ためらわない"],
    "ENTJ": ["好きな人にも、つい本気で勝負しちゃう", "目標を語ると、仲間がついてくる",
             "目標が決まった瞬間、スイッチが入る", "貯金も目標額を決めると強い"],
    "ENTP": ["会話が面白い人に、ぐっとひかれる", "変な遊びを思いつくのは、だいたいあなた",
             "アイデアは満点。仕上げまでがんばろう", "新しいガジェットに目がない"],
    "ENFJ": ["相手の夢を、本気で応援できる人", "落ちこんだ友達を、放っておけない",
             "誰かのためだと、力が倍になる", "人のために使うお金は、惜しまない"],
    "ENFP": ["気になる人のことは、全部知りたい", "初対面でも、5分で仲良くなれる",
             "気になった所から始めると、止まらない", "「おもしろそう」に弱いので要注意"],
    "ISTJ": ["小さな約束を守るのが、あなたの愛情", "何年たっても、変わらない友達でいる",
             "毎日の積み重ねで、いつの間にか上位に", "レシートは取っておくタイプ"],
    "ISFJ": ["さりげない気づかいが、いちばん伝わる", "友達の小さな変化に、真っ先に気づく",
             "ノートがきれいで、よく借りられる", "自分のことは後回し。たまには自分に"],
    "ISTP": ["言葉より、行動で気持ちを伝える", "壊れた物は、あなたのところに集まる",
             "手を動かすと、一気に分かる", "道具にはお金をかけてもいい派"],
    "ISFP": ["一緒にぼーっとできる人が、ちょうどいい", "少ない友達と、深く長く",
             "好きなことなら、時間を忘れる", "好きな物だけに使う、センスのいい財布"],
    "INTJ": ["何通りも作戦を考えてから、動く", "相談すると、的確な答えが返ってくる",
             "ゴールから逆算して、計画を立てる", "買う前に、ちゃんと比べて調べる"],
    "INTP": ["好きになった理由を、つい分析しちゃう", "話がかみ合う相手とは、何時間でも話せる",
             "「なんで？」が分かると、忘れない", "気になった本や資料には、迷わない"],
    "INFJ": ["言わなくても、相手の気持ちに気づく", "相談ごとは、なぜかあなたに集まる",
             "意味が分かると、ぐんと伸びる", "心がこもった物にお金を使いたい"],
    "INFP": ["理想の恋を、頭の中で何度も描いている", "本音を話せる友達が、1人いれば十分",
             "物語にすると、すっと覚えられる", "かわいい物を見ると、つい手がのびる"],
}


# 守り神のもとになるもの。毎回ここからランダムに1つ選ぶ（2026-09-30）。
# 「かっこいい」でドラゴン・トカゲばかりになり、人とかぶったため、ドラゴン・トカゲ・ヘビは入れない。
# 動物に限らず、物・植物・自然・精霊なども入れる（ゆーしん「動物をもとにしなくてもいい」）。
CREATURES = [
    # 動物
    "fox", "wolf", "bear", "owl", "eagle", "crane", "deer", "rabbit", "cat", "dog", "tiger", "lion",
    "whale", "octopus", "turtle", "frog", "stag beetle", "butterfly", "hedgehog", "tanuki (raccoon dog)",
    "otter", "penguin", "elephant", "bat", "crow", "hamster", "sheep", "red panda", "shark", "manta ray",
    # 物
    "a paper lantern spirit", "a teapot golem", "an old wind-up clock", "a living umbrella", "a knight's helmet spirit",
    "a music box", "a kite", "a stone lantern", "a daruma doll", "a living backpack", "a lighthouse", "a hot air balloon",
    "a clockwork robot", "a pencil knight", "a treasure chest", "a living kettle",
    # 植物・自然
    "a mushroom spirit", "a cactus", "a sunflower", "a cherry blossom tree spirit", "a pine cone", "a cloud spirit",
    "a raindrop spirit", "a snowman", "a small volcano", "a star spirit", "a crescent moon spirit", "a rock golem",
    "an acorn", "a seashell", "a crystal", "a candle flame spirit",
]

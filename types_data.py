"""質問・16タイプ・相性の中身。

4つの軸（それぞれ2問）で16タイプに分ける。
「MBTI」「16Personalities」の名前・質問文・タイプ名は使わない（商標）。すべてオリジナル。
タイプ名は子どもでも分かる単語を漢字で書き、kana（読みがな）を上に小さく出す（2026-09-30）。

軸：
  E/I  にぎやか ↔ マイペース
  S/N  じっさい ↔ ひらめき
  T/F  りくつ   ↔ きもち
  J/P  けいかく ↔ きまま
にぎやか/マイペースとじっさい/ひらめきは3問ずつ（多数決）、りくつ/きもちとけいかく/きままは2問ずつ（1問目を2点、2問目を1点）で、同点が起きないようにしている。
"""

QUESTIONS = [
    # 2026-09-30に8問→10問。選択肢は答えやすい短い2択にそろえる（12文字以内）。どちらを選んでも良い印象になるように書く（片方が「正解っぽい」と答えが偏り、
    # 兄弟や友だちで同じタイプになりやすくなるため）。軸は交互に並べる。
    {"axis": "EI", "weight": 1, "q": "予定のない休みの日。どうする？",
     "a": ("友だちと出かける", "E"), "b": ("家でのんびりする", "I")},
    {"axis": "SN", "weight": 1, "q": "新しいゲームや道具を手に入れたら？",
     "a": ("説明を先に読む", "S"), "b": ("とりあえず触る", "N")},
    {"axis": "TF", "weight": 2, "q": "友だちが落ちこんでいる。まずどうする？",
     "a": ("解決方法を一緒に考える", "T"), "b": ("だまって話を聞く", "F")},
    {"axis": "JP", "weight": 2, "q": "旅行に行くなら？",
     "a": ("予定を決めておく", "J"), "b": ("行ってから決める", "P")},
    {"axis": "EI", "weight": 1, "q": "初めて会う人が多い集まりでは？",
     "a": ("自分から話しかける", "E"), "b": ("まず様子を見る", "I")},
    {"axis": "SN", "weight": 1, "q": "聞いていて楽しいのは？",
     "a": ("本当にあった話", "S"), "b": ("「もしも」の話", "N")},
    {"axis": "TF", "weight": 1, "q": "みんなで何かを決めるとき、大事なのは？",
     "a": ("理由が正しいか", "T"), "b": ("みんなが楽しめるか", "F")},
    {"axis": "JP", "weight": 1, "q": "机の上や部屋は？",
     "a": ("物の場所が決まっている", "J"), "b": ("わりと自由", "P")},
    {"axis": "EI", "weight": 1, "q": "つかれたとき、元気が出るのは？",
     "a": ("だれかとしゃべる", "E"), "b": ("ひとりで過ごす", "I")},
    {"axis": "SN", "weight": 1, "q": "絵をかくなら？",
     "a": ("見たものをかく", "S"), "b": ("想像したものをかく", "N")},
]

AXIS_WORDS = {"E": "にぎやか", "I": "マイペース", "S": "じっさい", "N": "ひらめき",
              "T": "りくつ", "F": "きもち", "J": "けいかく", "P": "きまま"}

# color：タイプのテーマ色（カードの枠に使う）
# hue：同じ色を英語の言葉で（絵を描くAIに渡す。色番号を渡すと絵に文字として描いてしまうため）
# aruaru：結果ページ「どんな人？」のあるある（タイプで固定。2026-09-30、ゆーしん「タイプで決めといてもいい」）
# motif：絵を描くAIに渡す、そのタイプらしさ（英語）。生き物の種類は書かない（ドラゴンばかりになったため。種類は CREATURES から毎回選ぶ）
TYPES = {
    "ESTJ": {"hue": "warm vermilion red", "color": "#D9483B", "name": "しっかり者", "kana": "しっかりもの", "element": "ほのお", "motif": "orderly and commanding, neat polished armor, carries a banner",
             "desc": "決めたことをきっちりやり切る、頼れるまとめ役。", "strong": "段取りがうまい", "weak": "予定がくずれるとイライラしがち", "aruaru": "予定がくずれると、つい「どうする？」と仕切りだしてしまうことがある。"},
    "ESTP": {"hue": "bright orange", "color": "#F29E1F", "name": "行動派", "kana": "こうどうは", "element": "でんき", "motif": "agile and daring, always mid-leap, crackling with energy",
             "desc": "考えるより先に体が動く行動派。", "strong": "ピンチに強い", "weak": "あきっぽい", "aruaru": "説明を聞き終わる前に、もう手が動いていることがある。"},
    "ESFJ": {"hue": "sunny yellow", "color": "#E8B923", "name": "世話焼きさん", "kana": "せわやきさん", "element": "ひかり", "motif": "warm and caring, carries a basket of gifts, gentle glow",
             "desc": "まわりが笑顔だと自分もうれしくなる。", "strong": "気くばり", "weak": "頼まれると断れない", "aruaru": "みんなの分の飲み物や荷物まで、気づけば用意していることがある。"},
    "ESFP": {"hue": "soft pink", "color": "#EE7FA8", "name": "盛り上げ役", "kana": "もりあげやく", "element": "かぜ", "motif": "festive and cheerful, dancing pose, ribbons and confetti",
             "desc": "その場を一瞬で楽しくしてしまう。", "strong": "盛り上げ上手", "weak": "お金と時間を使いすぎる", "aruaru": "気づけば輪の真ん中にいて、いちばん笑っていることがある。"},
    "ENTJ": {"hue": "royal purple", "color": "#6C4AB6", "name": "負けず嫌い", "kana": "まけずぎらい", "element": "やみ", "motif": "ambitious and majestic, confident stance, royal cape",
             "desc": "大きな目標に向かって一直線に進む。", "strong": "決めるのが速い", "weak": "人にもきびしくなりがち", "aruaru": "ゲームでも勉強でも、やるからには一番をねらいがち。"},
    "ENTP": {"hue": "teal", "color": "#1FA99E", "name": "ひらめき王", "kana": "ひらめきおう", "element": "でんき", "motif": "mischievous inventor, goggles and handmade gadgets",
             "desc": "新しいアイデアが次々とわいてくる。", "strong": "発想力", "weak": "最後まで仕上げるのが苦手", "aruaru": "話しているうちに、新しい思いつきで話題がどんどん変わりがち。"},
    "ENFJ": {"hue": "coral", "color": "#FF7A59", "name": "応援団長", "kana": "おうえんだんちょう", "element": "ほのお", "motif": "passionate cheerleader, raising a flag, radiant warm aura",
             "desc": "人のいいところを見つけて伸ばすのが得意。", "strong": "人をやる気にさせる", "weak": "ひとりで抱えこみすぎる", "aruaru": "落ちこんでいる人を見ると、自分のことより先に声をかけてしまいがち。"},
    "ENFP": {"hue": "apricot", "color": "#F5A623", "name": "知りたがり屋", "kana": "しりたがりや", "element": "ひかり", "motif": "curious explorer, backpack and magnifying glass, sparkling eyes",
             "desc": "好奇心のかたまり。気になったらもう動いている。", "strong": "だれとでも仲良くなれる", "weak": "興味が次々変わる", "aruaru": "気になることを見つけると、予定を忘れて夢中になってしまうことがある。"},
    "ISTJ": {"hue": "forest green", "color": "#4F8A4B", "name": "努力家", "kana": "どりょくか", "element": "くさ", "motif": "steady and hardworking, sturdy build, carries tools and a notebook",
             "desc": "決めたことをまじめに積み上げる。", "strong": "信頼される", "weak": "急な変更が苦手", "aruaru": "一度決めた習慣は、雨の日でもきっちり続けがち。"},
    "ISFJ": {"hue": "mint green", "color": "#6DB38F", "name": "見守り役", "kana": "みまもりやく", "element": "くさ", "motif": "gentle protector, soft calm eyes, holding a lantern",
             "desc": "気づかれないところで人を支えている。", "strong": "思いやり", "weak": "自分のことを後回しにする", "aruaru": "自分のことは後回しにして、人の小さな変化に先に気づきがち。"},
    "ISTP": {"hue": "cobalt blue", "color": "#3F86C2", "name": "器用な職人", "kana": "きようなしょくにん", "element": "こおり", "motif": "cool skilled craftsman, tool belt, precise and calm",
             "desc": "口数は少ないけど、手を動かせばだれより器用。", "strong": "いつも冷静", "weak": "気持ちを言葉にするのが苦手", "aruaru": "説明書を読むより、分解して仕組みを確かめたくなることがある。"},
    "ISFP": {"hue": "lavender", "color": "#B07CC6", "name": "のんびり屋", "kana": "のんびりや", "element": "かぜ", "motif": "easygoing artist, paintbrush and flowers, relaxed pose",
             "desc": "自分の「好き」をなにより大切にする。", "strong": "センスがいい", "weak": "もめごとが苦手でだまりがち", "aruaru": "好きな音楽や景色の前では、時間を忘れてぼーっとしてしまうことがある。"},
    "INTJ": {"hue": "deep indigo", "color": "#3D3B8E", "name": "作戦名人", "kana": "さくせんめいじん", "element": "やみ", "motif": "mysterious strategist, map and chess pieces, thoughtful gaze",
             "desc": "先の先まで読んでから動く。", "strong": "計画力", "weak": "説明をはぶきがち", "aruaru": "何かを始める前に、頭の中で何通りもシミュレーションしがち。"},
    "INTP": {"hue": "sky blue", "color": "#5FA8D8", "name": "なぜなぜ博士", "kana": "なぜなぜはかせ", "element": "こおり", "motif": "curious scholar, stacks of books and a question-mark lamp",
             "desc": "気になったことはとことん考えぬく。", "strong": "分析力", "weak": "考えすぎて動けない", "aruaru": "「なんで？」が気になりだすと、夜ふかししてでも調べてしまうことがある。"},
    "INFJ": {"hue": "navy blue", "color": "#2F6690", "name": "聞き上手", "kana": "ききじょうず", "element": "みず", "motif": "serene good listener, calm smile, soft ripples of water",
             "desc": "人の気持ちを深く読みとる。", "strong": "見ぬく力", "weak": "ひとりで疲れやすい", "aruaru": "言葉にされなくても、相手の気持ちの変化に気づいてしまうことがある。"},
    "INFP": {"hue": "lilac", "color": "#9A86DB", "name": "夢見る人", "kana": "ゆめみるひと", "element": "みず", "motif": "dreamy storyteller, floating stars and a small book",
             "desc": "心の中に大きな世界をもっている。", "strong": "想像力", "weak": "傷つきやすい", "aruaru": "考えごとをしていると、話しかけられても気づかないことがある。"},
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

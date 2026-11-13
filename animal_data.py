"""アニマル診断と、2人の相性診断。2026-11-10（11-13に「自分で選ぶ」形へ変更）

学園祭企画まとめ（PDF）の「アニマルMBTI」「相性診断」を、パスポート（結果ページ /r/<token>）の中で遊べるようにしたもの。
2026-11-13 ゆーしん「ただのMBTIじゃなく、どうぶつを16種類から選んで、そこから相性診断とかできる感じにしたい」
  → 質問とレーダーチャートはやめ、16匹の中から「自分はこれ」と自分で選ぶ。相性は選んだ動物どうしで出す。

画面には「MBTI」の名前を出さない（商標）。内部では動物を4文字のコード（ESTJなど）で持ち、相性の点数の計算にだけ使う。
動物・文はすべてオリジナル。
"""

from __future__ import annotations

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


def best_partners(code: str, n: int = 2) -> list[dict]:
    ranked = sorted((c for c in ANIMALS if c != code), key=lambda c: (-match(code, c)["score"], c))
    return [ANIMALS[c] for c in ranked[:n]]


def choices() -> list[dict]:
    """選ぶ画面に出す16匹（並びは表のとおり）。"""
    return [{"code": c, **{k: v[k] for k in ("animal", "emoji", "catch")}} for c, v in ANIMALS.items()]


def payload(saved: dict) -> dict:
    """保存した {"code"} に、画面に出す中身を足す。"""
    code = saved["code"]
    return {**ANIMALS[code], "code": code, "partners": best_partners(code)}


def match(a: str, b: str) -> dict:
    """2匹の相性。点の付け方は16タイプ版（types_data.match）と同じで、理由を動物の名前で書く。"""
    A, B = ANIMALS[a]["animal"], ANIMALS[b]["animal"]
    score, reasons = 60, []
    if a == b:
        reasons.append(f"同じ{A}どうし。言わなくても分かりあえる")
    if a[1] == b[1]:
        score += 12
        if a != b:
            reasons.append(f"{A}と{B}は、おもしろいと思うものが似ていて話がはずむ")
    if a[0] != b[0]:
        score += 8
        e, i = (A, B) if a[0] == "E" else (B, A)
        reasons.append(f"にぎやかな{e}と、マイペースな{i}。おたがいの足りないところを補える")
    if a[2] == b[2]:
        score += 8
        if a != b:
            reasons.append("大事にしているものが同じで、ぶつかりにくい")
    if a[3] != b[3]:
        score += 7
        j, p = (A, B) if a[3] == "J" else (B, A)
        reasons.append(f"計画を立てる{j}と、その場で決める{p}。いっしょだとちょうどいいバランス")
    if not reasons:
        reasons.append(f"{A}と{B}は、ちがうところだらけ。だからこそ、いっしょにいると新しい発見がある")
    if score >= 90:
        title = "最強コンビ"
    elif score >= 80:
        title = "息ぴったり"
    elif score >= 70:
        title = "いいチーム"
    else:
        title = "刺激しあうライバル"
    return {"score": score, "title": title, "reasons": reasons}


def pair(a: dict, b: dict) -> dict:
    """2人の相性。a・b は保存した {"code"}。"""
    m = match(a["code"], b["code"])
    return {**m, "a": {k: ANIMALS[a["code"]][k] for k in ("animal", "emoji")},
            "b": {k: ANIMALS[b["code"]][k] for k in ("animal", "emoji")}}

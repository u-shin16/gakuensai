# 動物バトル診断（写し）

- 元のリポジトリ：https://github.com/kd1427248-create/animal-battle-quiz （作者：メンバー）
- 写したコミット：ef25461（2026-10-02「対戦画面と技の強さを、文化祭で遊べる形に整える」）。前は 0a2e459
- `quiz.js` と `battle.js` は**手を入れずにそのまま**置いている。直すときは元のリポジトリで直して、ここへ写し直す
- 質問と判定はサーバー側でも使うので、`battle_data.py` に Python で同じ内容を書いている。
  `quiz.js` を写し直したら `python3 battle_data.py --check` で、全4096通りの結果が一致するか確かめる
- Excelの表（質問・技・ステータス）はサイトに公開しない
- キャラの絵（battle.js の PORTRAITS = art/○○.png）は、元のリポジトリにまだ無い。届いたら static/battle/art/ に置けば /battle/art/ で出る。
  それまでは、自分（と友人戦の相手）の欄にパスポートの案内アニマルの絵を出している（templates/battle.html）
- 友人戦（static/battle/pvp.js）は battle.js の関数を使っている。battle.js を写し直したら、関数の名前や引数が変わっていないか確かめる

# 守り神診断（学園祭 2026-11-21 の模擬店）

10問の2択の質問に答えると16の性格タイプのどれかに決まり、好きなものと絵柄（かわいい／かっこいい）を選ぶと、
AI（Gemini）がその人だけの「守り神」を描いてカードにする。

- カード：タイプ名・守り神の絵と名前・守り神からのひとこと・QRコード
- QRの先の結果ページ：どんな人か、強みと弱点、守り神が占う運勢、2人の相性
- 守り神の広場：結果ページで「あいことば」を入れると、店の画面の広場に自分の守り神が現れて歩き回る

## 動かし方

Python 3.11以上。

```
git clone https://github.com/u-shin16/gakuensai.git
cd gakuensai
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
```

`.env` を開いて、**自分の** Gemini APIキーを入れる（https://aistudio.google.com/apikey で作れる）。
本番では、ほかに次の値も入れる。

| 名前 | 中身 |
|---|---|
| `SECRET_KEY` | ログイン状態を守るための長いランダムな文字列 |
| `ADMIN_EMAILS` | 管理者画面に入れるGoogleアカウント（カンマ区切り）。登録したアカウントだけが入れる |
| `PUBLIC_BASE_URL` | 本番のアドレス（例 `https://gakuensai.webtool-labs.com`）。カードのQRに入る |
| `FIREBASE_API_KEY` / `FIREBASE_AUTH_DOMAIN` / `FIREBASE_PROJECT_ID` | FirebaseのウェブアプリのSDK設定（公開してよい値） |
| `FIREBASE_KEY_PATH` | Firestore を読み書きするためのサービスアカウントの鍵（JSON）の場所。リポジトリには入れない |
| `FIRESTORE_PREFIX` | 手元で試すときは `dev_`。本番は空 |

```
./venv/bin/python app.py
```

http://localhost:8120 を開く。

**AIの料金は、`.env` に入れたキーの持ち主に請求される。** カード1枚あたり約10円（絵の描き直しを含む目安）。
キーは人に渡さない。`.env` はGitHubに上げない設定になっている。

## 絵を描く部分の差し替え

絵を描く部分は `drawing.py` の `draw(info)` だけに分けてある。アプリはここを1回呼ぶだけ。

- 自分の描き方に替えるとき：別のファイル（例 `friend_draw.py`）に `draw(info) -> bytes` を作り、`.env` に `DRAW_FUNC=friend_draw:draw` と書いて起動し直す
- `info` に入っているもの（絵の説明・守り神の名前・タイプ・タイプの色・好きなもの・絵柄）と、返すもの（正方形のPNG）は `drawing.py` の先頭に書いてある
- 見本：`draw_example.py`（AIを使わず、タイプの色の丸を描くだけ。料金がかからないので動作確認にも使える）

## ページ

| ページ | 内容 | だれが使う |
|---|---|---|
| `/` | 診断してカードを作る（お店のあいことばが必要） | お客さん（店のタブレット・自分のスマホ） |
| `/r/<16文字>` | 結果ページ（運勢・相性・広場に出す／出る） | お客さん（カードのQR） |
| `/plaza` | 守り神の広場 | 店の大きい画面 |
| `/admin` | 管理者画面の入口 | スタッフ（登録したGoogleアカウントでログイン。手元で直接動かすときはログイン不要） |
| `/admin/plaza` | 広場の管理（あいことば・守り神を出す） | スタッフ（同上） |
| `/admin/characters` | これまでに作った守り神の一覧 | スタッフ（同上） |

同じWi-Fiのタブレットからは `http://<アプリを動かすPCのIP>:8120` で開く。

## 記録

- 守り神の絵：サーバーの `data/results/`（GitHubには上げない）
- それ以外（カードの結果・広場・あいことば・通し番号・記録）：Firebase の Firestore（`store.py`）。名前は取らない。好きなものは保存する

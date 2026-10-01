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
| `GOOGLE_CLIENT_ID` | 管理者のGoogleログイン用（Google Cloudで作るOAuthクライアントID） |
| `ADMIN_EMAILS` | 管理者画面に入れるGoogleアカウント（カンマ区切り）。登録したアカウントだけが入れる |
| `PUBLIC_BASE_URL` | 本番のアドレス（例 `https://gakuensai.webtool-labs.com`）。カードのQRに入る |

```
./venv/bin/python app.py
```

http://localhost:8120 を開く。

**AIの料金は、`.env` に入れたキーの持ち主に請求される。** カード1枚あたり約10円（絵の描き直しを含む目安）。
キーは人に渡さない。`.env` はGitHubに上げない設定になっている。

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

`data/` に保存し、GitHubには上げない。

- `data/results/`：カードごとの結果と絵（名前は取らない。好きなものは保存する）
- `data/log.jsonl`：作ったカード・相性・広場の記録
- `data/plaza.json`：広場のあいことばと、広場にいる守り神

# iPhone 16 整備済製品 在庫通知システム

Appleの整備済製品ページ（https://www.apple.com/jp/shop/refurbished/iphone）を
15分おきにチェックし、**iPhone 16シリーズが新規に入荷したときだけ**メールで通知します。
（在庫あり→なし→ありに変わったタイミングのみ通知。毎回は送りません。）

GitHub Actionsで動くので、自分のPCを起動しっぱなしにする必要はありません。無料枠で十分動きます。

---

## セットアップ手順

### 1. Gmailの「アプリパスワード」を発行する

通常のGmailパスワードはこの用途には使えません。専用の「アプリパスワード」を発行します。

1. Googleアカウントの [セキュリティ設定](https://myaccount.google.com/security) を開く
2. 「2段階認証プロセス」を有効にする（未設定なら先にこれが必要）
3. 「アプリパスワード」を検索 → 新規作成 → 任意の名前（例: `iphone-watcher`）を入力
4. 表示された16桁のパスワードをコピーしておく（後で使います）

### 2. GitHubリポジトリを作成する

1. GitHubで新しいリポジトリを作成（Public/Privateどちらでも可。Privateでも無料枠でActionsは使えます）
2. このフォルダの中身（`check_stock.py`、`.github/workflows/check.yml`、この`README.md`）をそのリポジトリにアップロード
   - GitHubのWeb画面から「Add file」→「Upload files」でドラッグ&ドロップでもOK

### 3. GitHub Secretsを設定する

リポジトリの `Settings` → `Secrets and variables` → `Actions` → `New repository secret` から、以下の3つを登録します。

| Name | 値 |
|---|---|
| `GMAIL_ADDRESS` | 送信元にするGmailアドレス |
| `GMAIL_APP_PASSWORD` | 手順1で発行した16桁のアプリパスワード |
| `NOTIFY_TO` | 通知を受け取りたいメールアドレス（Gmailアドレスと同じでも可） |

### 4. 動作確認

1. リポジトリの `Actions` タブを開く
2. 左側の `Check iPhone 16 Refurbished Stock` を選択
3. `Run workflow` ボタンで手動実行してみる
4. 実行ログで「現在の状態: NOT_FOUND」などと表示されればOK（正常にページを取得できています）

これで設定完了です。以降は15分おきに自動でチェックされ、iPhone 16が入荷したタイミングでメールが届きます。

---

## カスタマイズ

- **チェック頻度を変える**: `.github/workflows/check.yml` の `cron: "*/15 * * * *"` を編集
  - 例: 5分おき → `*/5 * * * *`（あまり短くしすぎるとGitHub Actionsの無料枠を消費するので注意）
- **他のモデルも監視したい**: `check_stock.py` の `KEYWORD = "iPhone 16"` を `"iPhone 16 Pro"` などに変更、
  もしくは複数キーワードに対応させたい場合はお知らせください。
- **メール以外に変更したい**: Discord Webhookやその他の通知方法にも対応できます。

## 注意事項

- Apple公式サイトのHTML構造が変わると検知精度に影響する可能性があります。しばらく通知が来ない場合は、
  Actionsのログでエラーが出ていないか確認してください。
- あくまで個人利用の監視ツールです。あまりに高頻度なアクセスはサイトに負荷をかけるため、15分おき程度を推奨します。

# YouTube 限定公開再生リスト自動作成ツール

ご自身のYouTubeチャンネルから動画を自動検索し、日付ごとの**限定公開再生リスト**を自動作成・動画追加して共有用URLを発行するツールです。

- [Privacy Policy / プライバシーポリシー](PRIVACY.md)

---

## 1. ローカルでの実行

### 手動実行メニュー
**[run.bat](file:///c:/Users/user/projects/Youtube限定公開/run.bat)** をダブルクリックします：
- **`[1]` 今日の動画を自動検出して限定公開再生リストを作成**
- **`[2]` チャンネル全体を一括走査して日付ごとに再生リストを作成**（public動画の限定公開化含む）
- **`[3]` 手動で動画URLを入力して作成**

---

## 2. Cloud Run Jobs による毎日自動化（クラウド運用）

PCを起動していなくても、Google Cloud 上で**毎晩（23:00 JST）自動実行**される仕組みです。

### 仕組み
- **Cloud Run Jobs**（コンテナ実行基盤）: 実行時（数秒間）だけ起動して自動終了するため、**Google Cloudの無料枠（月額0円）**で動作します。
- **Cloud Scheduler**（定時トリガー）: 毎日 23:00 にジョブを自動起動します。
- **動作内容**:
  1. その日にアップロードされた動画を自動検出
  2. public動画があれば限定公開（unlisted）に変更
  3. その日の限定公開再生リストを作成して動画を追加
  4. 完了ログを Cloud Logging に記録

### デプロイ方法（ワンクリック）
1. **[deploy_cloud_run.bat](file:///c:/Users/user/projects/Youtube限定公開/deploy_cloud_run.bat)** をダブルクリックします。
2. 画面の指示に従い、プロジェクトID（デフォルトで検出された `youtubegentei` など）を確認して Enter を押します。
3. 自動的にビルド・デプロイ・定期スケジューラー登録が行われます。

※もし gcloud のログインアカウントを切り替える必要がある場合は、事前にターミナルで `gcloud auth login` を実行してください。

---

## 3. 作成済み再生リストの一覧
作成された限定公開再生リストの共有用URLは、[PLAYLISTS.md](file:///c:/Users/user/projects/Youtube限定公開/PLAYLISTS.md) でいつでも確認できます。

---

## 4. トラブルシューティング: トークンが7日間で切れる問題について
Google Cloud の「OAuth 同意画面」の公開ステータスが **「テスト中（Testing）」** の場合、セキュリティ仕様により **リフレッシュトークンが7日間で強制失効** します。

### 恒久対策（7日期限をなくす手順）
1. **Google Cloud Console** の [APIとサービス] → [OAuth 同意画面](https://console.cloud.google.com/apis/credentials/consent) を開きます。
2. 「公開ステータス」にある **「アプリを公開（PUBLISH APP）」** ボタンをクリックします。
   - ※「Google の確認（審査）」についての警告が出ますが、自分自身で利用する個人・自社ツールの場合は**審査を申請・完了させる必要はありません**。公開ステータスを本番にするだけで7日制限が解除されます。
3. **[reauth.bat](file:///c:/Users/user/projects/Youtube限定公開/reauth.bat)** を実行してブラウザでログイン承認し、長期有効なトークンを再取得します。
   - ※「このアプリは Google で確認されていません」と表示されたら「詳細」→「安全ではないページに移動（続行）」をクリックします。
4. **[deploy_cloud_run.bat](file:///c:/Users/user/projects/Youtube限定公開/deploy_cloud_run.bat)** を実行して Cloud Run に新しいトークンを反映させます。


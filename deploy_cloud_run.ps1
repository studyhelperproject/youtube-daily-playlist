param(
    [string]$ProjectId = "",
    [switch]$NonInteractive
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Cloud Run Jobs 自動デプロイツール"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Cloud Run Jobs + Cloud Scheduler デプロイスクリプト" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. token.json の存在確認
$TokenPath = Join-Path $ScriptDir "token.json"
if (-not (Test-Path $TokenPath)) {
    Write-Host "[エラー] token.json が見つかりません。先にローカルで一度認証を完了させてください。" -ForegroundColor Red
    if (-not $NonInteractive) { Read-Host "Enterキーを押して終了..." }
    exit 1
}

# 2. プロジェクトIDの取得/確認
$ClientSecretPath = Join-Path $ScriptDir "client_secret.json"
$DefaultProject = ""
if (Test-Path $ClientSecretPath) {
    try {
        $csJson = Get-Content $ClientSecretPath -Raw | ConvertFrom-Json
        if ($csJson.installed.project_id) {
            $DefaultProject = $csJson.installed.project_id
        }
    } catch {}
}

if (-not $ProjectId) {
    Write-Host "対象の Google Cloud プロジェクトID を確認します。" -ForegroundColor Yellow
    if ($DefaultProject) {
        Write-Host "client_secret.json から検出されたプロジェクト: $DefaultProject"
        if ($NonInteractive) {
            $ProjectId = $DefaultProject
        } else {
            $InputProject = Read-Host "プロジェクトID [Enterで '$DefaultProject' を使用]"
            if (-not $InputProject) {
                $ProjectId = $DefaultProject
            } else {
                $ProjectId = $InputProject.Trim()
            }
        }
    } else {
        $ProjectId = Read-Host "Google Cloud プロジェクトIDを入力してください"
    }
}

if (-not $ProjectId) {
    Write-Host "[エラー] プロジェクトIDが指定されませんでした。" -ForegroundColor Red
    exit 1
}

$Region = "asia-northeast1" # 東京リージョン
$JobName = "youtube-daily-playlist"
$ImageName = "gcr.io/$ProjectId/$JobName"

Write-Host ""
Write-Host "■ 設定内容:" -ForegroundColor Green
Write-Host "  プロジェクト : $ProjectId"
Write-Host "  リージョン   : $Region"
Write-Host "  ジョブ名     : $JobName"
Write-Host "  コンテナ     : $ImageName"
Write-Host ""

# gcloud プロジェクト設定
Write-Host "[1/5] gcloud のプロジェクトを設定中..." -ForegroundColor Cyan
gcloud config set project $ProjectId

# 必要なAPIの有効化
Write-Host "[2/5] 必要な Google Cloud API を有効化中..." -ForegroundColor Cyan
gcloud services enable run.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com

# token.json を1行のJSON文字列として取得
$TokenContent = Get-Content $TokenPath -Raw
# 改行や空白を圧縮
$TokenCompact = ($TokenContent | ConvertFrom-Json | ConvertTo-Json -Compress)

# Cloud Build でコンテナをビルド
Write-Host "[3/5] コンテナイメージをビルド中 (Cloud Build)..." -ForegroundColor Cyan
gcloud builds submit --tag $ImageName .

if ($LASTEXITCODE -ne 0) {
    Write-Host "[エラー] コンテナのビルドに失敗しました。" -ForegroundColor Red
    exit 1
}

# Cloud Run Jobs を作成/更新
Write-Host "[4/5] Cloud Run Job をデプロイ中..." -ForegroundColor Cyan

# 一時的な環境変数ファイルを作成して安全に渡す
$EnvFile = Join-Path $ScriptDir ".env.yaml"
"YOUTUBE_TOKEN_JSON: '$TokenCompact'" | Set-Content -Path $EnvFile -Encoding UTF8

gcloud run jobs deploy $JobName --image $ImageName --region $Region --env-vars-file $EnvFile --max-retries 1 --task-timeout 10m

# 一時ファイルを削除
Remove-Item $EnvFile -Force -ErrorAction SilentlyContinue

if ($LASTEXITCODE -ne 0) {
    Write-Host "[エラー] Cloud Run Job のデプロイに失敗しました。" -ForegroundColor Red
    exit 1
}

# Cloud Scheduler で毎日定時実行（例: 毎日 23:00 JST）
Write-Host "[5/5] Cloud Scheduler で毎日 23:00 (JST) の自動実行を登録中..." -ForegroundColor Cyan
$SchedulerName = "youtube-daily-playlist-trigger"

# 既存スケジューラーがあれば削除
gcloud scheduler jobs delete $SchedulerName --location $Region --quiet 2>$null

# Cloud Run Job を実行するためのサービスアカウント権限設定（デフォルトCompute Engineアカウント使用）
$ProjectNumber = (gcloud projects describe $ProjectId --format="value(projectNumber)")
$ServiceAccount = "$ProjectNumber-compute@developer.gserviceaccount.com"

# 実行トリガー用スケジューラ作成
$SchedulerUri = "https://$Region-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$ProjectId/jobs/$JobName:run"
gcloud scheduler jobs create http $SchedulerName --location $Region --schedule "0 23 * * *" --time-zone "Asia/Tokyo" --uri $SchedulerUri --http-method POST --oauth-service-account-email $ServiceAccount

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " 🎉 Cloud Run 定期実行のデプロイが完了しました！" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "■ スケジュール: 毎日 23:00 (日本時間)"
Write-Host "■ 動作内容    : その日にアップロードされた動画を自動検出"
Write-Host "                public動画を限定公開に変更"
Write-Host "                日付ごとの限定公開再生リストを作成して動画を追加"
Write-Host ""
Write-Host "今すぐテスト実行したい場合は以下のコマンドで実行できます:" -ForegroundColor Yellow
Write-Host "  gcloud run jobs execute $JobName --region $Region"
Write-Host ""
if (-not $NonInteractive) {
    Read-Host "Enterキーを押して終了..."
}

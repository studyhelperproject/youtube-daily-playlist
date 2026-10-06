[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = 'YouTube 限定公開再生リスト自動化ツール'

Write-Host '========================================================' -ForegroundColor Cyan
Write-Host '   YouTube 限定公開再生リスト 自動管理ツール' -ForegroundColor Cyan
Write-Host '========================================================' -ForegroundColor Cyan
Write-Host ''

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonExe = Join-Path $ScriptDir '.venv\Scripts\python.exe'

if (-not (Test-Path $PythonExe)) {
    Write-Host '[エラー] Python仮想環境 (.venv) が見つかりません。' -ForegroundColor Red
    Read-Host 'Enterキーを押して終了してください...'
    exit 1
}

Write-Host '実行するメニューを選択してください:' -ForegroundColor Yellow
Write-Host '  [1] 今日のアップロード動画を自動検出して限定公開再生リストを作成'
Write-Host '  [2] チャンネル内を一括走査して日付ごとに再生リストを作成（public動画の限定公開化含む）'
Write-Host '  [3] 手動で動画URL/IDを入力して作成'
Write-Host '  [4] YouTube認証の再取得・更新（トークン再生成）'
Write-Host ''
$choice = Read-Host '番号を入力 (1-4, デフォルトは 1)'

if ($choice -eq '2') {
    Write-Host '>> チャンネル一括自動作成を開始します...' -ForegroundColor Green
    & $PythonExe batch_process_channel.py
} elseif ($choice -eq '3') {
    Write-Host '>> 手動入力モードを開始します...' -ForegroundColor Green
    & $PythonExe create_daily_playlist.py
} elseif ($choice -eq '4') {
    Write-Host '>> 再認証モードを開始します...' -ForegroundColor Green
    & $PythonExe reauth.py
} else {
    Write-Host '>> 今日の動画自動作成モードを開始します...' -ForegroundColor Green
    & $PythonExe auto_channel_playlist.py
}

Write-Host ''
Write-Host '--------------------------------------------------------' -ForegroundColor Gray
Read-Host 'Enterキーを押すと画面を閉じます...'

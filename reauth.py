"""
YouTube OAuth 再認証ツール
OAuth同意画面を「本番環境（In Production）」に変更した後、
このスクリプトを実行して長期有効なリフレッシュトークンを再取得します。
"""

import sys
from youtube_manager import YouTubeManager

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("=" * 60)
    print("  YouTube API 再認証スクリプト (トークン再取得)")
    print("=" * 60)
    print("※ Google Cloud Console の『OAuth 同意画面』で")
    print("   ステータスが『本番環境（In Production）』になっていることを確認してください。")
    print("   (ステータスがテスト中のままだと、7日でトークンが失効します)\n")

    manager = YouTubeManager()
    try:
        # 強制的にブラウザ認証を実行
        manager.authenticate(force_reauth=True)
        channel = manager.get_my_channel()
        print("\n" + "=" * 60)
        print(" 🎉 認証に成功しました！")
        print(f"  - チャンネル名: {channel['title']}")
        print(f"  - チャンネルID: {channel['id']}")
        print("  - トークン保存先: token.json")
        print("=" * 60)
        print("\n【次のステップ】")
        print("Cloud Run に最新トークンを反映させるため、")
        print("以下のコマンドまたは 'deploy_cloud_run.bat' を実行してください:")
        print("  powershell -ExecutionPolicy Bypass -File .\\deploy_cloud_run.ps1\n")
    except Exception as e:
        print(f"\n[エラー] 認証中に問題が発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

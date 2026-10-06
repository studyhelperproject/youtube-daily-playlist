"""
自チャンネルの動画を自動検索し、日付ごとの限定公開再生リストを作成・追加する自動化スクリプト
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from youtube_manager import YouTubeManager, JST


def parse_args():
    parser = argparse.ArgumentParser(
        description="チャンネル内の動画を自動検索し、日付ごとの限定公開再生リストを作成します。"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象の日付 (形式: YYYY-MM-DD)。省略時は日本時間の今日が使用されます。"
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="再生リストのタイトル。省略時は『YYYY-MM-DD 限定公開動画』になります。"
    )
    parser.add_argument(
        "--privacy",
        type=str,
        default="unlisted",
        choices=["unlisted", "private", "public"],
        help="作成する再生リストの公開設定 (デフォルト: unlisted / 限定公開)"
    )
    parser.add_argument(
        "--video-privacy",
        type=str,
        default=None,
        help="検索対象の動画公開ステータス (例: unlisted で限定公開動画のみ対象。省略時はすべて)"
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="確認プロンプトをスキップして自動作成します（定期実行用）"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 対象日付（デフォルトは日本時間の今日）
    now_jst = datetime.now(JST)
    target_date = args.date or now_jst.strftime("%Y-%m-%d")
    playlist_title = args.title or f"{target_date} 限定公開動画"

    print("=" * 60)
    print("  YouTube チャンネル自動検索 & 再生リスト作成ツール")
    print("=" * 60)
    print(f"■ 対象日付: {target_date} (JST)")
    print(f"■ 作成予定タイトル: {playlist_title}")
    print("-" * 60)

    # 1. 認証とチャンネル情報取得
    manager = YouTubeManager()
    try:
        manager.authenticate()
        channel = manager.get_my_channel()
        print(f"\n[接続成功] チャンネル名: {channel['title']} (ID: {channel['id']})")
    except FileNotFoundError as e:
        print(f"\n[エラー] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[エラー] チャンネル接続に失敗しました: {e}")
        sys.exit(1)

    # 2. チャンネル内動画の検索
    print(f"\n[検索中] {target_date} のアップロード動画を検索しています...")
    matched_videos = manager.get_my_videos(
        max_results=50,
        date_filter=target_date,
        privacy_filter=args.video_privacy
    )

    selected_videos = []

    if matched_videos:
        print(f"\n✓ {target_date} の動画が {len(matched_videos)} 件見つかりました：")
        for i, v in enumerate(matched_videos, 1):
            print(f"  {i}. [{v['published_at']}] [{v['privacy']}] {v['title']}")
            print(f"     URL: {v['url']}")
        selected_videos = matched_videos
    else:
        print(f"\n※ {target_date} にアップロードされた動画は見つかりませんでした。")
        print("\n直近のアップロード動画（最新5件）を確認します...")
        recent_videos = manager.get_my_videos(max_results=5)
        if not recent_videos:
            print("チャンネル内に動画が見つかりませんでした。動画をアップロードしてから再度実行してください。")
            sys.exit(0)

        print("\n--- 直近のアップロード動画 ---")
        for i, v in enumerate(recent_videos, 1):
            print(f"  {i}. [{v['published_at']}] [{v['privacy']}] {v['title']}")
            print(f"     URL: {v['url']}")

        if args.auto_confirm:
            print("\n自動実行モードのため、対象動画がないため処理を終了します。")
            sys.exit(0)

        # ユーザー選択プロンプト
        print("\n直近の動画から再生リストに追加するものを選択してください：")
        print("  - 全て追加する場合       : all と入力")
        print("  - 番号で指定する場合     : 1, 2 のようにカンマ区切りで入力")
        print("  - キャンセルする場合     : 何も入力せず Enter")
        
        try:
            choice = input("\n選択 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nキャンセルされました。")
            sys.exit(0)

        if not choice:
            print("処理を終了します。")
            sys.exit(0)
        elif choice.lower() == "all":
            selected_videos = recent_videos
        else:
            try:
                indices = [int(x.strip()) for x in choice.split(",") if x.strip().isdigit()]
                for idx in indices:
                    if 1 <= idx <= len(recent_videos):
                        selected_videos.append(recent_videos[idx - 1])
            except Exception:
                print("入力が正しくありません。終了します。")
                sys.exit(1)

    if not selected_videos:
        print("追加対象の動画がありませんでした。")
        sys.exit(0)

    # 3. 再生リストの作成確認
    if not args.auto_confirm:
        print(f"\n以下の {len(selected_videos)} 本の動画で再生リスト『{playlist_title}』({args.privacy}) を作成します。")
        try:
            confirm = input("作成を続行しますか？ [Y/n]: ").strip().lower()
            if confirm in ["n", "no"]:
                print("キャンセルしました。")
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            print("\nキャンセルしました。")
            sys.exit(0)

    # 4. 再生リスト作成
    print(f"\n[1/2] 再生リストを作成中: '{playlist_title}' ...")
    try:
        playlist = manager.create_playlist(
            title=playlist_title,
            description=f"{target_date} 用の限定公開再生リストです。",
            privacy_status=args.privacy
        )
        playlist_id = playlist["id"]
        playlist_url = playlist["url"]
        print(f"✓ 作成完了! (ID: {playlist_id})")
    except Exception as e:
        print(f"[エラー] 再生リスト作成に失敗しました: {e}")
        sys.exit(1)

    # 5. 動画の追加
    print(f"\n[2/2] 動画を再生リストに追加中...")
    video_ids = [v["id"] for v in selected_videos]
    added = manager.add_videos_to_playlist(playlist_id, video_ids)

    # 6. 結果表示
    print("\n" + "=" * 60)
    print(" 🎉 再生リストの自動作成が完了しました！")
    print("=" * 60)
    print(f"■ タイトル        : {playlist_title}")
    print(f"■ 公開設定        : {args.privacy} (限定公開)")
    print(f"■ 追加された動画数: {len(added)} / {len(selected_videos)} 件")
    print(f"■ 限定公開URL (共有用):")
    print(f"  -> {playlist_url}")
    print("=" * 60)
    print("※この限定公開URLをグループメンバーに共有してください。")
    print("※履歴は 'playlists_history.json' に自動保存されました。\n")


if __name__ == "__main__":
    main()

"""
日付ごとの限定公開再生リストを作成し、動画を追加する実行スクリプト
"""

import argparse
import sys
from datetime import datetime
from youtube_manager import YouTubeManager, extract_video_id


def parse_args():
    parser = argparse.ArgumentParser(
        description="日付ごとのYouTube限定公開再生リストを作成し、動画を追加します。"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象の日付 (形式: YYYY-MM-DD)。省略時は今日の日付が使用されます。"
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="再生リストのタイトル。省略時は『YYYY-MM-DD 限定公開動画』になります。"
    )
    parser.add_argument(
        "--videos",
        "-v",
        nargs="*",
        default=[],
        help="追加する動画のURLまたは動画ID（複数指定可）"
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="動画のURL/IDが1行ずつ書かれたテキストファイルのパス"
    )
    parser.add_argument(
        "--privacy",
        type=str,
        default="unlisted",
        choices=["unlisted", "private", "public"],
        help="再生リストの公開設定 (デフォルト: unlisted / 限定公開)"
    )
    return parser.parse_args()


def load_videos_from_file(file_path: str) -> list[str]:
    videos = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    videos.append(line)
    except Exception as e:
        print(f"[エラー] ファイル '{file_path}' の読み込みに失敗しました: {e}")
    return videos


def prompt_for_videos() -> list[str]:
    print("\n--- 動画の登録 ---")
    print("追加したい動画のURLまたは動画IDを入力してください。")
    print("（入力を終えるには、何も入力せずに Enter キーを押してください）")
    videos = []
    idx = 1
    while True:
        try:
            line = input(f"動画 {idx}: ").strip()
            if not line:
                break
            video_id = extract_video_id(line)
            if video_id:
                videos.append(line)
                idx += 1
            else:
                print("  ※有効なYouTubeのURLまたは動画IDではありません。再度入力してください。")
        except (KeyboardInterrupt, EOFError):
            print("\n入力を中断しました。")
            break
    return videos


def main():
    args = parse_args()

    # 1. 日付の決定
    target_date = args.date or datetime.now().strftime("%Y-%m-%d")

    # 2. タイトルの決定
    title = args.title or f"{target_date} 限定公開動画"
    description = f"{target_date} 用の限定公開再生リストです。"

    # 3. 動画リストの収集
    videos_to_add = list(args.videos)

    if args.file:
        videos_to_add.extend(load_videos_from_file(args.file))

    # 引数でもファイルでも指定がなければ対話入力
    if not videos_to_add:
        videos_to_add = prompt_for_videos()

    if not videos_to_add:
        print("\n[キャンセル] 追加する動画が指定されなかったため、処理を終了します。")
        sys.exit(0)

    print("\n" + "=" * 50)
    print(f"作成対象日付: {target_date}")
    print(f"再生リスト名: {title}")
    print(f"公開設定    : {args.privacy}")
    print(f"追加予定動画: {len(videos_to_add)} 件")
    print("=" * 50 + "\n")

    # 4. YouTube Manager の初期化と認証
    manager = YouTubeManager()
    try:
        manager.authenticate()
    except FileNotFoundError as e:
        print(f"\n[エラー] {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[エラー] 認証中に問題が発生しました: {e}\n")
        sys.exit(1)

    # 5. 再生リストの作成
    print(f"\n[1/2] 再生リストを作成中: '{title}' ...")
    try:
        playlist = manager.create_playlist(
            title=title,
            description=description,
            privacy_status=args.privacy
        )
        playlist_id = playlist["id"]
        playlist_url = playlist["url"]
        print(f"✓ 再生リスト作成成功!")
        print(f"  ID : {playlist_id}")
        print(f"  URL: {playlist_url}")
    except Exception as e:
        print(f"[エラー] 再生リストの作成に失敗しました: {e}")
        sys.exit(1)

    # 6. 動画の追加
    print(f"\n[2/2] 動画を再生リストに追加中...")
    added = manager.add_videos_to_playlist(playlist_id, videos_to_add)

    # 7. 完了結果の表示
    print("\n" + "=" * 60)
    print(" 🎉 すべての処理が完了しました！")
    print("=" * 60)
    print(f"■ 再生リストタイトル : {title}")
    print(f"■ 追加された動画数   : {len(added)} / {len(videos_to_add)} 件")
    print(f"■ 限定公開URL (共有用):")
    print(f"  -> {playlist_url}")
    print("=" * 60)
    print("※この限定公開URLをグループのメンバーに共有してください。")
    print("※履歴は 'playlists_history.json' に保存されました。\n")


if __name__ == "__main__":
    main()

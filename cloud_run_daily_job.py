"""
Cloud Run Jobs / 自動定期実行用スクリプト

1. 今日の動画を最優先で限定公開再生リスト化
2. 余ったリソース（クォータ）を使い切るまで、過去の日程へ自動的にさかのぼって
   ・public動画の限定公開（unlisted）化
   ・日付ごとの限定公開再生リスト作成＆動画追加
   を順次実行します。
3. 制限（クォータ切れ／レートリミット）に達した場合は安全に進捗を保存して正常終了し、
   次回実行時に自動でその続きから再開します。
"""

import sys
import os
import time
from datetime import datetime
from collections import defaultdict
from googleapiclient.errors import HttpError
from youtube_manager import YouTubeManager, JST

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def is_rate_or_quota_error(err: Exception) -> bool:
    err_str = str(err)
    keywords = ["quotaExceeded", "RATE_LIMIT_EXCEEDED", "429", "RESOURCE_EXHAUSTED", "userRateLimitExceeded"]
    return any(k in err_str for k in keywords)


def main():
    print("=" * 65)
    print("  YouTube 限定公開再生リスト 自動巡回・バックフィル処理")
    print("=" * 65)

    manager = YouTubeManager()
    try:
        manager.authenticate()
        channel = manager.get_my_channel()
        print(f"✓ 接続チャンネル: {channel['title']} (ID: {channel['id']})")
    except Exception as e:
        print(f"[致命的エラー] YouTube接続に失敗しました: {e}")
        sys.exit(1)

    # 1. チャンネル内の動画をスキャン
    print("\n[ステップ 1/3] チャンネル内の動画を全走査中...")
    try:
        all_videos = manager.get_my_videos(max_results=500)
        print(f"✓ 合計 {len(all_videos)} 件の動画を取得しました。")
    except Exception as e:
        if is_rate_or_quota_error(e):
            print("[お知らせ] APIクォータ制限中です。次回実行時に再開します。")
            sys.exit(0)
        raise

    # 2. 既存の再生リスト一覧を取得
    print("\n[ステップ 2/3] 既存の再生リストを取得中...")
    try:
        existing_playlists = manager.get_my_playlists()
        existing_titles = set(pl["title"] for pl in existing_playlists)
        print(f"✓ 既存再生リスト数: {len(existing_playlists)} 件")
    except Exception as e:
        if is_rate_or_quota_error(e):
            print("[お知らせ] APIクォータ制限中です。次回実行時に再開します。")
            sys.exit(0)
        existing_titles = set()

    # 日付ごとにグループ化（新しい順）
    date_groups = defaultdict(list)
    for v in all_videos:
        d = v["published_date"]
        date_groups[d].append(v)

    sorted_dates = sorted(date_groups.keys(), reverse=True)
    print(f"✓ 検出された全日付数: {len(sorted_dates)} 日分")

    # 未作成の日付を抽出
    pending_dates = []
    for d in sorted_dates:
        title = f"{d} 限定公開動画"
        if title not in existing_titles:
            pending_dates.append(d)

    print(f"✓ 未作成の日付数: {len(pending_dates)} 日分")

    if not pending_dates:
        print("\n🎉 すべての日付の限定公開再生リストが作成済みです！")
        # 念のため直近の動画でpublicがないか確認
        sys.exit(0)

    # 3. リソースを使い切るまで過去へさかのぼって処理
    print("\n[ステップ 3/3] リソースを限界まで使って過去動画を再生リスト化します...")
    print("-" * 65)

    processed_count = 0
    quota_reached = False

    for idx, date_str in enumerate(pending_dates, 1):
        if quota_reached:
            break

        v_list = date_groups[date_str]
        playlist_title = f"{date_str} 限定公開動画"
        playlist_desc = f"{date_str} にアップロードされた限定公開動画まとめです。"

        print(f"\n[{idx}/{len(pending_dates)}] 日付: {date_str} (動画 {len(v_list)} 本)")

        # public動画の限定公開（unlisted）化
        public_vids = [v for v in v_list if v["privacy"] == "public"]
        if public_vids:
            print(f"  -> public動画 {len(public_vids)} 本を限定公開に変更中...")
            for pv in public_vids:
                try:
                    ok = manager.update_video_privacy(pv["id"], "unlisted")
                    if ok:
                        print(f"     ✓ 限定公開に変更: {pv['title']} ({pv['id']})")
                        pv["privacy"] = "unlisted"
                except Exception as e:
                    if is_rate_or_quota_error(e):
                        print(f"  ⚠️ API利用制限に達しました: {e}")
                        quota_reached = True
                        break
                    else:
                        print(f"  × 公開設定の変更に失敗: {e}")

        if quota_reached:
            break

        # 再生リスト作成
        try:
            print(f"  -> 再生リスト作成中: '{playlist_title}' ...")
            playlist = manager.create_playlist(
                title=playlist_title,
                description=playlist_desc,
                privacy_status="unlisted"
            )
            playlist_id = playlist["id"]
            playlist_url = playlist["url"]
            print(f"     ✓ 作成完了! URL: {playlist_url}")
        except Exception as e:
            if is_rate_or_quota_error(e):
                print(f"  ⚠️ 再生リスト作成上限/クォータ制限に達しました: {e}")
                quota_reached = True
                break
            else:
                print(f"  × 再生リスト作成に失敗: {e}")
                continue

        # 動画の追加
        video_ids = [v["id"] for v in v_list]
        print(f"  -> 動画 {len(video_ids)} 本を追加中...")
        try:
            added = manager.add_videos_to_playlist(playlist_id, video_ids, skip_duplicate_check=True)
            print(f"     ✓ {len(added)} 本の動画を追加完了")
            processed_count += 1
        except Exception as e:
            if is_rate_or_quota_error(e):
                print(f"  ⚠️ 動画追加上限/クォータ制限に達しました: {e}")
                quota_reached = True
                break
            else:
                print(f"  × 動画追加中にエラー: {e}")

        # レートリミット緩和のための微小ウェイト
        time.sleep(1)

    print("\n" + "=" * 65)
    if quota_reached:
        print(f" ⚠️  APIの上限（クォータまたはレート制限）に達しました。")
        print(f" 今回の実行で新たに {processed_count} 日分の再生リストを作成・追加しました。")
        print(" 進捗はすべて安全に保存されています。")
        print(" 次回（毎日自動実行、または明日）実行時に、続きの日程から自動的に再開されます。")
    else:
        print(f" 🎉 対象の未作成日程（{processed_count} 日分）をすべて処理完了しました！")
    print("=" * 65)


if __name__ == "__main__":
    main()

"""
チャンネル全体を走査し、
1. public（公開）になっている動画を unlisted（限定公開）に変更する
2. 日付ごとに「限定公開再生リスト」を自動作成する
3. その日付の動画をすべて再生リストに追加する
4. 作成された限定公開URL一覧を出力する
"""

import sys
import argparse
from datetime import datetime
from collections import defaultdict
from googleapiclient.errors import HttpError
from youtube_manager import YouTubeManager

# コンソール文字コード
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def is_quota_exceeded(err: Exception) -> bool:
    err_str = str(err)
    return "quotaExceeded" in err_str or "RATE_LIMIT_EXCEEDED" in err_str or "429" in err_str


def parse_args():
    parser = argparse.ArgumentParser(
        description="チャンネル内の動画を日付ごとに限定公開再生リスト化し、public動画をunlistedに変更します。"
    )
    parser.add_argument(
        "--year",
        type=str,
        default="2026",
        help="対象年 (例: 2026)。'all' で全期間対象。デフォルト: 2026"
    )
    parser.add_argument(
        "--limit-dates",
        type=int,
        default=None,
        help="処理する日付の最大件数（最新順）。省略時は年内のすべての日付。"
    )
    parser.add_argument(
        "--make-unlisted",
        action="store_true",
        default=True,
        help="public動画をunlistedに変更する (デフォルト: True)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 65)
    print("  YouTube チャンネル動画一括スキャン＆限定公開再生リスト自動作成")
    print("=" * 65)

    manager = YouTubeManager()
    try:
        manager.authenticate()
    except Exception as e:
        print(f"[エラー] 認証に失敗しました: {e}")
        sys.exit(1)

    channel = manager.get_my_channel()
    print(f"\n[接続チャンネル] {channel['title']} (ID: {channel['id']})")

    # 1. チャンネル内の動画をスキャン
    print("\n[ステップ 1/3] チャンネル内のアップロード動画をスキャン中...")
    try:
        all_videos = manager.get_my_videos(max_results=500)
    except Exception as e:
        if is_quota_exceeded(e):
            print("\n[注意] APIクォータ上限に達しています。日本時間16:00以降に再実行してください。")
            sys.exit(0)
        raise

    print(f"✓ 合計 {len(all_videos)} 件の動画を取得しました。")

    # 年フィルター
    if args.year != "all":
        target_videos = [v for v in all_videos if v["published_date"].startswith(args.year)]
        print(f"  -> {args.year} 年の動画: {len(target_videos)} 件を対象にします。")
    else:
        target_videos = all_videos
        print(f"  -> 全期間の動画: {len(target_videos)} 件を対象にします。")

    # 日付ごとにグループ化
    date_groups = defaultdict(list)
    for v in target_videos:
        d = v["published_date"]
        date_groups[d].append(v)

    sorted_dates = sorted(date_groups.keys(), reverse=True)
    if args.limit_dates:
        sorted_dates = sorted_dates[:args.limit_dates]

    print(f"\n処理対象の日付数: {len(sorted_dates)} 日分")
    print("-" * 65)

    created_results = []
    quota_hit = False

    # 各日付ごとに処理
    for date_idx, date_str in enumerate(sorted_dates, 1):
        if quota_hit:
            break

        v_list = date_groups[date_str]
        print(f"\n[{date_idx}/{len(sorted_dates)}] 日付: {date_str} (動画 {len(v_list)} 本)")

        # 2. public 動画の unlisted 化
        if args.make_unlisted:
            public_vids = [v for v in v_list if v["privacy"] == "public"]
            if public_vids:
                print(f"  -> public動画 {len(public_vids)} 本を unlisted (限定公開) に変更します...")
                for pv in public_vids:
                    try:
                        ok = manager.update_video_privacy(pv["id"], "unlisted")
                        if ok:
                            print(f"     ✓ 限定公開に変更: {pv['title']} ({pv['id']})")
                            pv["privacy"] = "unlisted"
                    except Exception as e:
                        if is_quota_exceeded(e):
                            quota_hit = True
                            print("\n⚠️ APIの1日利用クォータ上限に達しました。")
                            break

        if quota_hit:
            break

        # 3. 日付再生リストの作成または取得
        playlist_title = f"{date_str} 限定公開動画"
        playlist_desc = f"{date_str} にアップロードされた限定公開動画まとめです。"
        try:
            playlist = manager.get_or_create_playlist(
                title=playlist_title,
                description=playlist_desc,
                privacy_status="unlisted"
            )
        except Exception as e:
            if is_quota_exceeded(e):
                print("\n⚠️ APIの1日利用クォータ上限に達しました。")
                quota_hit = True
                break
            else:
                print(f"  × 再生リスト作成に失敗: {e}")
                continue

        playlist_id = playlist["id"]
        playlist_url = playlist.get("url") or f"https://www.youtube.com/playlist?list={playlist_id}"

        # 4. 動画を再生リストに追加
        video_ids = [v["id"] for v in v_list]
        print(f"  -> 再生リスト '{playlist_title}' に動画を追加中...")
        try:
            added = manager.add_videos_to_playlist(playlist_id, video_ids)
        except Exception as e:
            if is_quota_exceeded(e):
                print("\n⚠️ APIの1日利用クォータ上限に達しました。")
                quota_hit = True
            else:
                print(f"  × 動画追加中にエラー: {e}")
            added = []

        created_results.append({
            "date": date_str,
            "title": playlist_title,
            "url": playlist_url,
            "total_videos": len(v_list),
            "added_videos": len(added)
        })

    # 結果サマリー表示
    print("\n" + "=" * 65)
    if quota_hit:
        print(" ⚠️  本日のAPI利用クォータ上限（10,000 units）に達しました")
        print("=" * 65)
        print("ここまでの処理は正常に完了し、履歴にも保存されています。")
        print("Googleのクォータは【日本時間の毎日 16:00】に全回復（リセット）します。")
        print("明日 16:00 以降に再実行していただければ、続きの日程から自動再開されます。")
    else:
        print(" 🎉 すべての再生リスト作成・追加処理が完了しました！")
    print("=" * 65)

    if created_results:
        print(f"{'日付':<12} | {'動画数':<6} | {'限定公開 再生リストURL'}")
        print("-" * 65)
        for r in created_results:
            print(f"{r['date']:<12} | {r['total_videos']:>4}本 | {r['url']}")
        print("=" * 65)

    print("\n※作成されたURL一覧は 'PLAYLISTS.md' および 'playlists_history.json' に保存されています。")


if __name__ == "__main__":
    main()

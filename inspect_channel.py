import sys
from youtube_manager import YouTubeManager

try:
    manager = YouTubeManager()
    manager.authenticate()
    channel = manager.get_my_channel()
    print(f"チャンネル名: {channel['title']} (ID: {channel['id']})")
    
    videos = manager.get_my_videos(max_results=50)
    print(f"アップロード動画件数: {len(videos)}")
    for i, v in enumerate(videos, 1):
        print(f"{i}. 日付: {v['published_date']} ({v['published_at']}) | 公開状態: {v['privacy']} | タイトル: {v['title']} | ID: {v['id']}")
except Exception as e:
    print(f"エラー: {e}")
    sys.exit(1)

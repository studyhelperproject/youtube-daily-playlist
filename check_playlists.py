from youtube_manager import YouTubeManager

manager = YouTubeManager()
manager.authenticate()
res = manager.youtube.playlists().list(part="snippet,status", mine=True, maxResults=50).execute()
items = res.get("items", [])
print(f"既存再生リスト数: {len(items)}")
for it in items:
    privacy = it["status"]["privacyStatus"]
    title = it["snippet"]["title"]
    pid = it["id"]
    print(f"- [{privacy}] {title} (ID: {pid})")

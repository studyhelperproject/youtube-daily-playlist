"""
YouTube API を操作して限定公開再生リストの作成や動画追加、自チャンネル動画の取得を行うモジュール
"""

import os
import re
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# コンソールの文字エンコーディング設定
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly"
]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"
HISTORY_FILE = "playlists_history.json"

# 日本時間 (JST: UTC+9)
JST = timezone(timedelta(hours=9))


def extract_video_id(url_or_id: str) -> Optional[str]:
    """YouTubeのURLまたは直接の動画IDから11文字のvideoIdを抽出する"""
    url_or_id = url_or_id.strip()
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url_or_id):
        return url_or_id

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None


class YouTubeManager:
    def __init__(self, client_secret_path: str = CLIENT_SECRET_FILE, token_path: str = TOKEN_FILE):
        self.client_secret_path = client_secret_path
        self.token_path = token_path
        self.youtube = None

    def authenticate(self, force_reauth: bool = False) -> Any:
        """
        OAuth 2.0 による認証を行い、YouTube API クライアントを初期化する。
        優先順位:
          1. 環境変数 YOUTUBE_TOKEN_JSON（Cloud Run などのクラウド環境向け）
          2. ローカルファイル token.json
          3. client_secret.json からブラウザ認証フロー
        """
        creds = None

        if not force_reauth:
            # 1. 環境変数からのロード（Cloud Run / Docker環境用）
            env_token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
            if env_token_str:
                try:
                    token_data = json.loads(env_token_str)
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                    print("[認証] 環境変数 'YOUTUBE_TOKEN_JSON' から認証情報を読み込みました。")
                except Exception as e:
                    print(f"[警告] 環境変数のトークン読み込みに失敗しました: {e}")
                    creds = None

            # 2. ローカルファイルからのロード
            if not creds and os.path.exists(self.token_path):
                try:
                    creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
                except Exception as e:
                    print(f"既存のトークンファイルの読み込みに失敗しました: {e}")
                    creds = None

            # 3. トークンの有効期限切れリフレッシュ
            if creds and not creds.valid:
                if creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        print("[認証] トークンを自動リフレッシュしました。")
                        # ローカル実行の場合、リフレッシュされた最新トークンを保存
                        if os.path.exists(self.token_path) and not env_token_str:
                            with open(self.token_path, "w", encoding="utf-8") as token_file:
                                token_file.write(creds.to_json())
                    except Exception as e:
                        print(f"トークンのリフレッシュに失敗しました（有効期限切れまたは失効）: {e}")
                        if env_token_str:
                            raise RuntimeError(
                                "[認証失敗] クラウド環境変数 'YOUTUBE_TOKEN_JSON' のリフレッシュトークンが失効しています。\n"
                                "Google Cloud Consoleの『OAuth 同意画面』が『本番環境（In Production）』になっているか確認の上、\n"
                                "ローカルで再認証を行って Cloud Run に再デプロイしてください。"
                            ) from e
                        creds = None
                else:
                    creds = None

        # 4. ブラウザ認証（ローカル開発環境のみ）
        if not creds:
            if not os.path.exists(self.client_secret_path):
                raise FileNotFoundError(
                    f"OAuth認証情報ファイル '{self.client_secret_path}' または有効な環境変数 'YOUTUBE_TOKEN_JSON' が見つかりません。"
                )

            flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES)
            print("\n========================================================")
            print("[認証] ブラウザが開きます。YouTubeチャンネルを管理するGoogleアカウントでログイン・承認してください...")
            print("※『このアプリは Google で確認されていません』と表示された場合は、")
            print("  『詳細』をクリックして『安全ではないページに移動（続行）』を選択してください。")
            print("========================================================\n")
            creds = flow.run_local_server(port=0)

            with open(self.token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
            print(f"[認証完了] 新しいトークンを '{self.token_path}' に保存しました。")

        self.youtube = build("youtube", "v3", credentials=creds)
        return self.youtube

    def get_my_channel(self) -> Dict[str, Any]:
        """認証中ユーザーのチャンネル情報（チャンネル名、ID、アップロード用再生リストID）を取得"""
        if not self.youtube:
            self.authenticate()

        res = self.youtube.channels().list(
            mine=True,
            part="snippet,contentDetails"
        ).execute()

        items = res.get("items", [])
        if not items:
            raise RuntimeError("YouTubeチャンネルが見つかりませんでした。")

        channel = items[0]
        channel_title = channel["snippet"]["title"]
        uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]

        return {
            "id": channel["id"],
            "title": channel_title,
            "uploads_playlist_id": uploads_playlist_id
        }

    def get_my_videos(
        self,
        max_results: int = 50,
        date_filter: Optional[str] = None,
        privacy_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """自チャンネルのアップロード動画一覧を取得する"""
        channel = self.get_my_channel()
        uploads_id = channel["uploads_playlist_id"]

        videos = []
        next_page_token = None

        while len(videos) < max_results:
            fetch_count = min(50, max_results - len(videos))
            res = self.youtube.playlistItems().list(
                playlistId=uploads_id,
                part="snippet,status",
                maxResults=fetch_count,
                pageToken=next_page_token
            ).execute()

            items = res.get("items", [])
            if not items:
                break

            for item in items:
                snippet = item["snippet"]
                status = item.get("status", {})

                published_utc_str = snippet.get("publishedAt", "")
                published_jst_str = ""
                published_jst_date = ""

                if published_utc_str:
                    try:
                        utc_dt = datetime.fromisoformat(published_utc_str.replace("Z", "+00:00"))
                        jst_dt = utc_dt.astimezone(JST)
                        published_jst_str = jst_dt.strftime("%Y-%m-%d %H:%M:%S")
                        published_jst_date = jst_dt.strftime("%Y-%m-%d")
                    except Exception:
                        published_jst_date = published_utc_str[:10]

                video_id = snippet["resourceId"]["videoId"]
                privacy = status.get("privacyStatus", "unknown")

                if date_filter and published_jst_date != date_filter:
                    continue

                if privacy_filter and privacy != privacy_filter:
                    continue

                videos.append({
                    "id": video_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": published_jst_str or published_utc_str,
                    "published_date": published_jst_date,
                    "privacy": privacy,
                    "url": f"https://youtu.be/{video_id}"
                })

            next_page_token = res.get("nextPageToken")
            if not next_page_token:
                break

        return videos

    def update_video_privacy(self, video_id: str, privacy_status: str = "unlisted") -> bool:
        """動画の公開設定（public, unlisted, private）を変更する"""
        if not self.youtube:
            self.authenticate()

        try:
            res = self.youtube.videos().list(
                id=video_id,
                part="snippet,status"
            ).execute()

            items = res.get("items", [])
            if not items:
                print(f"  × 動画が見つかりません: {video_id}")
                return False

            video_data = items[0]
            current_status = video_data["status"]
            if current_status.get("privacyStatus") == privacy_status:
                return True

            current_status["privacyStatus"] = privacy_status
            body = {
                "id": video_id,
                "status": current_status
            }
            if "snippet" in video_data and "categoryId" in video_data["snippet"]:
                body["snippet"] = {
                    "title": video_data["snippet"]["title"],
                    "categoryId": video_data["snippet"]["categoryId"]
                }
                part = "snippet,status"
            else:
                part = "status"

            self.youtube.videos().update(
                part=part,
                body=body
            ).execute()
            return True
        except HttpError as e:
            print(f"  × 動画 {video_id} の公開ステータス変更に失敗: {e}")
            raise

    def get_my_playlists(self) -> List[Dict[str, Any]]:
        """自チャンネルの作成済み再生リスト一覧を取得する"""
        if not self.youtube:
            self.authenticate()

        playlists = []
        next_page = None
        while True:
            res = self.youtube.playlists().list(
                part="snippet,status",
                mine=True,
                maxResults=50,
                pageToken=next_page
            ).execute()
            for it in res.get("items", []):
                playlists.append({
                    "id": it["id"],
                    "title": it["snippet"]["title"],
                    "privacy": it["status"]["privacyStatus"],
                    "url": f"https://www.youtube.com/playlist?list={it['id']}"
                })
            next_page = res.get("nextPageToken")
            if not next_page:
                break
        return playlists

    def get_playlist_video_ids(self, playlist_id: str) -> List[str]:
        """再生リストに含まれる動画ID一覧を取得する（二重追加防止用）"""
        if not self.youtube:
            self.authenticate()

        video_ids = []
        next_page = None
        try:
            while True:
                res = self.youtube.playlistItems().list(
                    playlistId=playlist_id,
                    part="snippet",
                    maxResults=50,
                    pageToken=next_page
                ).execute()
                for item in res.get("items", []):
                    vid = item.get("snippet", {}).get("resourceId", {}).get("videoId")
                    if vid:
                        video_ids.append(vid)
                next_page = res.get("nextPageToken")
                if not next_page:
                    break
        except HttpError:
            return []
        return video_ids

    def get_or_create_playlist(
        self,
        title: str,
        description: str = "",
        privacy_status: str = "unlisted"
    ) -> Dict[str, Any]:
        """同名再生リストが既にあれば取得し、なければ新規作成する"""
        existing = self.get_my_playlists()
        for pl in existing:
            if pl["title"] == title:
                print(f"  [既存再生リストを使用] '{title}' (ID: {pl['id']})")
                pl["is_new"] = False
                return pl

        created = self.create_playlist(title, description, privacy_status)
        created["is_new"] = True
        return created

    def create_playlist(
        self,
        title: str,
        description: str = "",
        privacy_status: str = "unlisted"
    ) -> Dict[str, Any]:
        """限定公開再生リストを作成する"""
        if not self.youtube:
            self.authenticate()

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "defaultLanguage": "ja",
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }

        try:
            response = self.youtube.playlists().insert(
                part="snippet,status",
                body=body
            ).execute()

            playlist_id = response["id"]
            playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"

            result = {
                "id": playlist_id,
                "url": playlist_url,
                "title": title,
                "privacy": privacy_status,
                "created_at": datetime.now(JST).isoformat(),
                "is_new": True
            }

            self._save_to_history(result)
            return result

        except HttpError as e:
            print(f"再生リスト作成中にエラーが発生しました: {e}")
            raise

    def add_videos_to_playlist(
        self,
        playlist_id: str,
        video_urls_or_ids: List[str],
        skip_duplicate_check: bool = False
    ) -> List[Dict[str, Any]]:
        """再生リストに動画を追加する"""
        if not self.youtube:
            self.authenticate()

        if skip_duplicate_check:
            existing_ids = set()
        else:
            existing_ids = set(self.get_playlist_video_ids(playlist_id))

        added_videos = []

        for item in video_urls_or_ids:
            video_id = extract_video_id(item)
            if not video_id:
                print(f"  [スキップ] 有効な動画ID/URLではありません: {item}")
                continue

            if video_id in existing_ids:
                print(f"  - 既に登録済みのためスキップ: {video_id}")
                continue

            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.youtube.playlistItems().insert(
                        part="snippet",
                        body=body
                    ).execute()

                    title = response.get("snippet", {}).get("title", video_id)
                    print(f"  ✓ 追加成功: {title} (ID: {video_id})")
                    added_videos.append({
                        "video_id": video_id,
                        "title": title,
                        "item_id": response["id"]
                    })
                    existing_ids.add(video_id)
                    break
                except HttpError as e:
                    if "playlistNotFound" in str(e) and attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    print(f"  × 追加失敗: 動画ID {video_id} - {e}")
                    raise

        return added_videos

    def _save_to_history(self, playlist_info: Dict[str, Any]):
        """作成した再生リストの履歴をJSONファイルに保存する"""
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        if not any(h.get("id") == playlist_info.get("id") for h in history):
            clean_info = {k: v for k, v in playlist_info.items() if k != "is_new"}
            history.append(clean_info)
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

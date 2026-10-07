"""YouTube Data API でキーワード検索し、再生回数の多い順にタイトルとURLを表示する。"""

import html
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CONFIG_PATH = Path(__file__).with_name("config.json")
DISPLAY_COUNT = 5


def load_api_key(path: Path = CONFIG_PATH) -> str:
    """設定ファイルから YouTube Data API のキーを読み込む。"""
    try:
        with path.open(encoding="utf-8") as file:
            config = json.load(file)
    except FileNotFoundError:
        raise SystemExit(f"設定ファイルが見つかりません: {path}") from None
    except json.JSONDecodeError as error:
        raise SystemExit(f"設定ファイルの形式が正しくありません: {error}") from error

    api_key = str(config.get("api_key", "")).strip()
    if not api_key:
        raise SystemExit("設定ファイルに api_key がありません。")
    return api_key


def request_json(url: str, params: dict) -> dict:
    """YouTube Data API へ GET し、JSON を返す。"""
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}")
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"APIリクエストに失敗しました (HTTP {error.code}): {detail}"
        ) from error


def search_videos(
    keyword: str, api_key: str, max_results: int = DISPLAY_COUNT
) -> list[dict]:
    """キーワードに一致する動画を再生回数の多い順に探す。"""
    data = request_json(
        SEARCH_URL,
        {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "maxResults": max_results,
            "key": api_key,
        },
    )

    videos = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        title = item.get("snippet", {}).get("title")
        if title:
            title = html.unescape(title)
        if not video_id or not title:
            continue
        videos.append(
            {
                "id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )
    return videos


def attach_view_counts(videos: list[dict], api_key: str) -> list[dict]:
    """動画IDから再生回数を取得して各動画に加える。"""
    if not videos:
        return videos

    data = request_json(
        VIDEOS_URL,
        {
            "part": "statistics",
            "id": ",".join(video["id"] for video in videos),
            "key": api_key,
        },
    )
    counts = {}
    for item in data.get("items", []):
        raw_count = item.get("statistics", {}).get("viewCount")
        counts[item.get("id")] = int(raw_count) if raw_count is not None else 0

    for video in videos:
        video["view_count"] = counts.get(video["id"], 0)
    return videos


def top_by_views(videos: list[dict], limit: int = DISPLAY_COUNT) -> list[dict]:
    """再生回数の多い順に並べ、上位だけを返す。"""
    ranked = sorted(videos, key=lambda video: video["view_count"], reverse=True)
    return ranked[:limit]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) > 1:
        keyword = " ".join(sys.argv[1:])
    else:
        keyword = input("検索キーワードを入力してください: ").strip()

    if not keyword:
        raise SystemExit("キーワードが空です。")

    api_key = load_api_key()
    videos = top_by_views(attach_view_counts(search_videos(keyword, api_key), api_key))
    if not videos:
        print("該当する動画は見つかりませんでした。")
        return

    print(f"「{keyword}」の再生回数上位 ({len(videos)}件)")
    print("-" * 40)
    for index, video in enumerate(videos, start=1):
        print(f"{index}. {video['title']}")
        print(f"   {video['url']}")
        print(f"   再生回数: {video['view_count']:,}")


if __name__ == "__main__":
    main()

import re
from urllib.parse import parse_qs, urlparse

VIDEO_ID_PATTERN  = re.compile(r'^[A-Za-z0-9_-]{11}$')

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}

def extract_youtube_video_id(url: str) -> str:
    parsed_url = urlparse(url.strip())

    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("URL must start with http or https.")

    host = parsed_url.netloc.lower()

    if host not in YOUTUBE_HOSTS:
        raise ValueError("URL must be from YouTube.")
    if host == 'youtu.be':
        video_id = parsed_url.path.strip("/").split("/")[0]
        return _validate_video_id(video_id)

    if parsed_url.path == '/watch':
        query_params = parse_qs(parsed_url.query)
        video_id_list = query_params.get('v')
        if not video_id_list:
            raise ValueError("YouTube URL must contain a 'v' query parameter.")
        video_id = video_id_list[0]
        return _validate_video_id(video_id)
    path_parts = parsed_url.path.strip('/').split('/')

    if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts", "live"}:
        video_id = path_parts[1]
        return _validate_video_id(video_id)
    raise ValueError("Could not extract video ID from the provided URL.")

def _validate_video_id(video_id: str) -> str:
    if not VIDEO_ID_PATTERN.match(video_id):
        raise ValueError("Invalid YouTube video ID.")
    return video_id
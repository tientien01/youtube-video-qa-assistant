import re
from urllib.parse import parse_qs, urlparse


VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def parse_youtube_video_url(url: str) -> tuple[str, str]:
    """Return the stable video id and canonical watch URL."""

    parsed_url = urlparse(url.strip())
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("URL must start with http or https.")

    host = parsed_url.netloc.lower()
    if host not in YOUTUBE_HOSTS:
        raise ValueError("URL must be from YouTube.")

    if host == "youtu.be":
        video_id = parsed_url.path.strip("/").split("/")[0]
    elif parsed_url.path == "/watch":
        values = parse_qs(parsed_url.query).get("v")
        if not values:
            raise ValueError("YouTube URL must contain a 'v' query parameter.")
        video_id = values[0]
    else:
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) < 2 or path_parts[0] not in {"embed", "shorts", "live"}:
            raise ValueError("Could not extract video ID from the provided URL.")
        video_id = path_parts[1]

    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("Invalid YouTube video ID.")
    return video_id, f"https://www.youtube.com/watch?v={video_id}"

from app.domain.video_identity import parse_youtube_video_url


def extract_youtube_video_id(url: str) -> str:
    return parse_youtube_video_url(url)[0]

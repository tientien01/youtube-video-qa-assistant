from dataclasses import dataclass

import httpx


OEMBED_URL = "https://www.youtube.com/oembed"


@dataclass(frozen=True)
class YouTubeMetadata:
    title: str | None
    channel_title: str | None
    thumbnail_url: str | None


def fetch_youtube_metadata(url: str) -> YouTubeMetadata:
    try:
        response = httpx.get(
            OEMBED_URL,
            params={"url": url, "format": "json"},
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return YouTubeMetadata(title=None, channel_title=None, thumbnail_url=None)

    payload = response.json()
    return YouTubeMetadata(
        title=_optional_text(payload.get("title")),
        channel_title=_optional_text(payload.get("author_name")),
        thumbnail_url=_optional_text(payload.get("thumbnail_url")),
    )


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    stripped_value = value.strip()
    return stripped_value or None

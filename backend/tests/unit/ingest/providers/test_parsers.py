import pytest

from app.application.ingest.transcript import SubtitleFormat
from app.infrastructure.ingest.transcript.parsers import SubtitleParseError, parse_subtitle


@pytest.mark.parametrize(
    ("subtitle_format", "payload", "expected_text", "expected_range"),
    [
        (
            SubtitleFormat.VTT,
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nHello &amp; welcome\n",
            "Hello & welcome",
            (1000, 2500),
        ),
        (
            SubtitleFormat.TTML,
            '<tt xmlns="http://www.w3.org/ns/ttml"><body><p begin="1.5s" dur="2s">Xin <span>chào</span></p></body></tt>',
            "Xin chào",
            (1500, 3500),
        ),
        (
            SubtitleFormat.SRV3,
            '<timedtext><body><p t="3000" d="1250"><s>Generated caption</s></p></body></timedtext>',
            "Generated caption",
            (3000, 4250),
        ),
    ],
)
def test_each_supported_format_uses_its_own_parser(
    subtitle_format: SubtitleFormat,
    payload: str,
    expected_text: str,
    expected_range: tuple[int, int],
) -> None:
    segments = parse_subtitle(payload, subtitle_format)

    assert segments[0].text == expected_text
    assert (segments[0].start_ms, segments[0].end_ms) == expected_range


@pytest.mark.parametrize(
    ("subtitle_format", "payload"),
    [
        (SubtitleFormat.VTT, "WEBVTT\n\n00:00:02.000 --> 00:00:01.000\nBackwards\n"),
        (SubtitleFormat.TTML, "<tt><body><p begin='bad' end='2s'>Text</p></body></tt>"),
        (SubtitleFormat.SRV3, "<timedtext><p t='0' d='0'>Zero duration</p></timedtext>"),
    ],
)
def test_parser_rejects_invalid_timestamp_ranges(subtitle_format: SubtitleFormat, payload: str) -> None:
    with pytest.raises(SubtitleParseError):
        parse_subtitle(payload, subtitle_format)


def test_ttml_is_never_silently_parsed_as_vtt() -> None:
    ttml = "<tt><body><p begin='1s' end='2s'>Text</p></body></tt>"

    with pytest.raises(SubtitleParseError, match="no usable cues"):
        parse_subtitle(ttml, SubtitleFormat.VTT)

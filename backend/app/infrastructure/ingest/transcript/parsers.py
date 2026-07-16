from __future__ import annotations

import html
import re
from collections.abc import Callable
from xml.etree import ElementTree

from app.application.ingest.transcript import SourceTranscriptSegment, SubtitleFormat


MAX_SUBTITLE_CHARACTERS = 5_000_000
VTT_TIMING = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
TAG_PATTERN = re.compile(r"<[^>]+>")
OFFSET_TIME = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s)$")


class SubtitleParseError(ValueError):
    pass


def parse_subtitle(payload: str, subtitle_format: SubtitleFormat) -> tuple[SourceTranscriptSegment, ...]:
    if len(payload) > MAX_SUBTITLE_CHARACTERS:
        raise SubtitleParseError("Subtitle payload exceeds the local safety limit.")
    parsers: dict[SubtitleFormat, Callable[[str], list[SourceTranscriptSegment]]] = {
        SubtitleFormat.VTT: parse_vtt,
        SubtitleFormat.TTML: parse_ttml,
        SubtitleFormat.SRV3: parse_srv3,
    }
    parser = parsers.get(subtitle_format)
    if parser is None:
        raise SubtitleParseError(f"Unsupported subtitle format: {subtitle_format.value}.")
    segments = parser(payload)
    if not segments:
        raise SubtitleParseError("Subtitle payload contains no usable cues.")
    return tuple(segments)


def parse_vtt(payload: str) -> list[SourceTranscriptSegment]:
    lines = payload.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    segments: list[SourceTranscriptSegment] = []
    index = 0
    while index < len(lines):
        match = VTT_TIMING.search(lines[index].strip())
        if match is None:
            index += 1
            continue
        start_ms = _clock_time_ms(match.group("start"))
        end_ms = _clock_time_ms(match.group("end"))
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            cleaned = _clean_markup(lines[index])
            if cleaned:
                text_lines.append(cleaned)
            index += 1
        _append_segment(segments, " ".join(text_lines), start_ms, end_ms)
    return segments


def parse_ttml(payload: str) -> list[SourceTranscriptSegment]:
    root = _xml_root(payload)
    segments: list[SourceTranscriptSegment] = []
    for element in root.iter():
        if _local_name(element.tag) != "p":
            continue
        begin = element.attrib.get("begin")
        if begin is None:
            raise SubtitleParseError("TTML cue is missing begin time.")
        start_ms = _time_expression_ms(begin)
        if "end" in element.attrib:
            end_ms = _time_expression_ms(element.attrib["end"])
        elif "dur" in element.attrib:
            end_ms = start_ms + _time_expression_ms(element.attrib["dur"])
        else:
            raise SubtitleParseError("TTML cue is missing end or duration.")
        _append_segment(segments, "".join(element.itertext()), start_ms, end_ms)
    return segments


def parse_srv3(payload: str) -> list[SourceTranscriptSegment]:
    root = _xml_root(payload)
    segments: list[SourceTranscriptSegment] = []
    for element in root.iter():
        name = _local_name(element.tag)
        if name == "p" and "t" in element.attrib:
            start_ms = _integer_ms(element.attrib["t"], "SRV3 start")
            duration_ms = _integer_ms(element.attrib.get("d", "0"), "SRV3 duration")
        elif name == "text" and "start" in element.attrib:
            start_ms = round(_number(element.attrib["start"], "SRV3 start") * 1000)
            duration_ms = round(_number(element.attrib.get("dur", "0"), "SRV3 duration") * 1000)
        else:
            continue
        _append_segment(segments, "".join(element.itertext()), start_ms, start_ms + duration_ms)
    return segments


def _xml_root(payload: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        raise SubtitleParseError("Subtitle XML is malformed.") from error


def _append_segment(
    segments: list[SourceTranscriptSegment],
    text: str,
    start_ms: int,
    end_ms: int,
) -> None:
    cleaned = _clean_markup(text)
    if not cleaned:
        return
    try:
        segments.append(SourceTranscriptSegment(text=cleaned, start_ms=start_ms, end_ms=end_ms))
    except ValueError as error:
        raise SubtitleParseError(str(error)) from error


def _clean_markup(text: str) -> str:
    return " ".join(html.unescape(TAG_PATTERN.sub("", text)).split())


def _clock_time_ms(value: str) -> int:
    normalized = value.replace(",", ".")
    parts = normalized.split(":")
    if len(parts) not in {2, 3}:
        raise SubtitleParseError(f"Unsupported clock time: {value}.")
    try:
        seconds = float(parts[-1])
        minutes = int(parts[-2])
        hours = int(parts[-3]) if len(parts) == 3 else 0
    except ValueError as error:
        raise SubtitleParseError(f"Invalid clock time: {value}.") from error
    return round(((hours * 60 * 60) + (minutes * 60) + seconds) * 1000)


def _time_expression_ms(value: str) -> int:
    match = OFFSET_TIME.fullmatch(value.strip())
    if match:
        number = float(match.group("value"))
        return round(number if match.group("unit") == "ms" else number * 1000)
    return _clock_time_ms(value.strip())


def _integer_ms(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise SubtitleParseError(f"{label} is invalid.") from error


def _number(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise SubtitleParseError(f"{label} is invalid.") from error


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

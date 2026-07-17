from app.application.chunking import ChunkerConfig, HierarchicalChunker
from app.domain.entities import TranscriptSegment

from tests.unit.chunking.helpers import PunctuationSegmenter, WhitespaceTokenCounter


def test_canonical_segments_produce_ordered_exact_source_links() -> None:
    segments = [
        TranscriptSegment("transcript-1", 0, "First.", "First.", 100, 900, id="s0"),
        TranscriptSegment("transcript-1", 1, "Second.", "Second.", 900, 1_800, id="s1"),
        TranscriptSegment("transcript-1", 2, "Third.", "Third.", 1_800, 2_700, id="s2"),
    ]
    chunker = HierarchicalChunker(
        PunctuationSegmenter(),
        WhitespaceTokenCounter(),
        ChunkerConfig(child_target_tokens=2, child_max_tokens=3, child_overlap_tokens=1),
    )

    result = chunker.chunk(
        video_id="video-1",
        transcript_id="transcript-1",
        index_version_id="index-1",
        index_fingerprint=chunker.fingerprint("canonical-hash"),
        language_code="en",
        segments=segments,
    )

    links_by_chunk = {
        chunk.id: [link.transcript_segment_id for link in result.links if link.chunk_id == chunk.id]
        for chunk in result.chunks
    }
    for chunk in result.chunks:
        linked = links_by_chunk[chunk.id]
        linked_segments = [segments[int(segment_id[1:])] for segment_id in linked]
        assert linked == sorted(linked, key=lambda value: int(value[1:]))
        assert chunk.start_ms == linked_segments[0].start_ms
        assert chunk.end_ms == linked_segments[-1].end_ms
    assert all(child.parent_chunk_id for child in result.child_chunks)

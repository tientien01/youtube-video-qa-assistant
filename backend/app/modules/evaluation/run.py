from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.application.chunking import HierarchicalChunker
from app.application.chunking.models import ChunkerConfig
from app.domain.entities import ChunkType, TranscriptSegment
from app.infrastructure.chunking.sentence_segmenters import RegexSentenceSegmenter
from app.infrastructure.chunking.token_counters import HuggingFaceTokenCounter
from app.infrastructure.embeddings.ollama import OllamaEmbedding
from app.infrastructure.reranking.bge import BgeCrossEncoderReranker


ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class EvalChunk:
    chunk_id: str
    video_id: str
    text: str
    segment_ids: tuple[str, ...]


class Embedder(Protocol):
    name: str

    def documents(self, texts: list[str]) -> list[list[float]]: ...

    def queries(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder:
    def __init__(self, *, model: str, base_url: str) -> None:
        self.name = f"ollama/{model}"
        self._adapter = OllamaEmbedding(model=model, base_url=base_url)

    def documents(self, texts: list[str]) -> list[list[float]]:
        return self._adapter.embed_documents(texts)

    def queries(self, texts: list[str]) -> list[list[float]]:
        return [self._adapter.embed_query(text) for text in texts]


class SentenceTransformerEmbedder:
    def __init__(self, model: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.name = model
        self._model = SentenceTransformer(model, local_files_only=True)

    def documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def queries(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        values = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [[float(item) for item in vector] for vector in values]


def main() -> int:
    args = _parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.select_existing:
        _select_existing(config)
        return 0
    dataset_path = ROOT / config["dataset"]
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    _validate_dataset(dataset)

    report_path = ROOT / config["report_json"]
    markdown_path = ROOT / config["report_markdown"]
    report = evaluate(config, dataset, dataset_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    print(f"Evaluation report: {report_path.relative_to(ROOT)}")
    print(f"Recommended default: {report['recommendation']['variant_id']}")
    return 0


def evaluate(config: dict[str, Any], dataset: dict[str, Any], dataset_path: Path) -> dict[str, Any]:
    tracemalloc.start()
    started = time.perf_counter()
    questions = dataset["questions"]
    chunks_by_strategy = {
        "fixed_word": _fixed_chunks(dataset, config["fixed_word"]),
        "hierarchical_sentence": _hierarchical_chunks(dataset, config["hierarchical_sentence"]),
    }
    embedders: list[Embedder] = [
        OllamaEmbedder(model=config["embeddings"]["qwen3"]["model"], base_url=config["ollama_base_url"]),
        SentenceTransformerEmbedder(config["embeddings"]["bge_m3"]["model"]),
    ]
    reranker = BgeCrossEncoderReranker(config["reranker"]["model"])
    variants: list[dict[str, Any]] = []
    for chunker_name, chunks in chunks_by_strategy.items():
        lexical_rankings, lexical_latencies = _timed_rankings(
            lambda item: _lexical_rank(item["question"], item["video_id"], chunks), questions
        )
        variants.append(
            _variant_result(
                chunker=chunker_name,
                embedding="none",
                mode="lexical",
                chunks=chunks,
                questions=questions,
                rankings=lexical_rankings,
                latencies=lexical_latencies,
                top_k=int(config["top_k"]),
                index_ms=0.0,
            )
        )
        reranker_scores, reranker_latencies = _reranker_scores(reranker, questions, chunks)
        for embedder in embedders:
            index_started = time.perf_counter()
            document_vectors = embedder.documents([chunk.text for chunk in chunks])
            index_ms = _ms(index_started)
            dense_rankings = []
            dense_latencies = []
            for question in questions:
                query_started = time.perf_counter()
                query_vector = embedder.queries([question["question"]])[0]
                dense_rankings.append(_dense_rank(question["video_id"], query_vector, chunks, document_vectors))
                dense_latencies.append(_ms(query_started))
            rrf_rankings, rrf_latencies = _timed_pairs(_rrf, lexical_rankings, dense_rankings)
            rankings = {
                "dense": dense_rankings,
                "rrf": rrf_rankings,
                "reranked": [_rerank(rrf_rankings[index], reranker_scores[index]) for index in range(len(questions))],
            }
            mode_latencies = {
                "dense": dense_latencies,
                "rrf": [
                    dense + lexical + fusion
                    for dense, lexical, fusion in zip(dense_latencies, lexical_latencies, rrf_latencies, strict=True)
                ],
                "reranked": [
                    dense + lexical + fusion + rerank
                    for dense, lexical, fusion, rerank in zip(
                        dense_latencies, lexical_latencies, rrf_latencies, reranker_latencies, strict=True
                    )
                ],
            }
            for mode, mode_rankings in rankings.items():
                variants.append(
                    _variant_result(
                        chunker=chunker_name,
                        embedding=embedder.name,
                        mode=mode,
                        chunks=chunks,
                        questions=questions,
                        rankings=mode_rankings,
                        latencies=mode_latencies[mode],
                        top_k=int(config["top_k"]),
                        index_ms=index_ms,
                    )
                )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    recommendation = _recommend(variants, float(config["quality_equivalence_margin"]))
    return {
        "schema_version": "1.0",
        "dataset": {
            "id": dataset["dataset_id"],
            "version": dataset["version"],
            "sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            "question_count": len(questions),
            "reviewed_count": sum(item["review"]["status"] == "reviewed" for item in questions),
        },
        "config_sha256": _fingerprint(config),
        "hardware": {
            "platform": platform.platform(),
            "processor": platform.processor() or "unreported",
            "logical_cpu_count": os.cpu_count(),
            "python": platform.python_version(),
        },
        "run": {
            "duration_ms": _ms(started),
            "python_peak_memory_mb": round(peak / 1024 / 1024, 2),
        },
        "variants": variants,
        "recommendation": {
            "variant_id": recommendation["variant_id"],
            "selection_policy": (
                "within the post-baseline 0.01 citation/nDCG equivalence margin, choose lower p95 latency; "
                "then Recall@K and MRR"
            ),
            "quality": recommendation["quality"],
            "cost": recommendation["cost"],
        },
    }


def _fixed_chunks(dataset: dict[str, Any], config: dict[str, Any]) -> list[EvalChunk]:
    target = int(config["words"])
    overlap = int(config["overlap_words"])
    output: list[EvalChunk] = []
    for video in dataset["videos"]:
        words: list[tuple[str, str]] = []
        for segment in video["segments"]:
            words.extend((word, segment["segment_id"]) for word in segment["text"].split())
        start = 0
        sequence = 0
        while start < len(words):
            window = words[start : start + target]
            segment_ids = tuple(dict.fromkeys(segment_id for _, segment_id in window))
            output.append(
                EvalChunk(
                    f"{video['video_id']}-fixed-{sequence:03d}",
                    video["video_id"],
                    " ".join(word for word, _ in window),
                    segment_ids,
                )
            )
            sequence += 1
            if start + target >= len(words):
                break
            start += target - overlap
    return output


def _hierarchical_chunks(dataset: dict[str, Any], config: dict[str, Any]) -> list[EvalChunk]:
    counter = HuggingFaceTokenCounter(config["tokenizer_model"])
    chunker = HierarchicalChunker(
        RegexSentenceSegmenter(),
        counter,
        ChunkerConfig(**config["chunker_config"]),
    )
    output: list[EvalChunk] = []
    for video in dataset["videos"]:
        transcript_id = f"{video['video_id']}-transcript"
        segments = [
            TranscriptSegment(
                id=item["segment_id"],
                transcript_id=transcript_id,
                sequence_number=index,
                original_text=item["text"],
                normalized_text=item["text"],
                start_ms=item["start_ms"],
                end_ms=item["end_ms"],
            )
            for index, item in enumerate(video["segments"])
        ]
        result = chunker.chunk(
            video_id=video["video_id"],
            transcript_id=transcript_id,
            index_version_id=f"{video['video_id']}-evaluation-index",
            index_fingerprint="local-v1-evaluation",
            language_code=video["language"],
            segments=segments,
        )
        links: dict[str, list[str]] = {}
        for link in result.links:
            links.setdefault(link.chunk_id, []).append(link.transcript_segment_id)
        output.extend(
            EvalChunk(chunk.id, video["video_id"], chunk.text, tuple(links.get(chunk.id, ())))
            for chunk in result.chunks
            if chunk.chunk_type is ChunkType.CHILD
        )
    return output


def _lexical_rank(query: str, video_id: str, chunks: list[EvalChunk]) -> list[tuple[str, float, float]]:
    terms = _terms(query)
    scored = []
    for chunk in chunks:
        if chunk.video_id != video_id:
            continue
        document = _terms(chunk.text)
        score = sum(document.count(term) for term in terms) / math.sqrt(max(len(document), 1))
        scored.append((chunk.chunk_id, score, 0.0))
    return sorted(scored, key=lambda item: (-item[1], item[0]))


def _dense_rank(
    video_id: str, query: list[float], chunks: list[EvalChunk], documents: list[list[float]]
) -> list[tuple[str, float, float]]:
    scored = [
        (chunk.chunk_id, _cosine(query, vector), 0.0)
        for chunk, vector in zip(chunks, documents, strict=True)
        if chunk.video_id == video_id
    ]
    return sorted(scored, key=lambda item: (-item[1], item[0]))


def _rrf(
    lexical: list[tuple[str, float, float]], dense: list[tuple[str, float, float]], rank_constant: int = 60
) -> list[tuple[str, float, float]]:
    scores: dict[str, float] = {}
    for ranking in (lexical, dense):
        for rank, (chunk_id, _, _) in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (rank_constant + rank)
    return [(chunk_id, score, 0.0) for chunk_id, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def _reranker_scores(
    reranker, questions: list[dict[str, Any]], chunks: list[EvalChunk]
) -> tuple[list[dict[str, float]], list[float]]:
    scores = []
    latencies = []
    for item in questions:
        started = time.perf_counter()
        values = reranker.score(item["question"], [chunk.text for chunk in chunks])
        latencies.append(_ms(started))
        scores.append(dict(zip((chunk.chunk_id for chunk in chunks), values, strict=True)))
    return scores, latencies


def _timed_rankings(function, items: list[Any]) -> tuple[list[Any], list[float]]:
    rankings = []
    latencies = []
    for item in items:
        started = time.perf_counter()
        rankings.append(function(item))
        latencies.append(_ms(started))
    return rankings, latencies


def _timed_pairs(function, left: list[Any], right: list[Any]) -> tuple[list[Any], list[float]]:
    rankings = []
    latencies = []
    for first, second in zip(left, right, strict=True):
        started = time.perf_counter()
        rankings.append(function(first, second))
        latencies.append(_ms(started))
    return rankings, latencies


def _rerank(ranking: list[tuple[str, float, float]], scores: dict[str, float]) -> list[tuple[str, float, float]]:
    return sorted(
        [(chunk_id, score, scores[chunk_id]) for chunk_id, score, _ in ranking],
        key=lambda item: (-item[2], -item[1], item[0]),
    )


def _variant_result(
    *,
    chunker: str,
    embedding: str,
    mode: str,
    chunks: list[EvalChunk],
    questions: list[dict[str, Any]],
    rankings: list[list[tuple[str, float, float]]],
    latencies: list[float],
    top_k: int,
    index_ms: float,
) -> dict[str, Any]:
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    metrics = []
    for question, ranking in zip(questions, rankings, strict=True):
        retrieved = [by_id[item[0]] for item in ranking[:top_k]]
        expected = set(question["relevant_segment_ids"])
        relevant = [bool(set(chunk.segment_ids) & expected) for chunk in retrieved]
        metrics.append(_question_metrics(relevant, expected, retrieved, top_k))
    quality = {
        key: round(statistics.fmean(item[key] for item in metrics), 4)
        for key in ("recall_at_k", "hit_rate_at_k", "mrr", "ndcg_at_k", "citation_accuracy")
    }
    unanswerable = [item for item in metrics if item["is_unanswerable"]]
    quality["unanswerable_false_positive_rate"] = round(
        statistics.fmean(item["unanswerable_false_positive"] for item in unanswerable), 4
    )
    return {
        "variant_id": f"{chunker}|{embedding}|{mode}",
        "chunker": chunker,
        "embedding": embedding,
        "retrieval": mode,
        "quality": quality,
        "cost": {
            "chunk_count": len(chunks),
            "index_time_ms": round(index_ms, 2),
            "p50_query_latency_ms": round(statistics.median(latencies), 4),
            "p95_query_latency_ms": round(_percentile(latencies, 0.95), 4),
        },
    }


def _question_metrics(
    relevant: list[bool], expected: set[str], retrieved: list[EvalChunk], top_k: int
) -> dict[str, float]:
    if not expected:
        return {
            "recall_at_k": 1.0,
            "hit_rate_at_k": 1.0,
            "mrr": 1.0,
            "ndcg_at_k": 1.0,
            "citation_accuracy": 1.0,
            "unanswerable_false_positive": float(bool(retrieved)),
            "is_unanswerable": 1.0,
        }
    covered = set().union(*(set(chunk.segment_ids) & expected for chunk in retrieved)) if retrieved else set()
    first = next((index for index, value in enumerate(relevant, start=1) if value), None)
    dcg = sum((1.0 if value else 0.0) / math.log2(index + 1) for index, value in enumerate(relevant, start=1))
    ideal_hits = min(sum(relevant), top_k)
    idcg = sum(1 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    cited_segments = sum(len(chunk.segment_ids) for chunk in retrieved)
    supported_segments = sum(len(set(chunk.segment_ids) & expected) for chunk in retrieved)
    return {
        "recall_at_k": len(covered) / len(expected),
        "hit_rate_at_k": float(any(relevant)),
        "mrr": 1 / first if first else 0.0,
        "ndcg_at_k": dcg / idcg if idcg else 0.0,
        "citation_accuracy": supported_segments / max(cited_segments, 1),
        "unanswerable_false_positive": 0.0,
        "is_unanswerable": 0.0,
    }


def _validate_dataset(dataset: dict[str, Any]) -> None:
    segment_ids = {segment["segment_id"] for video in dataset["videos"] for segment in video["segments"]}
    required_types = {"same_language", "cross_language", "keyword", "paraphrase", "multi_evidence", "unanswerable"}
    actual_types = {item["case_type"] for item in dataset["questions"]}
    if not required_types <= actual_types:
        raise ValueError(f"Dataset is missing required case types: {sorted(required_types - actual_types)}")
    for item in dataset["questions"]:
        if item["review"]["status"] != "reviewed":
            raise ValueError(f"Question {item['question_id']} is not reviewed.")
        unknown = set(item["relevant_segment_ids"]) - segment_ids
        if unknown:
            raise ValueError(f"Question {item['question_id']} references unknown segments: {sorted(unknown)}")
        if item["unanswerable"] != (not item["relevant_segment_ids"]):
            raise ValueError(f"Question {item['question_id']} has inconsistent unanswerable evidence.")


def _recommend(variants: list[dict[str, Any]], margin: float) -> dict[str, Any]:
    if not 0 <= margin < 1:
        raise ValueError("Quality equivalence margin must be between zero and one.")
    best_citation = max(item["quality"]["citation_accuracy"] for item in variants)
    citation_equivalent = [item for item in variants if item["quality"]["citation_accuracy"] >= best_citation - margin]
    best_ndcg = max(item["quality"]["ndcg_at_k"] for item in citation_equivalent)
    equivalent = [item for item in citation_equivalent if item["quality"]["ndcg_at_k"] >= best_ndcg - margin]
    return min(
        equivalent,
        key=lambda item: (
            item["cost"]["p95_query_latency_ms"],
            -item["quality"]["recall_at_k"],
            -item["quality"]["mrr"],
            item["variant_id"],
        ),
    )


def _select_existing(config: dict[str, Any]) -> None:
    report_path = ROOT / config["report_json"]
    markdown_path = ROOT / config["report_markdown"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    selected = _recommend(report["variants"], float(config["quality_equivalence_margin"]))
    report["config_sha256"] = _fingerprint(config)
    report["recommendation"] = {
        "variant_id": selected["variant_id"],
        "selection_policy": (
            "within the post-baseline 0.01 citation/nDCG equivalence margin, choose lower p95 latency; "
            "then Recall@K and MRR"
        ),
        "quality": selected["quality"],
        "cost": selected["cost"],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    print(f"Updated recommendation: {selected['variant_id']}")


def _markdown(report: dict[str, Any]) -> str:
    rows = []
    for item in report["variants"]:
        quality, cost = item["quality"], item["cost"]
        rows.append(
            f"| {item['variant_id']} | {quality['recall_at_k']:.4f} | {quality['hit_rate_at_k']:.4f} | "
            f"{quality['mrr']:.4f} | {quality['ndcg_at_k']:.4f} | {quality['citation_accuracy']:.4f} | "
            f"{cost['index_time_ms']:.2f} | {cost['p95_query_latency_ms']:.4f} |"
        )
    return (
        "# Local V1 Retrieval Evaluation\n\n"
        f"Dataset: `{report['dataset']['id']}@{report['dataset']['version']}` "
        f"({report['dataset']['reviewed_count']} reviewed questions).\n\n"
        "No release threshold was chosen before this baseline. The recommendation follows the committed selection policy.\n\n"
        "| Variant | Recall@K | Hit@K | MRR | nDCG@K | Citation accuracy | Index ms | p95 query ms |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n" + "\n".join(rows) + "\n\n## Recommendation\n\n"
        f"`{report['recommendation']['variant_id']}`\n\n"
        f"Policy: {report['recommendation']['selection_policy']}.\n\n"
        "## Hardware/config fingerprint\n\n"
        f"- Config SHA-256: `{report['config_sha256']}`\n"
        f"- Platform: `{report['hardware']['platform']}`\n"
        f"- Processor: `{report['hardware']['processor']}`\n"
        f"- Logical CPUs: `{report['hardware']['logical_cpu_count']}`\n"
        f"- Python peak memory: `{report['run']['python_peak_memory_mb']} MB`\n"
    )


def _terms(text: str) -> list[str]:
    return [term.strip(".,!?;:()[]\"'").casefold() for term in text.split() if term.strip(".,!?;:()[]\"'")]


def _cosine(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
    return sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[min(round((len(ordered) - 1) * percentile), len(ordered) - 1)] if ordered else 0.0


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 4)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--select-existing", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())

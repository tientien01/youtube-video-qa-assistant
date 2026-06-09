import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from evaluation.metrics import average_metrics, compute_retrieval_metrics  # noqa: E402
from app.services.rag.local_store import VideoNotIndexedError  # noqa: E402
from app.services.rag.retrieval_service import RetrievalMode, retrieve_chunks  # noqa: E402


DEFAULT_MODES: list[RetrievalMode] = ["bm25", "embedding", "hybrid"]


def main() -> None:
    args = _parse_args()
    dataset = _load_dataset(args.dataset)
    modes = args.modes or DEFAULT_MODES

    print(f"Dataset: {args.dataset}")
    print(f"Items: {len(dataset)}")
    print(f"Top K: {args.top_k}")
    print("")

    for mode in modes:
        mode_result = _evaluate_mode(
            dataset=dataset,
            mode=mode,
            top_k=args.top_k,
        )
        _print_mode_result(mode, mode_result)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval modes on a small local dataset.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation") / "eval_dataset.example.json",
        help="Path to evaluation dataset JSON.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Number of chunks to retrieve per question.",
    )
    parser.add_argument(
        "--modes",
        nargs="*",
        choices=DEFAULT_MODES,
        help="Retrieval modes to evaluate.",
    )
    return parser.parse_args()


def _load_dataset(dataset_path: Path) -> list[dict[str, object]]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    return list(payload.get("items", []))


def _evaluate_mode(
    *,
    dataset: list[dict[str, object]],
    mode: RetrievalMode,
    top_k: int,
) -> dict[str, object]:
    metrics = []
    latencies = []
    errors = []

    for item in dataset:
        started_at = perf_counter()
        try:
            retrieved_chunks = retrieve_chunks(
                video_id=str(item["video_id"]),
                question=str(item["question"]),
                mode=mode,
                top_k=top_k,
            )
            retrieved_chunk_ids = [result.chunk.chunk_id for result in retrieved_chunks]
        except VideoNotIndexedError as error:
            retrieved_chunk_ids = []
            errors.append(f"{item['video_id']}: {error}")

        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        latencies.append(latency_ms)
        metrics.append(
            compute_retrieval_metrics(
                retrieved_chunk_ids=retrieved_chunk_ids,
                expected_chunk_ids=list(item["expected_chunk_ids"]),
            )
        )

    averaged_metrics = average_metrics(metrics)
    average_latency = round(sum(latencies) / max(len(latencies), 1), 3)

    return {
        "metrics": asdict(averaged_metrics),
        "average_latency_ms": average_latency,
        "errors": errors,
    }


def _print_mode_result(mode: RetrievalMode, result: dict[str, object]) -> None:
    metrics = result["metrics"]
    print(f"Mode: {mode}")
    print(f"  Precision@k: {metrics['precision_at_k']}")
    print(f"  Recall@k:    {metrics['recall_at_k']}")
    print(f"  MRR:         {metrics['mrr']}")
    print(f"  Latency:     {result['average_latency_ms']} ms")
    errors = result["errors"]
    if errors:
        print("  Errors:")
        for error in errors:
            print(f"    - {error}")
    print("")


if __name__ == "__main__":
    main()

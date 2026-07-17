import hashlib
import json
from pathlib import Path

from app.modules.evaluation.run import _fingerprint, _recommend, _validate_dataset


ROOT = Path(__file__).resolve().parents[2]


def test_committed_dataset_and_report_are_reviewed_and_fingerprinted() -> None:
    dataset_path = ROOT / "backend/evaluation/datasets/local-v1-v1.json"
    config_path = ROOT / "backend/evaluation/local-v1.yaml"
    report_path = ROOT / "backend/evaluation/reports/local-v1.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    _validate_dataset(dataset)
    assert report["dataset"]["reviewed_count"] == len(dataset["questions"])
    assert report["dataset"]["sha256"] == hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    assert report["config_sha256"] == _fingerprint(config)
    assert {item["retrieval"] for item in report["variants"]} == {"lexical", "dense", "rrf", "reranked"}
    assert {item["chunker"] for item in report["variants"]} == {"fixed_word", "hierarchical_sentence"}
    assert report["recommendation"]["variant_id"] == _recommend(
        report["variants"], config["quality_equivalence_margin"]
    )["variant_id"]

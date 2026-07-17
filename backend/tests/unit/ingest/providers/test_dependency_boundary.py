from pathlib import Path


def test_production_code_does_not_import_legacy_transcript_service() -> None:
    backend_root = Path(__file__).resolve().parents[4]
    legacy_import = "app.application.legacy.extraction.transcript_service"
    violations = []

    for path in (backend_root / "app").rglob("*.py"):
        if legacy_import in path.read_text(encoding="utf-8"):
            violations.append(path.relative_to(backend_root).as_posix())

    assert violations == []


def test_application_transcript_contract_has_no_provider_sdk_imports() -> None:
    backend_root = Path(__file__).resolve().parents[4]
    application_root = backend_root / "app" / "application" / "ingest"
    forbidden = ("youtube_transcript_api", "yt_dlp", "import requests")
    violations = []

    for path in application_root.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        if any(token in content for token in forbidden):
            violations.append(path.relative_to(backend_root).as_posix())

    assert violations == []

from pathlib import Path


def test_domain_and_application_layers_do_not_import_sqlalchemy() -> None:
    backend_root = Path(__file__).resolve().parents[3]
    protected_roots = [backend_root / "app" / "domain", backend_root / "app" / "application"]

    violations = []
    for protected_root in protected_roots:
        for path in protected_root.rglob("*.py"):
            if "sqlalchemy" in path.read_text(encoding="utf-8").lower():
                violations.append(path.relative_to(backend_root).as_posix())

    assert violations == []

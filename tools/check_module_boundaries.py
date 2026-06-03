#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUNDARIES = [
    {
        "name": "CELT",
        "paths": [ROOT / "src" / "opus" / "celt", ROOT / "tests"],
        "test_prefix": "celt_",
        "forbidden": [
            ("src.opus.silk", "SILK"),
            ("src.opus.hybrid", "Hybrid"),
        ],
    },
    {
        "name": "SILK",
        "paths": [ROOT / "src" / "opus" / "silk", ROOT / "tests"],
        "test_prefix": "silk_",
        "forbidden": [
            ("src.opus.celt", "CELT"),
            ("src.opus.hybrid", "Hybrid"),
        ],
    },
]


def uya_files(paths: list[Path], test_prefix: str) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".uya":
            files.append(path)
            continue
        if path.is_dir():
            for file_path in path.rglob("*.uya"):
                if file_path.parent == ROOT / "tests" and not file_path.name.startswith(test_prefix):
                    continue
                files.append(file_path)
    return sorted(files)


def main() -> int:
    violations: list[str] = []
    for boundary in BOUNDARIES:
        for path in uya_files(boundary["paths"], boundary["test_prefix"]):
            rel = path.relative_to(ROOT)
            for line_no, line in enumerate(path.read_text().splitlines(), start=1):
                stripped = line.strip()
                if not stripped.startswith("use "):
                    continue
                for import_prefix, label in boundary["forbidden"]:
                    if import_prefix in stripped:
                        violations.append(
                            f"{rel}:{line_no}: {boundary['name']} module imports {label}: {stripped}"
                        )

    if violations:
        for violation in violations:
            print(violation)
        return 1

    print("check_module_boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

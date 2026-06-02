#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELT_PATHS = [
    ROOT / "src" / "opus" / "celt",
    ROOT / "tests",
]


def uya_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".uya":
            files.append(path)
            continue
        if path.is_dir():
            for file_path in path.rglob("*.uya"):
                if file_path.parent == ROOT / "tests" and not file_path.name.startswith("celt_"):
                    continue
                files.append(file_path)
    return sorted(files)


def main() -> int:
    violations: list[str] = []
    for path in uya_files(CELT_PATHS):
        rel = path.relative_to(ROOT)
        for line_no, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith("use "):
                continue
            if "src.opus.silk" in stripped:
                violations.append(f"{rel}:{line_no}: CELT module imports SILK: {stripped}")

    if violations:
        for violation in violations:
            print(violation)
        return 1

    print("check_module_boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

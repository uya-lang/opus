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

HYBRID_STATE_TYPES = ("SilkDecoderState", "CeltDecoderState")
HYBRID_STRUCTS_WITHOUT_CODEC_HISTORY = (
    ROOT / "src" / "opus" / "hybrid" / "state.uya",
    ROOT / "src" / "opus" / "hybrid" / "decoder.uya",
)


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


def exported_struct_bodies(path: Path) -> dict[str, tuple[int, list[str]]]:
    bodies: dict[str, tuple[int, list[str]]] = {}
    current_name = ""
    current_start = 0
    current_lines: list[str] = []
    in_struct = False

    for line_no, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not in_struct and stripped.startswith("export struct ") and stripped.endswith("{"):
            current_name = stripped.removeprefix("export struct ").removesuffix("{").strip()
            current_start = line_no
            current_lines = []
            in_struct = True
            continue

        if in_struct:
            if stripped == "}":
                bodies[current_name] = (current_start, current_lines)
                current_name = ""
                current_start = 0
                current_lines = []
                in_struct = False
                continue
            current_lines.append(line)

    return bodies


def check_hybrid_glue_state_ownership(violations: list[str]) -> None:
    for path in HYBRID_STRUCTS_WITHOUT_CODEC_HISTORY:
        rel = path.relative_to(ROOT)
        for struct_name, (line_no, body_lines) in exported_struct_bodies(path).items():
            if struct_name not in ("HybridDecoderState", "HybridDecoderScratch"):
                continue
            body = "\n".join(body_lines)
            for state_type in HYBRID_STATE_TYPES:
                if state_type in body:
                    violations.append(
                        f"{rel}:{line_no}: {struct_name} must not embed {state_type}; "
                        "Hybrid glue should borrow codec history state instead"
                    )


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

    check_hybrid_glue_state_ownership(violations)

    if violations:
        for violation in violations:
            print(violation)
        return 1

    print("check_module_boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

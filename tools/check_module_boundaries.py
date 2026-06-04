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
API_PUBLIC_FORBIDDEN_STATE_TYPES = (
    "CeltDecoderState",
    "CeltMonoDecodeScratch",
    "CeltPlcScratch",
    "HybridDecoderScratch",
    "HybridDecoderState",
    "OpusDecoderHistory",
    "OpusDecoderScratch",
    "OpusDecoderState",
    "SilkDecoderState",
    "SilkStereoState",
)
API_PUBLIC_FILES = (ROOT / "src" / "opus" / "api",)
API_DECODER_FILE = ROOT / "src" / "opus" / "api" / "decoder.uya"
API_DECODER_INIT_FORBIDDEN_SCRATCH_CLEARS = (
    ("decoder.scratch.celt_decode", "CeltMonoDecodeScratch"),
    ("decoder.scratch.celt_plc", "CeltPlcScratch"),
    ("decoder.scratch.hybrid", "HybridDecoderScratch"),
)
API_FINAL_RESAMPLE_DECODE_FUNCTIONS = (
    "decoder_decode_empty_packet_i16",
    "decoder_decode_celt_parsed_i16",
    "decoder_decode_hybrid_parsed_i16",
)
REPACKETIZER_FILE = ROOT / "src" / "opus" / "packet" / "repacketizer.uya"
REPACKETIZER_FORBIDDEN_IMPORTS = (
    ("src.opus.api", "public decoder API"),
    ("src.opus.celt", "CELT decoder"),
    ("src.opus.silk", "SILK decoder"),
    ("src.opus.hybrid", "Hybrid decoder"),
    ("src.opus.dsp", "DSP/audio processing"),
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


def check_api_public_structs_do_not_embed_codec_state(violations: list[str]) -> None:
    for path in uya_files(list(API_PUBLIC_FILES), ""):
        rel = path.relative_to(ROOT)
        for struct_name, (line_no, body_lines) in exported_struct_bodies(path).items():
            body = "\n".join(body_lines)
            for state_type in API_PUBLIC_FORBIDDEN_STATE_TYPES:
                if state_type in body:
                    violations.append(
                        f"{rel}:{line_no}: public API struct {struct_name} must not expose {state_type}"
                    )


def function_body_lines(path: Path, function_name: str) -> list[tuple[int, str]]:
    lines = path.read_text().splitlines()
    body: list[tuple[int, str]] = []
    in_function = False
    depth = 0

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_function:
            if stripped.startswith(f"fn {function_name}("):
                in_function = True
                depth = line.count("{") - line.count("}")
            continue

        body.append((line_no, line))
        depth += line.count("{") - line.count("}")
        if depth == 0:
            break

    return body


def check_api_decoder_init_avoids_large_scratch_clears(violations: list[str]) -> None:
    rel = API_DECODER_FILE.relative_to(ROOT)
    for line_no, line in function_body_lines(API_DECODER_FILE, "decoder_init_state"):
        compact = "".join(line.split())
        for lhs, type_name in API_DECODER_INIT_FORBIDDEN_SCRATCH_CLEARS:
            if f"{lhs}={type_name}{{}};" in compact:
                violations.append(
                    f"{rel}:{line_no}: decoder_init_state must not clear large {type_name} scratch for single-stream init"
                )


def count_token_in_function(path: Path, function_name: str, token: str) -> int:
    return sum(line.count(token) for _, line in function_body_lines(path, function_name))


def check_api_decode_uses_single_final_resample(violations: list[str]) -> None:
    rel = API_DECODER_FILE.relative_to(ROOT)
    direct_resample_calls: int = count_token_in_function(API_DECODER_FILE, "decoder_resample_output_i16", "resampler_process_i16(")
    if direct_resample_calls != 1:
        violations.append(
            f"{rel}: decoder_resample_output_i16 must contain exactly one direct resampler_process_i16 call"
        )

    for function_name in API_FINAL_RESAMPLE_DECODE_FUNCTIONS:
        final_resample_calls: int = count_token_in_function(API_DECODER_FILE, function_name, "decoder_resample_output_i16(")
        direct_calls: int = count_token_in_function(API_DECODER_FILE, function_name, "resampler_process_i16(")
        if final_resample_calls != 1:
            violations.append(
                f"{rel}: {function_name} must route non-48k output through exactly one final resample helper"
            )
        if direct_calls != 0:
            violations.append(
                f"{rel}: {function_name} must not call resampler_process_i16 directly"
            )


def check_repacketizer_stays_packet_only(violations: list[str]) -> None:
    rel = REPACKETIZER_FILE.relative_to(ROOT)
    for line_no, line in enumerate(REPACKETIZER_FILE.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("use "):
            continue
        for import_prefix, label in REPACKETIZER_FORBIDDEN_IMPORTS:
            if import_prefix in stripped:
                violations.append(
                    f"{rel}:{line_no}: repacketizer must not import {label}: {stripped}"
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
    check_api_public_structs_do_not_embed_codec_state(violations)
    check_api_decoder_init_avoids_large_scratch_clears(violations)
    check_api_decode_uses_single_final_resample(violations)
    check_repacketizer_stays_packet_only(violations)

    if violations:
        for violation in violations:
            print(violation)
        return 1

    print("check_module_boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

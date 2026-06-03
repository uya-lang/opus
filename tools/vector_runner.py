#!/usr/bin/env python3
"""Manifest validation and PCM comparison for decoder vector corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


MANIFEST_FORMAT = "uopus.decoder-vectors.v1"
VALID_SAMPLE_RATES = {8000, 12000, 16000, 24000, 48000}
CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class ManifestError(Exception):
    """Raised when a vector manifest or corpus file is invalid."""


@dataclass(frozen=True)
class VectorCase:
    id: str
    sample_rate_hz: int
    channels: int
    frame_size: int
    decode_fec: bool
    packets: tuple[str, ...]
    reference_pcm: str
    reference_sha256: str
    max_abs_error: int = 0
    max_total_abs_error: int = 0
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PcmDiffStats:
    passed: bool
    sample_count: int
    mismatch_count: int
    max_abs_error: int
    total_abs_error: int
    first_diff_sample: int | None
    length_mismatch: bool = False
    reason: str = ""


@dataclass(frozen=True)
class DiffResult:
    case: VectorCase
    actual_pcm: Path
    stats: PcmDiffStats


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{name} must be an object")
    return value


def _require_bool(value: Any, name: str, default: bool | None = None) -> bool:
    if value is None and default is not None:
        return default
    if not isinstance(value, bool):
        raise ManifestError(f"{name} must be a boolean")
    return value


def _require_int(value: Any, name: str, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ManifestError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ManifestError(f"{name} must be >= {minimum}")
    return value


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{name} must be a non-empty string")
    return value


def _safe_relative_path(value: Any, name: str) -> str:
    raw = _require_str(value, name)
    if "\\" in raw:
        raise ManifestError(f"{name} must use forward slash separators")
    path = PurePosixPath(raw)
    if path.is_absolute():
        raise ManifestError(f"{name} must be relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ManifestError(f"{name} must not contain empty, '.', or '..' segments")
    return str(path)


def _resolve_corpus_path(corpus_root: Path, rel_path: str) -> Path:
    root = corpus_root.resolve()
    resolved = (root / rel_path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ManifestError(f"path escapes corpus root: {rel_path}")
    return resolved


def _parse_packets(value: Any, case_id: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ManifestError(f"case {case_id}: packets must be a non-empty list")
    return tuple(_safe_relative_path(item, f"case {case_id}: packets[]") for item in value)


def _parse_tags(value: Any, case_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ManifestError(f"case {case_id}: tags must be a list")
    tags: list[str] = []
    for item in value:
        tag = _require_str(item, f"case {case_id}: tags[]")
        if not CASE_ID_RE.match(tag):
            raise ManifestError(f"case {case_id}: invalid tag: {tag}")
        tags.append(tag)
    return tuple(tags)


def _parse_tolerance(case_obj: dict[str, Any], case_id: str) -> tuple[int, int]:
    tolerance = case_obj.get("tolerance")
    if tolerance is None:
        return 0, 0
    tol_obj = _require_object(tolerance, f"case {case_id}: tolerance")
    max_abs = _require_int(tol_obj.get("max_abs_error", 0), f"case {case_id}: tolerance.max_abs_error", 0)
    max_total = _require_int(
        tol_obj.get("max_total_abs_error", 0),
        f"case {case_id}: tolerance.max_total_abs_error",
        0,
    )
    return max_abs, max_total


def _parse_case(value: Any, seen_ids: set[str]) -> VectorCase:
    case_obj = _require_object(value, "case")
    case_id = _require_str(case_obj.get("id"), "case.id")
    if not CASE_ID_RE.match(case_id):
        raise ManifestError(f"invalid case id: {case_id}")
    if case_id in seen_ids:
        raise ManifestError(f"duplicate case id: {case_id}")
    seen_ids.add(case_id)

    sample_rate = _require_int(case_obj.get("sample_rate_hz"), f"case {case_id}: sample_rate_hz")
    if sample_rate not in VALID_SAMPLE_RATES:
        raise ManifestError(f"case {case_id}: unsupported sample_rate_hz: {sample_rate}")

    channels = _require_int(case_obj.get("channels"), f"case {case_id}: channels")
    if channels not in {1, 2}:
        raise ManifestError(f"case {case_id}: channels must be 1 or 2")

    frame_size = _require_int(case_obj.get("frame_size"), f"case {case_id}: frame_size", 1)
    decode_fec = _require_bool(case_obj.get("decode_fec"), f"case {case_id}: decode_fec", False)
    packets = _parse_packets(case_obj.get("packets"), case_id)
    reference_pcm = _safe_relative_path(case_obj.get("reference_pcm"), f"case {case_id}: reference_pcm")
    reference_sha256 = _require_str(case_obj.get("reference_sha256"), f"case {case_id}: reference_sha256").lower()
    if not SHA256_RE.match(reference_sha256):
        raise ManifestError(f"case {case_id}: reference_sha256 must be 64 hex characters")

    max_abs, max_total = _parse_tolerance(case_obj, case_id)
    tags = _parse_tags(case_obj.get("tags"), case_id)

    return VectorCase(
        id=case_id,
        sample_rate_hz=sample_rate,
        channels=channels,
        frame_size=frame_size,
        decode_fec=decode_fec,
        packets=packets,
        reference_pcm=reference_pcm,
        reference_sha256=reference_sha256,
        max_abs_error=max_abs,
        max_total_abs_error=max_total,
        tags=tags,
    )


def load_manifest(manifest_path: Path) -> list[VectorCase]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestError(f"cannot read manifest: {manifest_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON in manifest: {exc}") from exc

    manifest = _require_object(data, "manifest")
    if manifest.get("format") != MANIFEST_FORMAT:
        raise ManifestError(f"manifest format must be {MANIFEST_FORMAT}")
    cases_value = manifest.get("cases")
    if not isinstance(cases_value, list):
        raise ManifestError("manifest cases must be a list")

    seen_ids: set[str] = set()
    return [_parse_case(case_value, seen_ids) for case_value in cases_value]


def validate_manifest_files(cases: Iterable[VectorCase], corpus_root: Path) -> None:
    for case in cases:
        for packet_rel in case.packets:
            packet_path = _resolve_corpus_path(corpus_root, packet_rel)
            if not packet_path.is_file():
                raise ManifestError(f"case {case.id}: missing packet file: {packet_rel}")

        ref_path = _resolve_corpus_path(corpus_root, case.reference_pcm)
        if not ref_path.is_file():
            raise ManifestError(f"case {case.id}: missing reference PCM: {case.reference_pcm}")
        digest = hashlib.sha256(ref_path.read_bytes()).hexdigest()
        if digest != case.reference_sha256:
            raise ManifestError(
                f"case {case.id}: reference PCM sha256 mismatch: "
                f"expected {case.reference_sha256}, got {digest}"
            )


def _read_i16le(data: bytes, sample_index: int) -> int:
    return struct.unpack_from("<h", data, sample_index * 2)[0]


def compare_pcm_i16le(
    reference: bytes,
    actual: bytes,
    max_abs_error: int = 0,
    max_total_abs_error: int = 0,
) -> PcmDiffStats:
    if len(reference) % 2 != 0 or len(actual) % 2 != 0:
        return PcmDiffStats(
            passed=False,
            sample_count=min(len(reference), len(actual)) // 2,
            mismatch_count=0,
            max_abs_error=0,
            total_abs_error=0,
            first_diff_sample=None,
            length_mismatch=True,
            reason="PCM byte length must be even for signed 16-bit little-endian samples",
        )

    reference_samples = len(reference) // 2
    actual_samples = len(actual) // 2
    common_samples = min(reference_samples, actual_samples)
    length_mismatch = reference_samples != actual_samples

    mismatch_count = abs(reference_samples - actual_samples)
    max_abs = 0
    total_abs = 0
    first_different: int | None = None
    first_over_limit: int | None = None

    for i in range(common_samples):
        delta = abs(_read_i16le(reference, i) - _read_i16le(actual, i))
        if delta != 0:
            mismatch_count += 1
            if first_different is None:
                first_different = i
        if delta > max_abs:
            max_abs = delta
        total_abs += delta
        if first_over_limit is None and delta > max_abs_error:
            first_over_limit = i

    first_diff = first_over_limit
    if first_diff is None and total_abs > max_total_abs_error:
        first_diff = first_different
    if first_diff is None and length_mismatch:
        first_diff = common_samples

    passed = (
        not length_mismatch
        and max_abs <= max_abs_error
        and total_abs <= max_total_abs_error
    )
    reason = ""
    if length_mismatch:
        reason = f"sample length mismatch: expected {reference_samples}, got {actual_samples}"
    elif max_abs > max_abs_error:
        reason = f"max abs error {max_abs} exceeds {max_abs_error}"
    elif total_abs > max_total_abs_error:
        reason = f"total abs error {total_abs} exceeds {max_total_abs_error}"

    return PcmDiffStats(
        passed=passed,
        sample_count=reference_samples,
        mismatch_count=mismatch_count,
        max_abs_error=max_abs,
        total_abs_error=total_abs,
        first_diff_sample=first_diff,
        length_mismatch=length_mismatch,
        reason=reason,
    )


def run_diff(manifest_path: Path, actual_dir: Path, corpus_root: Path | None = None) -> list[DiffResult]:
    cases = load_manifest(manifest_path)
    root = corpus_root if corpus_root is not None else manifest_path.parent
    validate_manifest_files(cases, root)

    results: list[DiffResult] = []
    for case in cases:
        ref_path = _resolve_corpus_path(root, case.reference_pcm)
        actual_path = actual_dir / f"{case.id}.s16le"
        if not actual_path.is_file():
            raise ManifestError(f"case {case.id}: missing actual PCM: {actual_path}")
        stats = compare_pcm_i16le(
            ref_path.read_bytes(),
            actual_path.read_bytes(),
            max_abs_error=case.max_abs_error,
            max_total_abs_error=case.max_total_abs_error,
        )
        results.append(DiffResult(case=case, actual_pcm=actual_path, stats=stats))
    return results


def _print_case_list(cases: Iterable[VectorCase]) -> None:
    for case in cases:
        packets = ",".join(case.packets)
        print(
            "\t".join(
                [
                    case.id,
                    str(case.sample_rate_hz),
                    str(case.channels),
                    str(case.frame_size),
                    "1" if case.decode_fec else "0",
                    packets,
                ]
            )
        )


def _cmd_validate(args: argparse.Namespace) -> int:
    cases = load_manifest(args.manifest)
    validate_manifest_files(cases, args.corpus_root or args.manifest.parent)
    print(f"ok: {args.manifest} has {len(cases)} decoder vector case(s)")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    cases = load_manifest(args.manifest)
    _print_case_list(cases)
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    results = run_diff(args.manifest, args.actual_dir, args.corpus_root or args.manifest.parent)
    failed = 0
    for result in results:
        stats = result.stats
        status = "ok" if stats.passed else "FAIL"
        detail = (
            f"samples={stats.sample_count} mismatches={stats.mismatch_count} "
            f"max_abs={stats.max_abs_error} total_abs={stats.total_abs_error}"
        )
        if stats.reason:
            detail = f"{detail} reason={stats.reason}"
        print(f"{status}: {result.case.id}: {detail}")
        if not stats.passed:
            failed += 1
    if failed:
        print(f"error: {failed} decoder vector case(s) failed", file=sys.stderr)
        return 1
    print(f"ok: {len(results)} decoder vector case(s) matched reference PCM")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate manifest, files, and reference hashes")
    validate.add_argument("manifest", type=Path)
    validate.add_argument("--corpus-root", type=Path)
    validate.set_defaults(func=_cmd_validate)

    list_cmd = subparsers.add_parser("list", help="print decoder jobs as tab-separated rows")
    list_cmd.add_argument("manifest", type=Path)
    list_cmd.set_defaults(func=_cmd_list)

    diff = subparsers.add_parser("diff", help="compare actual PCM files named <case id>.s16le")
    diff.add_argument("manifest", type=Path)
    diff.add_argument("--actual-dir", type=Path, required=True)
    diff.add_argument("--corpus-root", type=Path)
    diff.set_defaults(func=_cmd_diff)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

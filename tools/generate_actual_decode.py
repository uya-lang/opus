#!/usr/bin/env python3
"""Generate actual decoder PCM files for manifest cases."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from tools.opus_demo_bitstream import MAX_PACKET_BYTES
    from tools.vector_runner import (
        ManifestError,
        VectorCase,
        _resolve_corpus_path,
        load_manifest,
        validate_manifest_files,
    )
except ModuleNotFoundError:  # pragma: no cover - supports `python3 tools/generate_actual_decode.py`
    from opus_demo_bitstream import MAX_PACKET_BYTES
    from vector_runner import ManifestError, VectorCase, _resolve_corpus_path, load_manifest, validate_manifest_files


class GenerationError(Exception):
    """Raised when actual PCM generation cannot complete."""


def _write_packet_record(output, payload: bytes) -> None:
    output.write(len(payload).to_bytes(4, "big"))
    output.write((0).to_bytes(4, "big"))
    output.write(payload)


def _synthesize_packet_bitstream(case: VectorCase, corpus_root: Path, output_path: Path) -> Path:
    with output_path.open("wb") as output:
        for packet_rel in case.packets:
            packet_path = _resolve_corpus_path(corpus_root, packet_rel)
            payload = packet_path.read_bytes()
            if not payload:
                raise GenerationError(f"case {case.id}: packet source cannot be empty: {packet_rel}")
            if len(payload) > MAX_PACKET_BYTES:
                raise GenerationError(
                    f"case {case.id}: packet source {packet_rel} has {len(payload)} byte(s), "
                    f"exceeds max {MAX_PACKET_BYTES}"
                )
            _write_packet_record(output, payload)
    return output_path


def _input_bitstream_for_case(case: VectorCase, corpus_root: Path, scratch_dir: Path) -> Path:
    if case.bitstream is not None:
        return _resolve_corpus_path(corpus_root, case.bitstream)
    return _synthesize_packet_bitstream(case, corpus_root, scratch_dir / f"{case.id}.bit")


def _run_decoder(decoder: Path, case: VectorCase, input_bitstream: Path, output_pcm: Path) -> None:
    if output_pcm.exists():
        output_pcm.unlink()

    command = [
        str(decoder),
        str(case.sample_rate_hz),
        str(case.channels),
        "1" if case.decode_fec else "0",
        str(input_bitstream),
        str(output_pcm),
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise GenerationError(f"actual decoder command failed for {case.id}: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        if detail:
            raise GenerationError(
                f"actual decode failed for {case.id}: exit {completed.returncode}: {detail}"
            )
        raise GenerationError(f"actual decode failed for {case.id}: exit {completed.returncode}")

    if not output_pcm.is_file():
        raise GenerationError(f"actual decode failed for {case.id}: missing output {output_pcm}")


def generate_actual_pcm(
    manifest_path: Path,
    actual_dir: Path,
    decoder: Path,
    corpus_root: Path | None = None,
    include_disabled: bool = False,
) -> list[Path]:
    root = corpus_root if corpus_root is not None else manifest_path.parent
    cases = load_manifest(manifest_path)
    validate_manifest_files(cases, root)
    selected = [case for case in cases if include_disabled or case.enabled]

    actual_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="uopus-decode-inputs-") as tmp:
        scratch_dir = Path(tmp)
        for case in selected:
            input_bitstream = _input_bitstream_for_case(case, root, scratch_dir)
            output_pcm = actual_dir / f"{case.id}.s16le"
            _run_decoder(decoder, case, input_bitstream, output_pcm)
            outputs.append(output_pcm)
            print(f"generated: {case.id}: {output_pcm}")
    return outputs


def _cmd_generate(args: argparse.Namespace) -> int:
    outputs = generate_actual_pcm(
        args.manifest,
        args.actual_dir,
        args.decoder,
        corpus_root=args.corpus_root,
        include_disabled=args.all,
    )
    print(f"ok: generated {len(outputs)} actual decoder PCM file(s) in {args.actual_dir}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--actual-dir", type=Path, required=True)
    parser.add_argument("--decoder", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path)
    parser.add_argument("--all", action="store_true", help="generate disabled cases too")
    parser.set_defaults(func=_cmd_generate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (GenerationError, ManifestError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

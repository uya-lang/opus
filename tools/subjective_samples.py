#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import wave
from pathlib import Path, PurePosixPath
from typing import Iterable

MANIFEST_FORMAT = "uopus.subjective-samples.v1"
SUPPORTED_SAMPLE_RATES = {8000, 12000, 16000, 24000, 48000}
GENERATOR_CHANNELS = {
    "voice_pulses": 1,
    "stereo_music": 2,
    "transient_stereo": 2,
    "lowband_sweep": 1,
}


class SubjectiveSampleError(Exception):
    """Raised when a subjective sample manifest or case is invalid."""


def _read_manifest(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except OSError as exc:
        raise SubjectiveSampleError(f"cannot read manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SubjectiveSampleError(f"invalid JSON manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise SubjectiveSampleError("manifest must be a JSON object")
    return manifest


def _validate_output_wav(rel_path: str) -> None:
    path = PurePosixPath(rel_path)
    if path.is_absolute() or ".." in path.parts:
        raise SubjectiveSampleError(f"output path escapes sample output root: {rel_path}")
    if path.suffix != ".wav":
        raise SubjectiveSampleError(f"output_wav must end with .wav: {rel_path}")


def _require_str(case: dict, field: str) -> str:
    value = case.get(field)
    if not isinstance(value, str) or not value:
        raise SubjectiveSampleError(f"case field must be a non-empty string: {field}")
    return value


def _require_int(case: dict, field: str) -> int:
    value = case.get(field)
    if not isinstance(value, int):
        raise SubjectiveSampleError(f"case field must be an integer: {field}")
    return value


def load_manifest(path: Path) -> list[dict]:
    manifest = _read_manifest(path)
    if manifest.get("format") != MANIFEST_FORMAT:
        raise SubjectiveSampleError(f"unsupported manifest format: {manifest.get('format')}")
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise SubjectiveSampleError("manifest cases must be a list")

    seen_ids: set[str] = set()
    seen_outputs: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise SubjectiveSampleError("each case must be a JSON object")
        case_id = _require_str(case, "id")
        if not all(ch.islower() or ch.isdigit() or ch == "-" for ch in case_id):
            raise SubjectiveSampleError(f"case id must be lowercase kebab-case: {case_id}")
        if case_id in seen_ids:
            raise SubjectiveSampleError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)

        _ = _require_str(case, "title")
        _ = _require_str(case, "category")
        sample_rate_hz = _require_int(case, "sample_rate_hz")
        channels = _require_int(case, "channels")
        duration_ms = _require_int(case, "duration_ms")
        generator = _require_str(case, "generator")
        output_wav = _require_str(case, "output_wav")

        if sample_rate_hz not in SUPPORTED_SAMPLE_RATES:
            raise SubjectiveSampleError(f"unsupported sample rate for {case_id}: {sample_rate_hz}")
        if channels not in (1, 2):
            raise SubjectiveSampleError(f"unsupported channel count for {case_id}: {channels}")
        if duration_ms <= 0 or duration_ms > 10000:
            raise SubjectiveSampleError(f"duration_ms out of range for {case_id}: {duration_ms}")
        if (sample_rate_hz * duration_ms) % 1000 != 0:
            raise SubjectiveSampleError(f"duration does not produce an integer frame count for {case_id}")
        expected_channels = GENERATOR_CHANNELS.get(generator)
        if expected_channels is None:
            raise SubjectiveSampleError(f"unknown generator for {case_id}: {generator}")
        if channels != expected_channels:
            raise SubjectiveSampleError(f"generator {generator} requires {expected_channels} channel(s)")
        _validate_output_wav(output_wav)
        if output_wav in seen_outputs:
            raise SubjectiveSampleError(f"duplicate output_wav: {output_wav}")
        seen_outputs.add(output_wav)

    return cases


def _clamp_i16(value: float) -> int:
    if value > 1.0:
        value = 1.0
    if value < -1.0:
        value = -1.0
    return int(round(value * 32767.0))


def _noise(seed: int) -> tuple[int, float]:
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return seed, ((seed / 1073741824.0) - 1.0)


def _synth_voice_pulses(sample_rate_hz: int, frames: int) -> list[tuple[float, ...]]:
    samples: list[tuple[float, ...]] = []
    seed = 1
    for frame in range(frames):
        t = frame / sample_rate_hz
        syllable = (t * 4.0) % 1.0
        envelope = max(0.0, math.sin(math.pi * syllable))
        f0 = 118.0 + 18.0 * math.sin(2.0 * math.pi * 1.7 * t)
        voiced = (
            math.sin(2.0 * math.pi * f0 * t)
            + 0.35 * math.sin(2.0 * math.pi * f0 * 2.0 * t)
            + 0.16 * math.sin(2.0 * math.pi * f0 * 3.0 * t)
        )
        seed, noisy = _noise(seed)
        fricative = 0.10 * noisy if 0.55 <= syllable <= 0.78 else 0.0
        samples.append((0.38 * envelope * voiced + fricative,))
    return samples


def _synth_stereo_music(sample_rate_hz: int, frames: int) -> list[tuple[float, ...]]:
    notes = [261.63, 329.63, 392.00, 523.25, 440.00, 349.23, 392.00, 293.66]
    samples: list[tuple[float, ...]] = []
    for frame in range(frames):
        t = frame / sample_rate_hz
        note = notes[int(t / 0.375) % len(notes)]
        local = (t % 0.375) / 0.375
        envelope = min(1.0, local * 8.0) * max(0.35, 1.0 - local * 0.35)
        bass = math.sin(2.0 * math.pi * (note / 2.0) * t)
        lead = math.sin(2.0 * math.pi * note * t)
        side = math.sin(2.0 * math.pi * (note * 1.5) * t + 0.7)
        left = envelope * (0.30 * bass + 0.24 * lead + 0.15 * side)
        right = envelope * (0.30 * bass + 0.20 * lead - 0.18 * side)
        samples.append((left, right))
    return samples


def _synth_transient_stereo(sample_rate_hz: int, frames: int) -> list[tuple[float, ...]]:
    samples: list[tuple[float, ...]] = []
    seed = 7
    for frame in range(frames):
        t = frame / sample_rate_hz
        beat = (t * 5.0) % 1.0
        burst = math.exp(-beat * 38.0) if beat < 0.22 else 0.0
        seed, noisy = _noise(seed)
        tone = math.sin(2.0 * math.pi * 180.0 * t) * math.exp(-beat * 12.0)
        left = 0.55 * burst * noisy + 0.20 * tone
        right = -0.48 * burst * noisy + 0.18 * tone
        samples.append((left, right))
    return samples


def _synth_lowband_sweep(sample_rate_hz: int, frames: int) -> list[tuple[float, ...]]:
    samples: list[tuple[float, ...]] = []
    phase = 0.0
    for frame in range(frames):
        position = frame / max(1, frames - 1)
        freq = 180.0 + 1250.0 * position * position
        phase += 2.0 * math.pi * freq / sample_rate_hz
        envelope = 0.55 + 0.35 * math.sin(math.pi * position)
        samples.append((0.48 * envelope * math.sin(phase),))
    return samples


def _synthesize_case(case: dict) -> list[tuple[float, ...]]:
    sample_rate_hz = int(case["sample_rate_hz"])
    frames = sample_rate_hz * int(case["duration_ms"]) // 1000
    generator = case["generator"]
    if generator == "voice_pulses":
        return _synth_voice_pulses(sample_rate_hz, frames)
    if generator == "stereo_music":
        return _synth_stereo_music(sample_rate_hz, frames)
    if generator == "transient_stereo":
        return _synth_transient_stereo(sample_rate_hz, frames)
    if generator == "lowband_sweep":
        return _synth_lowband_sweep(sample_rate_hz, frames)
    raise SubjectiveSampleError(f"unknown generator: {generator}")


def generate_samples(cases: Iterable[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        output_path = output_dir / case["output_wav"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        samples = _synthesize_case(case)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(int(case["channels"]))
            wav.setsampwidth(2)
            wav.setframerate(int(case["sample_rate_hz"]))
            payload = bytearray()
            for frame in samples:
                for value in frame:
                    payload.extend(struct.pack("<h", _clamp_i16(value)))
            wav.writeframes(bytes(payload))
        print(f"generated: {case['id']} -> {output_path}")


def command_validate(args: argparse.Namespace) -> int:
    cases = load_manifest(args.manifest)
    print(f"ok: {args.manifest} has {len(cases)} subjective sample case(s)")
    return 0


def command_list(args: argparse.Namespace) -> int:
    cases = load_manifest(args.manifest)
    for case in cases:
        print(f"{case['id']}: {case['sample_rate_hz']} Hz, {case['channels']} ch, {case['duration_ms']} ms")
    return 0


def command_generate(args: argparse.Namespace) -> int:
    cases = load_manifest(args.manifest)
    generate_samples(cases, args.output_dir)
    print(f"ok: generated {len(cases)} subjective sample file(s)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate and generate subjective listening samples.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("manifest", type=Path)
    validate.set_defaults(func=command_validate)

    list_cmd = subparsers.add_parser("list")
    list_cmd.add_argument("manifest", type=Path)
    list_cmd.set_defaults(func=command_list)

    generate = subparsers.add_parser("generate")
    generate.add_argument("manifest", type=Path)
    generate.add_argument("--output-dir", type=Path, default=Path("build/subjective-samples"))
    generate.set_defaults(func=command_generate)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SubjectiveSampleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

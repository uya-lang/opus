#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.vector_runner import (  # noqa: E402
    ManifestError,
    compare_pcm_i16le,
    load_manifest,
    run_diff,
    validate_manifest_files,
)


def pcm_bytes(samples: list[int]) -> bytes:
    return b"".join(struct.pack("<h", sample) for sample in samples)


class VectorRunnerTests(unittest.TestCase):
    def write_manifest(self, root: Path, data: dict) -> Path:
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return manifest

    def minimal_manifest(self, root: Path, reference: bytes) -> Path:
        (root / "packets").mkdir()
        (root / "pcm").mkdir()
        (root / "packets" / "silence.opus").write_bytes(bytes([0x80, 0x00]))
        (root / "pcm" / "silence.s16le").write_bytes(reference)
        return self.write_manifest(
            root,
            {
                "format": "uopus.decoder-vectors.v1",
                "cases": [
                    {
                        "id": "silence-celt-2p5ms",
                        "sample_rate_hz": 48000,
                        "channels": 1,
                        "frame_size": 120,
                        "decode_fec": False,
                        "packets": ["packets/silence.opus"],
                        "reference_pcm": "pcm/silence.s16le",
                        "reference_sha256": hashlib.sha256(reference).hexdigest(),
                    }
                ],
            },
        )

    def test_load_manifest_accepts_minimal_decoder_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.minimal_manifest(Path(tmp), pcm_bytes([0, 1, -1]))

            cases = load_manifest(manifest)

            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].id, "silence-celt-2p5ms")
            self.assertEqual(cases[0].sample_rate_hz, 48000)
            self.assertEqual(cases[0].channels, 1)
            self.assertEqual(cases[0].frame_size, 120)
            self.assertEqual(cases[0].packets, ("packets/silence.opus",))

    def test_manifest_rejects_unsafe_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.write_manifest(
                root,
                {
                    "format": "uopus.decoder-vectors.v1",
                    "cases": [
                        {
                            "id": "bad-path",
                            "sample_rate_hz": 48000,
                            "channels": 1,
                            "frame_size": 120,
                            "packets": ["../escape.opus"],
                            "reference_pcm": "pcm/out.s16le",
                            "reference_sha256": "0" * 64,
                        }
                    ],
                },
            )

            with self.assertRaises(ManifestError):
                load_manifest(manifest)

    def test_validate_manifest_files_checks_reference_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.minimal_manifest(root, pcm_bytes([4, 5, 6]))
            cases = load_manifest(manifest)
            validate_manifest_files(cases, root)

            (root / "pcm" / "silence.s16le").write_bytes(pcm_bytes([4, 5, 7]))
            with self.assertRaises(ManifestError):
                validate_manifest_files(cases, root)

    def test_compare_pcm_reports_exact_and_tolerant_diffs(self) -> None:
        exact = compare_pcm_i16le(pcm_bytes([10, -20, 30]), pcm_bytes([10, -20, 30]))
        self.assertTrue(exact.passed)
        self.assertEqual(exact.mismatch_count, 0)

        tolerant = compare_pcm_i16le(
            pcm_bytes([10, -20, 30]),
            pcm_bytes([11, -18, 29]),
            max_abs_error=2,
            max_total_abs_error=4,
        )
        self.assertTrue(tolerant.passed)
        self.assertEqual(tolerant.max_abs_error, 2)
        self.assertEqual(tolerant.total_abs_error, 4)

        mismatch = compare_pcm_i16le(
            pcm_bytes([10, -20, 30]),
            pcm_bytes([11, -18, 29]),
            max_abs_error=1,
            max_total_abs_error=4,
        )
        self.assertFalse(mismatch.passed)
        self.assertEqual(mismatch.first_diff_sample, 1)

    def test_run_diff_compares_actual_pcm_by_case_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = pcm_bytes([0, 100, -100])
            manifest = self.minimal_manifest(root, reference)
            actual_dir = root / "actual"
            actual_dir.mkdir()
            (actual_dir / "silence-celt-2p5ms.s16le").write_bytes(reference)

            results = run_diff(manifest, actual_dir)

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].stats.passed)


if __name__ == "__main__":
    unittest.main()

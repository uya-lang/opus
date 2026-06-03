#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "diff_decode.sh"


def pcm_bytes(samples: list[int]) -> bytes:
    return b"".join(struct.pack("<h", sample) for sample in samples)


def packet_record(payload: bytes, final_range: int) -> bytes:
    return len(payload).to_bytes(4, "big") + final_range.to_bytes(4, "big") + payload


class DiffDecodeScriptTests(unittest.TestCase):
    def write_manifest(self, root: Path, cases: list[dict]) -> None:
        (root / "manifest.json").write_text(
            json.dumps({"format": "uopus.decoder-vectors.v1", "cases": cases}, indent=2),
            encoding="utf-8",
        )

    def run_script(self, corpus: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        script_env = os.environ.copy()
        if env:
            script_env.update(env)
        return subprocess.run(
            [str(SCRIPT), str(corpus)],
            cwd=ROOT,
            env=script_env,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_single_case_corpus(self, root: Path, reference: bytes) -> dict:
        (root / "packets").mkdir()
        (root / "pcm").mkdir()
        (root / "packets" / "packet.opus").write_bytes(bytes([0x80, 0x00]))
        (root / "pcm" / "packet.s16le").write_bytes(reference)
        case = {
            "id": "one-packet",
            "sample_rate_hz": 48000,
            "channels": 1,
            "frame_size": 120,
            "decode_fec": False,
            "packets": ["packets/packet.opus"],
            "reference_pcm": "pcm/packet.s16le",
            "reference_sha256": hashlib.sha256(reference).hexdigest(),
        }
        self.write_manifest(root, [case])
        return case

    def create_disabled_case_corpus(self, root: Path, reference: bytes) -> None:
        (root / "rfc8251").mkdir()
        (root / "rfc8251" / "testvector01.bit").write_bytes(packet_record(bytes([0x01, 0x02]), 0x12345678))
        (root / "rfc8251" / "testvector01.dec").write_bytes(reference)
        self.write_manifest(
            root,
            [
                {
                    "id": "rfc8251-01-48000-mono",
                    "enabled": False,
                    "blocked_by": "actual decode path is not wired yet",
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "bitstream": "rfc8251/testvector01.bit",
                    "references": [
                        {
                            "path": "rfc8251/testvector01.dec",
                            "sha256": hashlib.sha256(reference).hexdigest(),
                        }
                    ],
                }
            ],
        )

    def test_missing_manifest_reports_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_script(Path(tmp))

            self.assertEqual(result.returncode, 2)
            self.assertIn("missing manifest", result.stderr)

    def test_empty_corpus_is_successful_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            self.write_manifest(corpus, [])

            result = self.run_script(corpus)

            self.assertEqual(result.returncode, 0)
            self.assertIn("has 0 decoder vector case(s)", result.stdout)
            self.assertIn("empty decoder vector corpus", result.stdout)

    def test_disabled_corpus_is_successful_noop_until_decode_path_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            self.create_disabled_case_corpus(corpus, pcm_bytes([0, 1, -1]))

            result = self.run_script(corpus)

            self.assertEqual(result.returncode, 0)
            self.assertIn("has 1 decoder vector case(s), 0 enabled", result.stdout)
            self.assertIn("empty decoder vector corpus", result.stdout)

    def test_nonempty_corpus_requires_actual_pcm_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            self.create_single_case_corpus(corpus, pcm_bytes([0, 1, -1]))

            result = self.run_script(corpus)

            self.assertEqual(result.returncode, 2)
            self.assertIn("requires UOPUS_DIFF_ACTUAL_DIR", result.stderr)

    def test_nonempty_corpus_can_compare_pregenerated_actual_pcm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp) / "corpus"
            actual = Path(tmp) / "actual"
            corpus.mkdir()
            actual.mkdir()
            reference = pcm_bytes([0, 1, -1])
            self.create_single_case_corpus(corpus, reference)
            (actual / "one-packet.s16le").write_bytes(reference)

            result = self.run_script(corpus, {"UOPUS_DIFF_ACTUAL_DIR": str(actual)})

            self.assertEqual(result.returncode, 0)
            self.assertIn("one-packet", result.stdout)
            self.assertIn("matched reference PCM", result.stdout)


if __name__ == "__main__":
    unittest.main()

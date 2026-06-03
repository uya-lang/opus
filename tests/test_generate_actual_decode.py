#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "generate_actual_decode.py"


def pcm_bytes(samples: list[int]) -> bytes:
    return b"".join(struct.pack("<h", sample) for sample in samples)


def packet_record(payload: bytes, final_range: int) -> bytes:
    return len(payload).to_bytes(4, "big") + final_range.to_bytes(4, "big") + payload


class GenerateActualDecodeTests(unittest.TestCase):
    def write_manifest(self, root: Path, cases: list[dict]) -> Path:
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"format": "uopus.decoder-vectors.v1", "cases": cases}, indent=2), encoding="utf-8")
        return manifest

    def write_fake_decoder(self, root: Path, body: str | None = None) -> Path:
        script = root / "fake_decoder.py"
        if body is None:
            body = """
import pathlib
import sys

sample_rate, channels, decode_fec, input_path, output_path = sys.argv[1:6]
payload = pathlib.Path(input_path).read_bytes()
pathlib.Path(output_path).write_bytes(
    f"{sample_rate}:{channels}:{decode_fec}\\n".encode("ascii") + payload
)
"""
        script.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
        script.chmod(0o755)
        return script

    def run_generator(
        self,
        manifest: Path,
        actual_dir: Path,
        decoder: Path,
        *extra_args: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(manifest),
                "--actual-dir",
                str(actual_dir),
                "--decoder",
                str(decoder),
                *extra_args,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_generates_actual_pcm_for_bitstream_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual_dir = root / "actual"
            (root / "vectors").mkdir()
            bitstream = packet_record(b"\x80\x01", 0x12345678)
            (root / "vectors" / "case.bit").write_bytes(bitstream)
            reference = pcm_bytes([1, 2])
            (root / "vectors" / "case.dec").write_bytes(reference)
            manifest = self.write_manifest(
                root,
                [
                    {
                        "id": "bitstream-case",
                        "sample_rate_hz": 48000,
                        "channels": 2,
                        "decode_fec": False,
                        "bitstream": "vectors/case.bit",
                        "reference_pcm": "vectors/case.dec",
                        "reference_sha256": hashlib.sha256(reference).hexdigest(),
                    }
                ],
            )
            decoder = self.write_fake_decoder(root)

            completed = self.run_generator(manifest, actual_dir, decoder)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((actual_dir / "bitstream-case.s16le").read_bytes(), b"48000:2:0\n" + bitstream)
            self.assertIn("generated: bitstream-case", completed.stdout)

    def test_synthesizes_opus_demo_bitstream_for_packet_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual_dir = root / "actual"
            (root / "packets").mkdir()
            (root / "pcm").mkdir()
            (root / "packets" / "a.opus").write_bytes(b"\x80\x01")
            (root / "packets" / "b.opus").write_bytes(b"\xff")
            reference = pcm_bytes([3, 4])
            (root / "pcm" / "case.s16le").write_bytes(reference)
            manifest = self.write_manifest(
                root,
                [
                    {
                        "id": "packet-case",
                        "sample_rate_hz": 16000,
                        "channels": 1,
                        "frame_size": 320,
                        "packets": ["packets/a.opus", "packets/b.opus"],
                        "reference_pcm": "pcm/case.s16le",
                        "reference_sha256": hashlib.sha256(reference).hexdigest(),
                    }
                ],
            )
            decoder = self.write_fake_decoder(root)
            expected_input = packet_record(b"\x80\x01", 0) + packet_record(b"\xff", 0)

            completed = self.run_generator(manifest, actual_dir, decoder)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((actual_dir / "packet-case.s16le").read_bytes(), b"16000:1:0\n" + expected_input)

    def test_skips_disabled_cases_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual_dir = root / "actual"
            (root / "vectors").mkdir()
            (root / "vectors" / "case.bit").write_bytes(packet_record(b"\x80", 1))
            reference = pcm_bytes([5])
            (root / "vectors" / "case.dec").write_bytes(reference)
            manifest = self.write_manifest(
                root,
                [
                    {
                        "id": "disabled-case",
                        "enabled": False,
                        "blocked_by": "not yet enabled",
                        "sample_rate_hz": 48000,
                        "channels": 1,
                        "bitstream": "vectors/case.bit",
                        "references": [
                            {
                                "path": "vectors/case.dec",
                                "sha256": hashlib.sha256(reference).hexdigest(),
                            }
                        ],
                    }
                ],
            )
            decoder = self.write_fake_decoder(root)

            completed = self.run_generator(manifest, actual_dir, decoder)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse((actual_dir / "disabled-case.s16le").exists())
            self.assertIn("generated 0 actual decoder PCM file(s)", completed.stdout)

    def test_reports_decoder_command_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual_dir = root / "actual"
            (root / "vectors").mkdir()
            (root / "vectors" / "case.bit").write_bytes(packet_record(b"\x80", 1))
            reference = pcm_bytes([6])
            (root / "vectors" / "case.dec").write_bytes(reference)
            manifest = self.write_manifest(
                root,
                [
                    {
                        "id": "fail-case",
                        "sample_rate_hz": 48000,
                        "channels": 1,
                        "bitstream": "vectors/case.bit",
                        "reference_pcm": "vectors/case.dec",
                        "reference_sha256": hashlib.sha256(reference).hexdigest(),
                    }
                ],
            )
            decoder = self.write_fake_decoder(root, "import sys\nsys.exit(7)\n")

            completed = self.run_generator(manifest, actual_dir, decoder)

            self.assertEqual(completed.returncode, 2)
            self.assertIn("actual decode failed for fail-case", completed.stderr)


if __name__ == "__main__":
    unittest.main()

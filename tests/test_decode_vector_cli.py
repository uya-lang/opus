#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "build" / "uopus-decode-vector"


def packet_record(payload: bytes, final_range: int = 0) -> bytes:
    return len(payload).to_bytes(4, "big") + final_range.to_bytes(4, "big") + payload


def api_smoke_packet() -> bytes:
    packet = bytearray(65)
    packet[0] = 128
    for i in range(1, 65):
        packet[i] = (i * 23 + 5) & 0xFF
    return bytes(packet)


class DecodeVectorCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        completed = subprocess.run(
            ["make", "decode-vector"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout + completed.stderr)

    def test_decodes_opus_demo_bitstream_to_s16le(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.bit"
            output_path = root / "out.s16le"
            input_path.write_bytes(packet_record(api_smoke_packet(), 0x12345678))

            completed = subprocess.run(
                [str(BIN), "48000", "1", "0", str(input_path), str(output_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            pcm = output_path.read_bytes()
            self.assertEqual(len(pcm), 120 * 2)

    def test_rejects_truncated_opus_demo_bitstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "bad.bit"
            output_path = root / "out.s16le"
            input_path.write_bytes(b"\x00\x00")

            completed = subprocess.run(
                [str(BIN), "48000", "1", "0", str(input_path), str(output_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output_path.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()

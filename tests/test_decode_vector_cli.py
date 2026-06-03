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


def first_packet_records(path: Path, count: int) -> bytes:
    data = path.read_bytes()
    pos = 0
    records = bytearray()
    for _ in range(count):
        if pos + 8 > len(data):
            raise AssertionError("truncated opus_demo packet header")
        size = int.from_bytes(data[pos:pos + 4], "big")
        final_range = data[pos + 4:pos + 8]
        pos += 8
        payload = data[pos:pos + size]
        if len(payload) != size:
            raise AssertionError("truncated opus_demo packet payload")
        pos += size
        records += size.to_bytes(4, "big") + final_range + payload
    return bytes(records)


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

    def test_decodes_rfc8251_testvector01_first_two_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "testvector01-first-two.bit"
            output_path = root / "out.s16le"
            input_path.write_bytes(first_packet_records(ROOT / "tests/vectors/rfc8251/testvector01.bit", 2))

            completed = subprocess.run(
                [str(BIN), "8000", "1", "0", str(input_path), str(output_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(len(output_path.read_bytes()), 2560)

    def test_decodes_rfc8251_testvector01_first_four_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "testvector01-first-four.bit"
            output_path = root / "out.s16le"
            input_path.write_bytes(first_packet_records(ROOT / "tests/vectors/rfc8251/testvector01.bit", 4))

            completed = subprocess.run(
                [str(BIN), "8000", "1", "0", str(input_path), str(output_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(len(output_path.read_bytes()), 4480)

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

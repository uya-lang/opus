#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.opus_demo_bitstream import (  # noqa: E402
    BitstreamError,
    iter_packets,
    summarize_bitstream,
)


def packet_record(payload: bytes, final_range: int) -> bytes:
    return len(payload).to_bytes(4, "big") + final_range.to_bytes(4, "big") + payload


class OpusDemoBitstreamTests(unittest.TestCase):
    def write_stream(self, root: Path, data: bytes) -> Path:
        path = root / "vector.bit"
        path.write_bytes(data)
        return path

    def test_iter_packets_reads_opus_demo_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_stream(
                Path(tmp),
                packet_record(b"\x80\x01", 0x12345678)
                + packet_record(b"\xff\x00\x7f", 0x90ABCDEF),
            )

            packets = list(iter_packets(path))

            self.assertEqual(len(packets), 2)
            self.assertEqual(packets[0].index, 0)
            self.assertEqual(packets[0].length, 2)
            self.assertEqual(packets[0].final_range, 0x12345678)
            self.assertEqual(packets[0].payload_offset, 8)
            self.assertEqual(packets[0].payload, b"\x80\x01")
            self.assertEqual(packets[1].index, 1)
            self.assertEqual(packets[1].payload_offset, 18)
            self.assertEqual(packets[1].payload, b"\xff\x00\x7f")

    def test_summarize_bitstream_reports_packet_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_stream(
                Path(tmp),
                packet_record(b"\x01", 0x00000002)
                + packet_record(b"\x02\x03\x04\x05", 0x00000006),
            )

            summary = summarize_bitstream(path)

            self.assertEqual(summary.packet_count, 2)
            self.assertEqual(summary.payload_bytes, 5)
            self.assertEqual(summary.max_packet_bytes, 4)
            self.assertEqual(summary.last_final_range, 0x00000006)

    def test_rejects_empty_or_truncated_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = [
                b"",
                b"\x00\x00",
                (3).to_bytes(4, "big") + b"\x01",
                (3).to_bytes(4, "big") + (9).to_bytes(4, "big") + b"\xaa",
            ]
            for index, data in enumerate(cases):
                with self.subTest(index=index):
                    path = self.write_stream(root, data)
                    with self.assertRaises(BitstreamError):
                        summarize_bitstream(path)

    def test_rejects_zero_length_and_oversized_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zero = self.write_stream(root, (0).to_bytes(4, "big") + (1).to_bytes(4, "big"))
            with self.assertRaises(BitstreamError):
                summarize_bitstream(zero)

            oversized = self.write_stream(
                root,
                (1501).to_bytes(4, "big") + (1).to_bytes(4, "big") + (b"\x00" * 1501),
            )
            with self.assertRaises(BitstreamError):
                summarize_bitstream(oversized)

    def test_cli_validates_and_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_stream(Path(tmp), packet_record(b"\x80", 0x11223344))

            completed = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "opus_demo_bitstream.py"), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("packets=1", completed.stdout)
            self.assertIn("last_final_range=0x11223344", completed.stdout)


if __name__ == "__main__":
    unittest.main()

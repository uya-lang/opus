#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MakeConformanceTests(unittest.TestCase):
    def test_conformance_target_runs_tests_before_decoder_vectors(self) -> None:
        result = subprocess.run(
            ["make", "-n", "conformance"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 0, output)
        test_index = output.find("make test")
        diff_index = output.find("tools/diff_decode.sh tests/vectors")
        self.assertNotEqual(test_index, -1, output)
        self.assertNotEqual(diff_index, -1, output)
        self.assertLess(test_index, diff_index, output)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "objective_quality_gate.py"


def quality_rows(*rows: str) -> str:
    return "\n".join(textwrap.dedent(row).strip() for row in rows) + "\n"


class ObjectiveQualityGateTests(unittest.TestCase):
    def run_gate(self, input_text: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_gate_passes_when_practical_improves_mse_for_each_case(self) -> None:
        output = quality_rows(
            """
            objective_quality, case=voice_16k_mono_24kbps, variant=baseline_complexity0, mse_q8=1000, snr_q8=200
            """,
            """
            objective_quality, case=voice_16k_mono_24kbps, variant=practical_complexity10, mse_q8=900, snr_q8=220
            """,
            """
            objective_quality, case=music_48k_stereo_64kbps, variant=baseline_complexity0, mse_q8=2000, snr_q8=300
            """,
            """
            objective_quality, case=music_48k_stereo_64kbps, variant=practical_complexity10, mse_q8=1700, snr_q8=330
            """,
        )

        result = self.run_gate(output, "--min-mse-improvement-percent", "5")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS voice_16k_mono_24kbps", result.stdout)
        self.assertIn("PASS music_48k_stereo_64kbps", result.stdout)

    def test_gate_fails_when_a_case_does_not_clear_threshold(self) -> None:
        output = quality_rows(
            """
            objective_quality, case=voice_16k_mono_24kbps, variant=baseline_complexity0, mse_q8=1000, snr_q8=200
            """,
            """
            objective_quality, case=voice_16k_mono_24kbps, variant=practical_complexity10, mse_q8=980, snr_q8=201
            """,
        )

        result = self.run_gate(output, "--min-mse-improvement-percent", "5")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL voice_16k_mono_24kbps", result.stdout)
        self.assertIn("requires practical mse_q8 <= 950", result.stdout)

    def test_gate_rejects_missing_baseline_or_practical_rows(self) -> None:
        output = quality_rows(
            """
            objective_quality, case=voice_16k_mono_24kbps, variant=baseline_complexity0, mse_q8=1000, snr_q8=200
            """,
        )

        result = self.run_gate(output)

        self.assertEqual(result.returncode, 2)
        self.assertIn("missing practical row", result.stderr)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "subjective_samples.py"
MANIFEST = ROOT / "samples" / "subjective" / "manifest.json"


class SubjectiveSamplesTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_manifest_validates(self) -> None:
        result = self.run_tool("validate", str(MANIFEST))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("subjective sample case(s)", result.stdout)

    def test_generate_writes_wav_files_matching_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = self.run_tool("generate", str(MANIFEST), "--output-dir", str(output_dir))

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            cases = manifest["cases"]
            self.assertGreaterEqual(len(cases), 4)

            for case in cases:
                wav_path = output_dir / case["output_wav"]
                self.assertTrue(wav_path.is_file(), wav_path)
                with wave.open(str(wav_path), "rb") as wav:
                    self.assertEqual(wav.getnchannels(), case["channels"])
                    self.assertEqual(wav.getframerate(), case["sample_rate_hz"])
                    self.assertEqual(wav.getsampwidth(), 2)
                    expected_frames = case["sample_rate_hz"] * case["duration_ms"] // 1000
                    self.assertEqual(wav.getnframes(), expected_frames)
                    preview = wav.readframes(min(256, expected_frames))
                    self.assertNotEqual(set(preview), {0}, f"{case['id']} should not be all silence")
                self.assertIn(f"generated: {case['id']}", result.stdout)

    def test_validate_rejects_output_paths_that_escape_sample_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "format": "uopus.subjective-samples.v1",
                        "cases": [
                            {
                                "id": "bad-path",
                                "title": "Bad Path",
                                "category": "speech",
                                "sample_rate_hz": 16000,
                                "channels": 1,
                                "duration_ms": 1000,
                                "generator": "voice_pulses",
                                "output_wav": "../bad.wav",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_tool("validate", str(manifest))

            self.assertEqual(result.returncode, 2)
            self.assertIn("escapes sample output root", result.stderr)


if __name__ == "__main__":
    unittest.main()

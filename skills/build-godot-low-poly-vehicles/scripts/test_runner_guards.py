#!/usr/bin/env python3
"""Standard-library safety tests. Does not launch Godot or render images."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_fixture as runner


class CaptureGuards(unittest.TestCase):
    def test_nonempty_rejected_before_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            stale = output / "traffic_models_front.png"
            stale.write_bytes(runner.PNG_SIGNATURE + b"stale")
            with patch.object(sys, "argv", ["runner", "--capture", str(output)]), patch.object(runner.subprocess, "run") as engine:
                with self.assertRaises(ValueError):
                    runner.main()
                engine.assert_not_called()
            self.assertEqual(stale.read_bytes(), runner.PNG_SIGNATURE + b"stale")

    def test_installed_skill_rejected_before_engine(self):
        root = Path(runner.__file__).resolve().parents[1]
        for output in [root, root / "forbidden-captures"]:
            with self.subTest(output=output), patch.object(sys, "argv", ["runner", "--capture", str(output)]), patch.object(runner.subprocess, "run") as engine:
                with self.assertRaises(ValueError):
                    runner.main()
                engine.assert_not_called()
        self.assertFalse((root / "forbidden-captures").exists())

    def test_symlink_into_skill_rejected(self):
        root = Path(runner.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            alias = Path(temp) / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                runner.prepare_capture_directory(alias / "captures", root)

    def test_new_empty_and_file_destinations(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            output = base / "new" / "captures"
            self.assertEqual(runner.prepare_capture_directory(output, base / "skill"), output)
            self.assertEqual(runner.prepare_capture_directory(output, base / "skill"), output)
            file = base / "file"
            file.write_text("keep")
            with self.assertRaises(ValueError):
                runner.prepare_capture_directory(file, base / "skill")

    def test_missing_empty_or_non_png_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "capture.png"
            with self.assertRaises(RuntimeError):
                runner.validate_capture(path)
            for data in [b"", runner.PNG_SIGNATURE, b"invalid file contents"]:
                path.write_bytes(data)
                with self.assertRaises(RuntimeError):
                    runner.validate_capture(path)
            # A signature check is not a complete PNG decoder or visual QA.
            path.write_bytes(runner.PNG_SIGNATURE + b"payload")
            runner.validate_capture(path)


if __name__ == "__main__":
    unittest.main()

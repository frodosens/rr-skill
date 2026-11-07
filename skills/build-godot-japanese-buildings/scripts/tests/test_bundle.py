"""Stdlib-only portability and safety tests. Does not need Blender or Godot."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("building_runner", ROOT / "scripts/run_sample.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class BundleTests(unittest.TestCase):
    def test_materialize_dependencies(self):
        with tempfile.TemporaryDirectory(prefix="building-portability-") as temporary:
            output = Path(temporary) / "fresh workspace"
            report = runner.prepare(output)
            self.assertEqual(report["status"], "PREPARED")
            manifest = json.loads((output / runner.MARKER).read_text())
            for entry in manifest["files"]:
                self.assertEqual(runner.digest(output / entry["workspace"]), entry["sha256"])
            for name in runner.SAMPLES.values():
                self.assertTrue((output / name / "project/project.godot").is_file())
                self.assertTrue((output / name / "project/assets/fuji_destinations/scenes").is_dir())
            hotel = output / runner.SAMPLES["hotel"] / "source/build_hotel.py"
            self.assertTrue((hotel.parent / "../../fuji_destination_assets_v1/source/build_assets.py").resolve().is_file())
            with self.assertRaises(ValueError):
                runner.prepare(output)

    def test_rejects_install_write_and_unprepared_workspace(self):
        with self.assertRaises(ValueError):
            runner.prepare(ROOT / "generated")
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                runner.workspace(Path(temporary))

    def test_copied_skill_works_without_original_parent(self):
        with tempfile.TemporaryDirectory(prefix="building-standalone-") as temporary:
            copy = Path(temporary) / "skill"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            result = subprocess.run([sys.executable, str(copy / "scripts/run_sample.py"), "prepare",
                                     "--output", str(Path(temporary) / "output")], cwd=temporary,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "PREPARED")


if __name__ == "__main__":
    unittest.main()

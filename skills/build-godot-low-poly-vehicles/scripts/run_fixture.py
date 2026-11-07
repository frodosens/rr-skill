#!/usr/bin/env python3
"""Run a relocatable Godot vehicle fixture in an isolated writable copy."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def prepare_capture_directory(path, skill_root):
    output = path.resolve()
    root = skill_root.resolve()
    if output == root or root in output.parents:
        raise ValueError("Capture output must be outside the installed skill")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Capture output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)
    return output


def validate_capture(path):
    if not path.is_file() or path.stat().st_size <= len(PNG_SIGNATURE):
        raise RuntimeError("Missing or empty capture: " + str(path))
    with path.open("rb") as stream:
        if stream.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
            raise RuntimeError("Invalid PNG signature: " + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default="godot", help="Godot 4.6 executable")
    parser.add_argument("--capture", type=Path, help="Also render NPC gallery PNGs to this directory (requires display/GPU)")
    args = parser.parse_args()
    skill_root = Path(__file__).resolve().parents[1]
    source = skill_root / "assets" / "vehicle-fixture"
    # Reject stale/unsafe destinations before any Godot process starts.
    output = prepare_capture_directory(args.capture, skill_root) if args.capture else None
    with tempfile.TemporaryDirectory(prefix="vehicle-skill-") as temp:
        base = Path(temp)
        project = base / "project"
        shutil.copytree(source, project, ignore=shutil.ignore_patterns(".godot", "*.uid"))
        env = os.environ.copy()
        for variable, folder in [("HOME", "home"), ("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache")]:
            location = base / folder
            location.mkdir()
            env[variable] = str(location)
        command = [args.godot, "--path", str(project), "--audio-driver", "Dummy"]
        for test in ["test_player_visual.gd", "test_traffic_visuals.gd"]:
            subprocess.run(command + ["--headless", "--script", "res://tests/" + test], env=env, check=True, timeout=120)
        if output is not None:
            subprocess.run(command + ["--script", "res://tools/capture_traffic_models.gd", "--", str(output)], env=env, check=True, timeout=180)
            expected = ["traffic_models_front", "traffic_models_rear"] + ["traffic_model_" + kind for kind in ["taxi", "truck", "sedan_a", "sedan_b", "hatchback"]]
            for name in expected:
                validate_capture(output / (name + ".png"))


if __name__ == "__main__":
    main()

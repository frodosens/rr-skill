#!/usr/bin/env python3
"""Materialize and run the bundled building examples in a separate workspace.

No game checkout, provider account or network download is used. Blender/Godot
are explicit host dependencies. Generated results never write into this skill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

SKILL = Path(__file__).resolve().parents[1]
SAMPLES = {"buildings": "fuji_geometry_nodes_assets_v2", "hotel": "fuji_onsen_hotel_massing_v3"}
MARKER = "building_sample_workspace.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outside_skill(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path == SKILL or SKILL in path.parents:
        raise ValueError("Output must be outside the installed skill directory.")
    return path


def prepare(output: Path) -> dict:
    output = outside_skill(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite a non-empty output directory; choose a new workspace.")
    output.mkdir(parents=True, exist_ok=True)
    inventory = []
    for category in ("scripts/samples", "assets/templates"):
        base = SKILL / category
        for source in sorted(base.rglob("*")):
            if not source.is_file() or "__pycache__" in source.parts:
                continue
            target = output / source.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            inventory.append({"bundled": str(source.relative_to(SKILL)),
                              "workspace": str(target.relative_to(output)), "sha256": digest(source)})
    for name in SAMPLES.values():
        sample = output / name
        for folder in ("evidence", "renders", "references", "models", "project/assets/fuji_destinations/scenes"):
            (sample / folder).mkdir(parents=True, exist_ok=True)
        reference_folder = "models" if name == SAMPLES["hotel"] else "references"
        for source, relative in [("current_blue_rally_reference.glb", f"{reference_folder}/current_blue_rally_reference.glb"),
                                 ("vehicle_reference_dimensions.json", "evidence/vehicle_reference_dimensions.json")]:
            original = SKILL / "assets/fixtures" / source
            target = sample / relative
            shutil.copy2(original, target)
            inventory.append({"bundled": str(original.relative_to(SKILL)),
                              "workspace": str(target.relative_to(output)), "sha256": digest(original)})
    report = {"schema": 1, "scope": "Standalone unplaced building assets. No game/world acceptance.",
              "samples": SAMPLES, "files": inventory}
    (output / MARKER).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {"status": "PREPARED", "workspace": str(output), "files": len(inventory)}


def workspace(path: Path) -> Path:
    path = outside_skill(path)
    marker = path / MARKER
    if not marker.is_file():
        raise ValueError("Missing workspace marker. Run prepare --output PATH first.")
    if json.loads(marker.read_text())["schema"] != 1:
        raise ValueError("Unsupported workspace schema.")
    return path


def binary(value: str) -> str:
    found = shutil.which(value)
    if not found:
        raise ValueError(f"Required executable not found: {value}. Install it separately or supply its path.")
    return found


def execute(command: list[str], root: Path, label: str, timeout: int, env=None) -> None:
    log = root / "evidence" / (label + ".log")
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                                env=env, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{label} failed ({result.returncode}); inspect {log}")
    print(json.dumps({"step": label, "status": "PASS", "log": str(log)}), flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Copy all required sources, templates and fixtures to a new output directory")
    prep.add_argument("--output", type=Path, required=True)
    for command in ("build", "validate", "godot-check", "render"):
        step = sub.add_parser(command)
        step.add_argument("--workspace", type=Path, required=True)
        step.add_argument("--sample", choices=["all", *SAMPLES], default="all")
        step.add_argument("--timeout", type=int, default=1200, help="Maximum seconds per subprocess")
        if command in ("build", "render"):
            step.add_argument("--blender", default="blender")
            step.add_argument("--threads", type=int, default=2)
        if command == "godot-check":
            step.add_argument("--godot", default="godot")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            print(json.dumps(prepare(args.output), indent=2))
            return 0
        if args.timeout <= 0 or getattr(args, "threads", 1) <= 0:
            raise ValueError("Timeout and thread count must be positive.")
        base = workspace(args.workspace)
        choices = SAMPLES if args.sample == "all" else [args.sample]
        for choice in choices:
            root = base / SAMPLES[choice]
            if args.command in ("build", "render"):
                scripts = {"buildings": ("build_node_assets.py", "render_assets.py"),
                           "hotel": ("build_hotel.py", "render_site_massing.py")}
                script = scripts[choice][0 if args.command == "build" else 1]
                execute([binary(args.blender), "--background", "--factory-startup", "--threads", str(args.threads),
                         "--python-exit-code", "1", "--python", str(root / "source" / script)],
                        root, args.command, args.timeout)
            elif args.command == "validate":
                scripts = ["validate_glb.py"]
                if choice == "hotel":
                    scripts += ["check_export_bounds.py", "check_geometry_channels.py", "audit_prepared_contract.py"]
                for script in scripts:
                    execute([sys.executable, str(root / "source" / script)], root, Path(script).stem, args.timeout)
            elif args.command == "godot-check":
                env = os.environ.copy()
                env.update(GODOT=binary(args.godot), PYTHON=sys.executable)
                execute([binary("bash"), str(root / "source/run_checks.sh")], root, "godot_check_runner", args.timeout, env)
        return 0
    except (ValueError, OSError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

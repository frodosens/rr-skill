#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT="${GODOT:-godot}"
PYTHON="${PYTHON:-python3}"
export XDG_DATA_HOME="$ROOT/.home/data" XDG_CONFIG_HOME="$ROOT/.home/config" XDG_CACHE_HOME="$ROOT/.home/cache"
cp "$ROOT/evidence/module_contracts.json" "$ROOT/project/assets/fuji_destinations/module_contracts.json"
"$PYTHON" "$ROOT/source/validate_glb.py"
"$GODOT" --headless --path "$ROOT/project" --editor --import > "$ROOT/evidence/import.log" 2>&1
"$PYTHON" - "$ROOT" <<'PYLOD'
import pathlib,sys
for p in pathlib.Path(sys.argv[1],"project/assets/fuji_destinations/models").glob("*.glb.import"):
 s=p.read_text().replace("meshes/generate_lods=true","meshes/generate_lods=false")
 p.write_text(s)
PYLOD
"$GODOT" --headless --path "$ROOT/project" --editor --import > "$ROOT/evidence/import_final.log" 2>&1
"$GODOT" --headless --path "$ROOT/project" --script res://tools/build_scenes.gd > "$ROOT/evidence/build_scenes.log" 2>&1
"$GODOT" --headless --path "$ROOT/project" --script res://tools/test_assets.gd > "$ROOT/evidence/godot_validation.log" 2>&1
cat "$ROOT/evidence/godot_validation.log"

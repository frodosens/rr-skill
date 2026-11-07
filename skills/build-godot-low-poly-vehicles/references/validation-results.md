# Bundle validation

Date: 2026-11-07. Engine available: Godot 4.6.3.stable.official.7d41c59c4.

- Skill frontmatter validator: passed.
- Python runner compilation: passed (Python standard library only).
- All 10 copied source files: SHA-256/byte identity verified against the source checkout; paths and hashes are recorded in `provenance.json`.
- First development headless run exposed errors in the new player test (it incorrectly read mesh surface materials rather than instance overrides, and assumed the index array was never null). The test was corrected; model code was not changed.
- Final isolated relocated headless run: passed with exit code 0 using Godot 4.6.3. The complete skill was copied under `/tmp` and its Python runner launched from that relocated copy with `TMPDIR=/tmp`; the runner created another isolated project/HOME/XDG copy. Blue player visual: 3,056 triangles, 20 mesh instances, 7 materials, 0 failures. Traffic visuals: 98/98 checks passed across all five kinds. No original project files or external game assets were needed. The development test errors above were resolved before this final run.
- Real renderer gallery: not run; this worker environment has no DISPLAY or Xvfb. No screenshot or GPU correctness claim.
- Full game, mobile device, physical driving, garage UI and save integration: not included or tested by this standalone fixture.

## Capture integrity follow-up

The Python runner now rejects nonempty output directories and paths inside the installed skill before launching any Godot process, including resolved symlink paths. It checks each expected PNG for a file size greater than its eight-byte signature and the correct signature. Five standard-library guard tests passed without launching Godot: stale-output preservation/early rejection, installed-skill rejection, symlink rejection, new/empty/file destinations, and missing/empty/invalid PNG rejection. Source GDScript and provenance hashes remain unchanged. This follow-up changes only Python capture guards and documentation; real rendering remains untested, and the earlier headless model results above are unchanged.

## Source identity correction

Verified the source checkout origin as `https://github.com/frodosens/RallyDelivery.git`. Corrected the earlier mistaken fsnet-godot-demo source attribution in the skill description and provenance/reference documentation. User project context does not establish checkout identity. The recorded source HEAD and all ten copied file hashes are unchanged; byte/hash identity was rechecked after this documentation-only correction.

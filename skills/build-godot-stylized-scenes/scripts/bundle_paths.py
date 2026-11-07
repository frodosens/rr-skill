#!/usr/bin/env python3
"""Local path guards for isolated authoring outputs. No network or project writes."""
from pathlib import Path

def fresh_output(value, *inputs):
    out = Path(value).resolve()
    protected = [Path(p).resolve() for p in inputs] + [Path(__file__).resolve().parents[1]]
    for source in protected:
        if out == source or source in out.parents or out in source.parents:
            raise ValueError(f"Output must be separate from input/skill paths: {out}")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"Output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    return out


def fresh_file(value):
    """Return a nonexistent output file outside this installed skill.

    Existing parent directories are allowed. Callers must create the final file
    exclusively (mode x/xb) so a concurrent writer cannot be overwritten.
    """
    candidate = Path(value)
    if candidate.exists() or candidate.is_symlink():
        raise ValueError(f"Output file must not exist: {candidate}")
    out = candidate.resolve()
    skill = Path(__file__).resolve().parents[1]
    if out == skill or skill in out.parents or out in skill.parents:
        raise ValueError(f"Output file must be outside the skill: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out

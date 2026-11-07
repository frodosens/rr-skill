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

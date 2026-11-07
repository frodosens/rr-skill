#!/usr/bin/env python3
"""Copy the bundled residential006 sample to a new isolated work directory."""
from pathlib import Path
import argparse,shutil
from bundle_paths import fresh_output
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();out=fresh_output(a.output)
shutil.copytree(Path(__file__).resolve().parents[1]/'assets/residential006/project',out/'project')
(out/'evidence').mkdir();(out/'captures').mkdir()
print(out/'project')

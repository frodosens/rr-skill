#!/usr/bin/env python3
"""Bake a leafless distant-tree vector card from the existing offline oak mesh.

No image service, runtime generation, copied imagery, or new tree geometry.
The SVG is an orthographic projection of the original Branches triangles.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from generate_branching_trees import grow
from bundle_paths import fresh_file


def build() -> str:
    meshes, _ = grow(6211, 'oak', False)
    branches = next(mesh for mesh in meshes if mesh.name == 'Branches')
    xs = [v[0] for v in branches.vertices]
    ys = [v[1] for v in branches.vertices]
    lo_x, hi_x = min(xs), max(xs)
    lo_y, hi_y = min(ys), max(ys)
    # Keep the root just inside the card bottom; transparent space separates twigs.
    def project(vertex):
        return (12 + (vertex[0]-lo_x)/(hi_x-lo_x)*232,
                502 - (vertex[1]-lo_y)/(hi_y-lo_y)*492)
    rows = ['<svg xmlns="http://www.w3.org/2000/svg" width="256" height="512" viewBox="0 0 256 512">',
            '<!-- Original oak seed 6211: orthographic Branches mesh, foliage omitted. -->',
            '<g fill="#514940">']
    for i in range(0, len(branches.indices), 3):
        points = [project(branches.vertices[j]) for j in branches.indices[i:i+3]]
        rows.append('<polygon points="' + ' '.join(f'{x:.3f},{y:.3f}' for x,y in points) + '"/>')
    rows.extend(['</g>', '</svg>', ''])
    return '\n'.join(rows)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    TARGET = args.output.resolve() if args.check else fresh_file(args.output)
    data = build()
    if args.check:
        assert TARGET.read_text() == data, 'Bare forest card differs from deterministic bake'
    else:
        with TARGET.open('x', encoding='utf-8') as output:
            output.write(data)
    print('PASS: deterministic bare oak card; source mesh only, 256x512')

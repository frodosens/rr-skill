"""Small, stdlib-only audit of the saved hotel GLBs. Does not launch an engine.

This intentionally rejects transforms and sparse accessors rather than silently
misreporting local bounds as world bounds. The current authored files use neither.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'project/assets/fuji_destinations'


def inspect(path):
    raw = path.read_bytes()
    assert struct.unpack_from('<III', raw) == (0x46546C67, 2, len(raw))
    chunks = {}
    offset = 12
    while offset < len(raw):
        size, kind = struct.unpack_from('<II', raw, offset)
        chunks[kind] = raw[offset + 8:offset + 8 + size]
        offset += 8 + size
    document = json.loads(chunks[0x4E4F534A])
    binary = chunks[0x004E4942]
    nodes = document['nodes']
    roots = document['scenes'][document.get('scene', 0)]['nodes']
    assert roots == [0] and len(nodes) == 1 and nodes[0]['mesh'] == 0
    assert not any(key in nodes[0] for key in ('matrix', 'translation', 'rotation', 'scale', 'children'))
    assert len(document['meshes']) == 1
    low, high = [math.inf] * 3, [-math.inf] * 3
    triangles, vertex_reads = 0, 0
    for primitive in document['meshes'][0]['primitives']:
        assert primitive.get('mode', 4) == 4
        accessor = document['accessors'][primitive['attributes']['POSITION']]
        assert accessor['componentType'] == 5126 and accessor['type'] == 'VEC3'
        assert 'sparse' not in accessor
        view = document['bufferViews'][accessor['bufferView']]
        assert view['buffer'] == 0
        base = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', 12)
        for i in range(accessor['count']):
            point = struct.unpack_from('<fff', binary, base + i * stride)
            assert all(math.isfinite(v) for v in point)
            for axis, value in enumerate(point):
                low[axis] = min(low[axis], value)
                high[axis] = max(high[axis], value)
            vertex_reads += 1
        count = document['accessors'][primitive['indices']]['count'] if 'indices' in primitive else accessor['count']
        assert count % 3 == 0
        triangles += count // 3
    return {
        'file': str(path.relative_to(ROOT)),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw),
        'aabb_min_xyz': low,
        'aabb_max_xyz': high,
        'size_width_depth_height': [high[0] - low[0], high[2] - low[2], high[1] - low[1]],
        'triangles': triangles,
        'material_surfaces': len(document['meshes'][0]['primitives']),
        'position_vertex_reads': vertex_reads,
        'identity_node_transform_verified': True,
    }


def main():
    manifest = json.loads((ASSETS / 'asset_manifest.json').read_text())
    receipts = {}
    for section in ('modules', 'assemblies'):
        for name, module in manifest[section].items():
            for lod, authored in module['lods'].items():
                actual = inspect(ASSETS / authored['file'])
                for key, expected_key in [('aabb_min_xyz', 'aabb_min'), ('aabb_max_xyz', 'aabb_max')]:
                    assert all(abs(a - b) < 1e-4 for a, b in zip(actual[key], authored[expected_key]))
                assert actual['triangles'] == authored['triangles']
                assert actual['material_surfaces'] == authored['surfaces']
                actual['manifest_matches'] = True
                receipts[f'{name}_lod{lod}'] = actual
    output = {
        'status': 'PASS_SAVED_GLB_BOUNDS_AND_COUNTS_ONLY',
        'units': 'metres',
        'axes': 'Godot/glTF +Y up; +Z front; identity root transform',
        'scope': 'Actual position bytes, finite coordinates, bounds, primitive triangle counts and manifest agreement. No engine, GPU, collision, terrain, weather or driving acceptance.',
        'models': receipts,
    }
    (ROOT / 'evidence/hotel_export_bounds_verified.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({key: value['size_width_depth_height'] for key, value in receipts.items()}, indent=2))


if __name__ == '__main__':
    main()

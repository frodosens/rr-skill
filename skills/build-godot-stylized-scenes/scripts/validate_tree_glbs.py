#!/usr/bin/env python3
"""Independent, read-only structural/geometry validation of baked tree GLBs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input',type=Path,required=True,help='Directory produced by generate_branching_trees.py')
ROOT=parser.parse_args().input.resolve()
manifest=json.loads((ROOT/'manifest.json').read_text())
checks=0

def check(value,description):
    global checks
    checks+=1
    assert value,description

for spec in manifest['assets']:
    path=ROOT/spec['file'];data=path.read_bytes()
    magic,version,size=struct.unpack_from('<4sII',data)
    check((magic,version,size)==(b'glTF',2,len(data)),f'{path.name}: GLB header')
    js_size,js_type=struct.unpack_from('<II',data,12)
    check(js_type==0x4E4F534A,'JSON chunk')
    doc=json.loads(data[20:20+js_size])
    offset=20+js_size
    bin_size,bin_type=struct.unpack_from('<II',data,offset)
    check(bin_type==0x004E4942 and offset+8+bin_size==len(data),'BIN chunk')
    buf=data[offset+8:]
    check(hashlib.sha256(data).hexdigest()==spec['sha256'],'Manifest source hash')
    check(not any(key in doc for key in ['animations','skins','images','textures','extensionsRequired']),'Static self-contained geometry')
    check(len(doc['materials'])==2 and len(doc['meshes'])==2,'Two meshes/materials')
    check(all(m.get('alphaMode','OPAQUE')=='OPAQUE' and not m.get('doubleSided',False) for m in doc['materials']),'Opaque back-face culled materials')
    check([n['name'] for n in doc['nodes']]==['Branches','Foliage'],'Stable node names')
    check(not any(k in n for n in doc['nodes'] for k in ['matrix','rotation','translation','scale']),'Identity mesh transforms')
    for view in doc['bufferViews']:
        check(view['byteOffset']%4==0 and view['byteOffset']+view['byteLength']<=len(buf),'Aligned in-bounds buffer view')
    def unpack(index):
        a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
        n={'SCALAR':1,'VEC3':3}[a['type']];fmt={5126:'f',5123:'H'}[a['componentType']]
        flat=struct.unpack_from('<'+fmt*a['count']*n,buf,v['byteOffset'])
        return [flat[i:i+n] for i in range(0,len(flat),n)] if n>1 else flat
    total=0
    for mesh in doc['meshes']:
        check(len(mesh['primitives'])==1,'One surface per mesh')
        p=mesh['primitives'][0];attrs=p['attributes'];verts=unpack(attrs['POSITION']);normals=unpack(attrs['NORMAL']);colors=unpack(attrs['COLOR_0']);indices=unpack(p['indices'])
        check(len(verts)==len(normals)==len(colors),'Attribute counts')
        check(len(indices)%3==0 and min(indices)>=0 and max(indices)<len(verts),'Triangle indices')
        check(all(math.isfinite(v) for arr in (verts,normals,colors) for vec in arr for v in vec),'Finite attributes')
        check(all(0<=v<=1 for vec in colors for v in vec),'Linear color range')
        check(all(abs(math.sqrt(sum(v*v for v in n))-1)<1e-5 for n in normals),'Unit normals')
        for i in range(0,len(indices),3):
            a,b,c=[verts[j] for j in indices[i:i+3]]
            u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
            cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            check(sum(x*x for x in cross)>1e-12,'No degenerate triangles')
            check(sum(cross[j]*normals[indices[i]][j] for j in range(3))>0,'CCW winding matches normals')
        total+=len(indices)//3
    check(total==spec['triangles'],'Reported triangle count')
    budget=manifest['budget'].get('species_overrides',{}).get(spec['species'],manifest['budget'])
    check(total<=budget[spec['lod']+'_max_triangles'],'Mobile geometry budget')
    print(f"PASS {path.name}: {total} triangles, SHA-256 verified, standalone opaque geometry")
print(f'TREE GLB STRUCTURE: {checks}/{checks} passed')

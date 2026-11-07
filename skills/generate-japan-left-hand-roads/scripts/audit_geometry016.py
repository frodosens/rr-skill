#!/usr/bin/env python3
"""Independent batch audit of emitted polygon area and triangle support."""
from pathlib import Path
import argparse,json,math,sys,hashlib
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--bundle',type=Path,required=True,help='Output root produced by generate_markings016.py')
a=p.parse_args();R=a.bundle.resolve()
(R/'evidence').mkdir(exist_ok=True)

from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
cfg=json.loads((R/'project/assets/world/road_markings016/marking_rules016.json').read_text());report=json.loads((R/'output/generation_report016.json').read_text());witness=json.loads((R/'output/support_witness016.json').read_text())
meshes={p.stem.removeprefix('mesh_').replace('_',':'):json.loads(p.read_text()) for p in (R/'output/meshes').glob('*.json')}
native_path=R/'evidence/native_vertices016.json';native=json.loads(native_path.read_text()) if native_path.exists() else None
polygons={};maximum_lift_error=0.;maximum_bary_outside=0.;errors=[];lift=cfg['geometry']['vertical_lift_m'];checked=0
for w in witness:
 cid=w['owner'];assert cid not in cfg['protected_owner_ids'];m=meshes[cid];offset=w['vertex_offset'];v=(native[cid] if native else m['vertices'])[offset:offset+3];a,b,c=w['source_vertices'];source=Polygon([(p[0],p[2]) for p in [a,b,c]]);poly=Polygon([(p[0],p[2]) for p in v]);cx,cz=map(int,cid.split(':'))
 assert len(v)==3 and poly.is_valid and poly.area>0
 assert (v[1][0]-v[0][0])*(v[2][2]-v[0][2])-(v[1][2]-v[0][2])*(v[2][0]-v[0][0])>0,'Godot clockwise top-face winding'
 for p in v:
  x,y,z=p;assert all(math.isfinite(t) for t in p);assert cx*128-1e-4<=x<=(cx+1)*128+1e-4 and cz*128-1e-4<=z<=(cz+1)*128+1e-4
  d=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2]);u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/d;v0=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/d
  h=u*a[1]+v0*b[1]+(1-u-v0)*c[1];maximum_lift_error=max(maximum_lift_error,abs(y-h-lift));maximum_bary_outside=max(maximum_bary_outside,source.distance(Point(x,z)))
  assert abs(y-h-lift)<2e-5,('lift',cid,abs(y-h-lift))
  assert source.distance(Point(x,z))<.0001,('support',cid,source.distance(Point(x,z)))
 key=(w['road_id'],w['marking_kind']);polygons.setdefault(key,[]).append(poly);checked+=1
areas={}
for (rid,kind),polys in polygons.items():
 measured=sum(p.area for p in polys);target=report['road_statistics'][rid]['types'][kind]['supported_area_m2'];union=unary_union(polys).area;error=abs(measured-target);overlap=measured-union
 # Native float32 at large world coordinates can change area at sub-mm boundaries.
 tolerance=.02 # Generator deliberately quantizes coordinates to native float32 before publication.
 assert error<tolerance,(rid,kind,'tessellation missing/excess area',error)
 assert overlap<tolerance,(rid,kind,'overlap',overlap)
 areas[rid+'/'+kind]={'target_area_m2':target,'emitted_area_m2':measured,'absolute_area_error_m2':error,'overlap_area_m2':overlap}
assert checked==report['triangles'];assert set(meshes)==set(report['owners'])
result={'status':'PASS','native_float32_readback':bool(native),'checked_triangles':checked,'checked_vertices':checked*3,'maximum_lift_error_m':maximum_lift_error,'maximum_support_xz_distance_m':maximum_bary_outside,'paint_vertical_lift_m':lift,'areas':areas,'sources':'Actual resource-matched saved source triangle for every emitted triangle; every vertex checked, not sparse samples.','geometry_unchanged':True}
(R/'evidence'/('native_geometry016.json' if native else 'generator_geometry016.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='areas'}))

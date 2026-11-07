#!/usr/bin/env python3
"""Deterministic bounded scenery. Saved, reviewed G007 triangles, never heightfield guesses."""
import argparse, json, math, hashlib, random, sys
from pathlib import Path
import numpy as np
from bundle_paths import fresh_output
from shapely.geometry import Polygon,Point,LineString,box
from shapely.strtree import STRtree
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--project', type=Path, required=True, help='Read-only candidate project')
ap.add_argument('--frozen-project', type=Path, required=True, help='Read-only authoritative snapshot with matching catalog')
ap.add_argument('--triangles', type=Path, required=True, help='Saved triangle JSONL matching catalog SHA-256')
ap.add_argument('--output', type=Path, required=True, help='New/empty additive overlay directory')
a=ap.parse_args(); P=a.project.resolve(); FROZEN=a.frozen_project.resolve(); BASE=P/'assets/world/fuji_v3'
ROOT=fresh_output(a.output,P,FROZEN,a.triangles); OVERLAY=ROOT/'project'

IDS={'3:-11','4:-11','3:-10','4:-10','3:-9','4:-9'}; bounds=box(384,-1408,640,-1024)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cat=json.loads((BASE/'surface_catalog.json').read_text()); frozen=json.loads((FROZEN/'assets/world/fuji_v3/surface_catalog.json').read_text())
assert sha(BASE/'surface_catalog.json')==sha(FROZEN/'assets/world/fuji_v3/surface_catalog.json')
tri_file=a.triangles.resolve();assert sha(tri_file)==cat['triangle_export']['sha256']
source_files={};chosen=[]
for r in cat['resources']:
 if r['chunk_id'] in IDS:
  p=P/r['path'].removeprefix('res://'); assert sha(p)==r['sha256']==sha(FROZEN/r['path'].removeprefix('res://'))
  source_files[r['path']]=r['sha256'];chosen.append(r)
rows=[]
with tri_file.open() as f:
 for line in f:
  r=json.loads(line)
  if r['chunk_id'] in IDS and r['source_kind'] in ['terrain_ground','roadside_ground','terrace_ground']:
   assert r['generation_id']==cat['generation_id'] and r['resource_sha256']==source_files[r['resource_path']] and r['visual_support'] and r['collision_owner'];rows.append(r)
verts=np.array([r['vertices'] for r in rows],dtype=float);polys=[Polygon(t[:,[0,2]]) for t in verts];tree=STRtree(polys)
def support(x,z):
 p=Point(x,z)
 for i in tree.query(p):
  a,b,c=verts[i];u=b[[0,2]]-a[[0,2]];v=c[[0,2]]-a[[0,2]];q=np.array([x,z])-a[[0,2]]
  den=u[0]*v[1]-u[1]*v[0]
  if abs(den)<1e-10:continue
  s=(q[0]*v[1]-q[1]*v[0])/den;t=(u[0]*q[1]-u[1]*q[0])/den
  if s>=-1e-7 and t>=-1e-7 and s+t<=1.0000001:
   n=np.cross(c-a,b-a);n/=np.linalg.norm(n)
   return float(a[1]+s*(b[1]-a[1])+t*(c[1]-a[1])),int(i),abs(float(n[1]))
 return None
ex=json.loads((BASE/'exclusions.json').read_text()); ep=[Polygon(v['vertices']).buffer(float(v.get('margin_m',0))) for v in ex['polygons']];et=STRtree(ep)
layout=json.loads((BASE/'layout_values.json').read_text());roads=[LineString([[p[0],p[2]] for p in r['points']]).buffer(r['width']/2) for r in layout['roads']]
river=LineString([(620,-1430),(640,-1330),(640,-1240),(640,-1160),(640,-1110),(592.779510148,-1111.480940707),(550,-1112),(520,-1090),(455,-1030)]).buffer(7)
pois=[box(p['position'][0]-p['size'][0]/2-7,p['position'][2]-p['size'][1]/2-7,p['position'][0]+p['size'][0]/2+7,p['position'][2]+p['size'][1]/2+7) for p in ex['pois']]
# Two intentionally open meadow pockets, connected through sparse forest edges.
meadows=[Point(468,-1171).buffer(34),Point(568,-1302).buffer(31)]
rng=random.Random(900971); items=[];reject={};occupied=[]
def rejected(reason):reject[reason]=reject.get(reason,0)+1
for kind,attempts in [('tree',2300),('grass',4100),('rock',180),('shrub',240)]:
 for j in range(attempts):
  x=rng.uniform(387,637);z=rng.uniform(-1405,-1027);p=Point(x,z);scale=rng.uniform(.75,1.42) if kind=='tree' else rng.uniform(.7,1.4)
  density=.48+.28*math.sin(x*.044+z*.027)*math.cos(z*.039-x*.016)
  meadow=any(p.within(m) for m in meadows)
  if kind=='tree' and (meadow or rng.random()>density):rejected('tree_clearing_density');continue
  if kind=='grass' and not meadow and rng.random()>.48:continue
  radius={'tree':.24*scale,'grass':.55*scale,'rock':1.15*scale,'shrub':1.15*scale}[kind]
  canopy={'tree':3.2*scale,'grass':radius,'rock':radius,'shrub':radius}[kind]
  if not bounds.covers(p.buffer(canopy)):rejected('scope_edge');continue
  if river.intersects(p.buffer(canopy)):rejected('future_stream_reservation');continue
  if any(q.intersects(p.buffer(canopy)) for q in pois):rejected('poi_clearance');continue
  if any(q.intersects(p.buffer(canopy+1.8)) for q in roads):rejected('road_clearance');continue
  if any(ep[int(i)].intersects(p.buffer(radius+.5)) for i in et.query(p.buffer(radius+.5))):rejected('catalog_exclusion');continue
  if kind=='tree' and any((x-a)**2+(z-b)**2<(2.9*scale)**2 for a,b in occupied):rejected('tree_spacing');continue
  samples=[(x,z)]+[(x+math.cos(k*math.tau/16)*radius,z+math.sin(k*math.tau/16)*radius) for k in range(16)]
  hits=[support(a,b) for a,b in samples]
  if any(h is None for h in hits):rejected('no_saved_support');continue
  if min(h[2] for h in hits)<(.80 if kind=='tree' else .72):rejected('slope');continue
  hs=[h[0] for h in hits];embed=.04 if kind in ['tree','grass'] else .07
  # Full lowest base plane below minimum terrain, not center-height floating.
  y=min(hs)-embed
  if max(hs)-y>(.42 if kind=='tree' else .48 if kind=='grass' else .78):rejected('footprint_relief');continue
  owner=f'{math.floor(x/128)}:{math.floor(z/128)}';assert owner in IDS
  item={'kind':kind,'position':[round(x,6),round(y,6),round(z,6)],'scale':scale,'yaw':rng.uniform(0,math.tau),'variant':j%4,'owner':owner,'cell':f'{math.floor(x/64)}:{math.floor(z/64)}','base_radius':radius,'support_height_range':[min(hs),max(hs)],'support_row':hits[0][1],'max_base_burial':max(hs)-y}
  items.append(item)
  if kind=='tree':occupied.append((x,z))
for p in [ROOT/'output',ROOT/'evidence',OVERLAY/'assets/world/forest009']:p.mkdir(parents=True,exist_ok=True)
data={'schema':1,'generation':'forest-pcg009','seed':900971,'bounds_xz':[384,-1408,640,-1024],'items':items,'source_files':source_files,'target_chunks':sorted(IDS),'original_catalog_status':cat['validation_status'],'original_world_status':cat['world_acceptance_status'],'surface_gate':'EXACT_HASH_MATCH_TO_CALLER_SUPPLIED_FROZEN_SNAPSHOT; independent review and native validation are separate','future_stream_corridor_excluded':True,'meadow_centers':[[468,-1171],[568,-1302]]}
(OVERLAY/'assets/world/forest009/placements.json').write_text(json.dumps(data,indent=2))
(ROOT/'output/placements.json').write_text(json.dumps(data,indent=2))
report={'status':'PLACEMENT_READY_NATIVE_VALIDATION_PENDING','counts':{k:sum(i['kind']==k for i in items) for k in ['tree','grass','rock','shrub']},'resources_checked':len(chosen),'support_triangles':len(rows),'root_samples_per_instance':17,'max_root_burial_m':max((i['max_base_burial'] for i in items),default=0),'rejections':reject,'protected_lakeside_chunks_untouched':True,'source_geometry_sha_matched':True,'catalog_not_promoted':True,'full_world_acceptance':cat['world_acceptance_status'],'triangle_source_sha256':sha(tri_file),'footprint_note':'16 point perimeter plus center. Trunk radius conservatively .24scale; grass .55scale; rock/shrub1.15scale. Base plane embedded below minimum. Not proof for arbitrary mesh vertices; native checker separately samples actual mesh bases.'}
(ROOT/'evidence/placement_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

from pathlib import Path
import argparse,json,math,hashlib,sys
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
from bundle_paths import fresh_output
import shapely
from shapely.geometry import Polygon,box
ap=argparse.ArgumentParser(description='Bake fixed-scope 011 distance/normal field from hash-checked saved triangles; no geometry changes.')
ap.add_argument('--project',type=Path,required=True)
ap.add_argument('--triangles',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args();P=a.project.resolve();src=a.triangles.resolve();ROOT=fresh_output(a.output,P,src)
BASE=P/'assets/world/fuji_v3';A=ROOT/'project/assets/world/ground011'
A.mkdir(parents=True);(ROOT/'evidence').mkdir()

IDS={'3:-11','4:-11','3:-10','4:-10','3:-9','4:-9'}; xmin,zmin,xmax,zmax=384,-1408,640,-1024;dx=.5; W,H=512,768
cat=json.loads((BASE/'surface_catalog.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(src)==cat['triangle_export']['sha256']; sources={r['path']:r['sha256'] for r in cat['resources'] if r['chunk_id']in IDS}
for path,h in sources.items():assert sha(P/path.removeprefix('res://'))==h
tri=[];roads=[]; clip=box(xmin-24,zmin-24,xmax+24,zmax+24)
with src.open()as f:
 for line in f:
  r=json.loads(line)
  if not (r['visual_support'] and r['collision_owner']):continue
  assert r['generation_id']==cat['generation_id']
  if r['chunk_id'] in IDS:assert r['resource_sha256']==sources[r['resource_path']]
  v=np.array(r['vertices'],dtype=float)
  if r['chunk_id']in IDS and r['source_kind']!='water_surface':tri.append(v)
  if r['source_kind']in['road_surface','bridge_deck'] and v[:,0].max()>xmin-24 and v[:,0].min()<xmax+24 and v[:,2].max()>zmin-24 and v[:,2].min()<zmax+24:
   poly=Polygon(v[:,[0,2]])
   if poly.area>1e-9:roads.append(poly)
xs=xmin+(np.arange(W)+.5)*dx;zs=zmin+(np.arange(H)+.5)*dx
normals=np.zeros((H,W,3),dtype=np.float32);height=np.full((H,W),-999.,dtype=np.float32)
for v in tri:
 lo=np.floor((v[:,[0,2]].min(axis=0)-[xmin,zmin])/dx-.5).astype(int);hi=np.ceil((v[:,[0,2]].max(axis=0)-[xmin,zmin])/dx-.5).astype(int)
 x0,x1=max(0,lo[0]),min(W-1,hi[0]);z0,z1=max(0,lo[1]),min(H-1,hi[1])
 if x0>x1 or z0>z1:continue
 X,Z=np.meshgrid(xs[x0:x1+1],zs[z0:z1+1]);a,b,c=v;u=b-a;vv=c-a;den=u[0]*vv[2]-u[2]*vv[0]
 if abs(den)<1e-9:continue
 s=((X-a[0])*vv[2]-(Z-a[2])*vv[0])/den;t=(u[0]*(Z-a[2])-u[2]*(X-a[0]))/den
 yy=a[1]+s*u[1]+t*vv[1];sub=height[z0:z1+1,x0:x1+1];inside=(s>=-1e-5)&(t>=-1e-5)&(s+t<=1.00001)&(yy>=sub-.0001)
 n=np.cross(vv,u);n/=np.linalg.norm(n)
 if n[1]<0:n=-n
 sub[inside]=yy[inside];normals[z0:z1+1,x0:x1+1][inside]=n
missing=int((height<-900).sum());assert missing==0,missing
# Smooth shading normals only, never saved vertex heights/collision.
for k in range(3):normals[:,:,k]=gaussian_filter(normals[:,:,k],sigma=3,mode='nearest')
normals/=np.linalg.norm(normals,axis=2)[:,:,None]
road=shapely.union_all(roads);X,Z=np.meshgrid(xs,zs);points=shapely.points(X.ravel(),Z.ravel());dist=shapely.distance(points,shapely.boundary(road));inside=shapely.contains_xy(road,X.ravel(),Z.ravel());dist[inside]*=-1
sdf=dist.reshape(H,W);field=np.stack([np.clip((sdf+8)/24,0,1),(normals[:,:,0]+1)/2,(normals[:,:,2]+1)/2],axis=2)
Image.fromarray(np.uint8(np.round(field*255)),'RGB').save(A/'ground_field011.png')
report={'schema':1,'generation':'forest-ground011-shading-only','bounds_xz':[xmin,zmin,xmax,zmax],'resolution':[W,H],'texel_m':dx,'channels':{'R':'signed distance to actual saved road/bridge polygon boundary, encoded(d+8)/24','G':'1.5m Gaussian smoothed saved triangle normal world X, encoded(n+1)/2','B':'same world normal Z'},'native_source_files':sources,'source_triangles_sha256':sha(src),'saved_source_triangles':len(tri),'missing_pixels':missing,'road_polygons':len(roads),'geometry_change':False,'collision_change':False,'scope_feather_m':12,'normal_smoothing_sigma_m':1.5,'field_sha256':sha(A/'ground_field011.png')}
(A/'field_contract011.json').write_text(json.dumps(report,indent=2));(ROOT/'evidence/field_report011.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

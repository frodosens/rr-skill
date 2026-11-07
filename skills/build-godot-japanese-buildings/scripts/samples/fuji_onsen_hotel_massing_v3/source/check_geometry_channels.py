"""Independent saved-index/exposure audit, no engine or runtime acceptance."""
import hashlib,json,struct,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
receipts={}
for file in sorted((ROOT/'project/assets/fuji_destinations/models').glob('*.glb')):
 raw=file.read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);binary=raw[28+size:]
 def read(index):
  a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];fmt='<'+{5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']]*{'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];stride=v.get('byteStride',struct.calcsize(fmt));offset=v.get('byteOffset',0)+a.get('byteOffset',0)
  values=[struct.unpack_from(fmt,binary,offset+i*stride) for i in range(a['count'])]
  if a.get('normalized'):values=[tuple(x/(65535 if a['componentType']==5123 else 255) for x in p) for p in values]
  return values
 degenerate=invalid=snow_inside=water_exposed=0;alphas=set();materials=[]
 for p in doc['meshes'][0]['primitives']:
  assert p.get('mode',4)==4
  pts=read(p['attributes']['POSITION']);colors=read(p['attributes']['COLOR_0']);indices=[x[0] for x in read(p['indices'])];material=doc['materials'][p['material']]['name'];materials.append(material);alphas.update(c[3] for c in colors)
  assert len(pts)==len(colors) and len(indices)%3==0
  if material=='water':water_exposed+=sum(c[3]>.5 for c in colors)
  for i in range(0,len(indices),3):
   ids=indices[i:i+3]
   if any(j>=len(pts) for j in ids):invalid+=1;continue
   a,b,c=[pts[j] for j in ids];u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
   if sum(x*x for x in n)<1e-14:degenerate+=1
   if n[1]>1e-8 and all(abs(pts[j][0])<22.25-1e-4 and abs(pts[j][2])<13.75-1e-4 and pts[j][1]<7 and colors[j][3]>.5 for j in ids):snow_inside+=1
 assert invalid==degenerate==snow_inside==water_exposed==0
 assert alphas=={0.,1.} and not doc.get('textures')
 assert set(materials)<={'cedar','charcoal','plaster','stone','vermilion','field','water','bamboo'}
 assert all(m.get('alphaMode','OPAQUE')=='OPAQUE' for m in doc['materials'])
 receipts[file.stem]={'sha256':hashlib.sha256(raw).hexdigest(),'invalid_indices':invalid,'degenerate_triangles':degenerate,'upward_exposed_triangles_wholly_inside_main_roof_below_y7':snow_inside,'exposed_water_vertices':water_exposed,'alpha_values':sorted(alphas),'materials':materials}
assert len(receipts)==4
report={'status':'PASS_SAVED_TRIANGLE_AND_EXPOSURE_CHECKS','scope':'Actual v3 GLB index/color bytes; narrow shelter-interior predicate excludes boundary-straddling faces. Not shader/Godot/weather/terrain/driving acceptance.','models':receipts}
(ROOT/'evidence/hotel_geometry_channels_verified.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'models':len(receipts)}))

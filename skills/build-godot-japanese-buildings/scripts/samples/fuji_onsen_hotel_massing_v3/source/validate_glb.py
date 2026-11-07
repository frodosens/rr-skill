"""Strict offline GLB policy inspection, not a game-dev CLI receipt."""
import struct,json,os,hashlib,math
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE=ROOT+'/project/assets/fuji_destinations'
manifest=json.load(open(BASE+'/asset_manifest.json'))
ctype={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'};size={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
checks=[];models={};failures=[];vertex_samples={}
def check(cond,msg):
 checks.append({'pass':bool(cond),'check':msg})
 if not cond:failures.append(msg)
def parse(path):
 data=open(path,'rb').read();magic,ver,total=struct.unpack('<4sII',data[:12]);check(magic==b'glTF' and ver==2 and total==len(data),path.split('/')[-1]+': GLB header valid')
 n,t=struct.unpack('<I4s',data[12:20]);doc=json.loads(data[20:20+n]);off=20+n;nb,tb=struct.unpack('<I4s',data[off:off+8]);bin=data[off+8:off+8+nb]
 def acc(i):
  a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];fmt='<'+ctype[a['componentType']]*size[a['type']];sz=struct.calcsize(fmt);offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',sz)
  out=[struct.unpack_from(fmt,bin,offset+j*stride) for j in range(a['count'])]
  if a.get('normalized'):
   den={5121:255,5123:65535}.get(a['componentType'],1);out=[tuple(x/den for x in v) for v in out]
  return out
 check(len(doc.get('nodes',[]))==1 and not any(k in doc['nodes'][0] for k in ['translation','rotation','scale','matrix','children']),'Single identity local root '+path.split('/')[-1])
 samples=[];tri=0;surfaces=0;colors=set();aabb=[];degenerate=0;names=set();vertices=0;alpha0=0;alpha1=0
 for mesh in doc['meshes']:
  for p in mesh['primitives']:
   surfaces+=1;check(p.get('mode',4)==4,'Triangle primitive '+path.split('/')[-1]);pts=acc(p['attributes']['POSITION']);aabb+=pts;vertices+=len(pts)
   names.add(doc['materials'][p['material']]['name']);check('COLOR_0' in p['attributes'],'Snow exposure channel exists '+path.split('/')[-1])
   if 'COLOR_0' in p['attributes']:
    cs=acc(p['attributes']['COLOR_0']);normals=acc(p['attributes']['NORMAL']);samples.extend(zip(pts,normals,[c[3] for c in cs]));colors.update(round(c[3],3) for c in cs);alpha0+=sum(c[3]<.01 for c in cs);alpha1+=sum(c[3]>.99 for c in cs)
   ix=[x[0] for x in acc(p['indices'])];tri+=len(ix)//3
   for i in range(0,len(ix),3):
    a,b,c=[pts[ix[i+j]] for j in range(3)];ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)];cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
    if sum(x*x for x in cross)<1e-14:degenerate+=1
 check(all(math.isfinite(v) for p in aabb for v in p),'Finite positions '+path.split('/')[-1]);check(degenerate==0,'No degenerate triangles '+path.split('/')[-1]);check(names<=set(manifest['materials']),'Palette-only materials '+path.split('/')[-1]);check(not doc.get('images') and not doc.get('textures'),'Zero texture dependencies '+path.split('/')[-1]);check(all(m.get('alphaMode','OPAQUE')=='OPAQUE' for m in doc['materials']),'Opaque only '+path.split('/')[-1]);check(surfaces<=8,'At most eight material surfaces '+path.split('/')[-1]);check(colors<={0.0,1.0},'Binary exposure preserved '+path.split('/')[-1])
 vertex_samples[os.path.basename(path)]=samples
 return {'triangles':tri,'surfaces':surfaces,'vertices':vertices,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'degenerate_triangles':degenerate,'sheltered_vertices':alpha0,'exposed_vertices':alpha1,'aabb_min':[min(p[i] for p in aabb) for i in range(3)],'aabb_max':[max(p[i] for p in aabb) for i in range(3)]}
for group in ['modules','assemblies']:
 for name,item in manifest[group].items():
  for lod,info in item['lods'].items():
   stats=parse(BASE+'/'+info['file']);models[name+'_lod'+lod]=stats
   check(stats['triangles']==info['triangles'],'Saved triangles equal authoring manifest '+name+'_lod'+lod)
   for axis in range(3):check(abs(stats['aabb_min'][axis]-info['aabb_min'][axis])<.001 and abs(stats['aabb_max'][axis]-info['aabb_max'][axis])<.001,'GLB bounds/axis correct '+name+'_lod'+lod+' axis '+str(axis))
  check(item['lods']['1']['triangles']<=item['lods']['0']['triangles'],'LOD never exceeds near geometry '+name)
  if group=='assemblies':check(item['lods']['0']['triangles']<=12000,'Location under 12k triangles '+name)
for name in manifest['modules']:
 check(len(manifest['modules'][name]['shelters'])==1,'One roof shelter only '+name)
 check(models[name+'_lod0']['sheltered_vertices']>0,'Sheltered vertices authored '+name)
check(sum(len(m['shelters']) for m in manifest['modules'].values())==1,'One contiguous hotel roof descriptor only')
# Geometric regression: every upward-facing vertex below a rectangular eave
# must have exposure zero in both independent modules and baked assemblies.
for group in ['modules','assemblies']:
 for name,item in manifest[group].items():
  roofs=[]
  if group=='modules':roofs=[(r,(0,0,0),0) for r in item['shelters']]
  else:
   for entry in item['layout']:
    for roof in manifest['modules'][entry['module']]['shelters']:roofs.append((roof,entry['position'],entry['yaw']))
  for lod in ['0','1']:
   bad=[];tested=0
   for p,n,a in vertex_samples[os.path.basename(item['lods'][lod]['file'])]:
    if n[1]<=.18:continue
    for roof,pos,yaw in roofs:
     dx=p[0]-pos[0];dz=p[2]-pos[2];cs=math.cos(yaw);sn=math.sin(yaw);x=dx*cs-dz*sn;z=dx*sn+dz*cs;y=p[1]-pos[1]
     if abs(x-roof['position'][0])<roof['size'][0]/2-.001 and abs(z-roof['position'][2])<roof['size'][2]/2-.001 and y<roof['position'][1]-.001:
      tested+=1
      if a>.001:bad.append(tuple(round(v,3) for v in p))
   check(not bad,'No exposed upward vertices beneath eaves '+name+'_lod'+lod+' ('+str(tested)+' covered vertices)')
   if bad:failures.append('Example uncovered points '+name+': '+str(bad[:8]))
for name in manifest['modules']:
 for lod in ['0','1']:
  check(abs(manifest['modules'][name]['shelters'][0]['roof_top_y']-models[name+'_lod'+lod]['aabb_max'][1])<.001,'Shelter roof_top_y matches exported maximum '+name+'_lod'+lod)
result={'passed':not failures,'checks':len(checks),'failures':failures,'scope':'Static exported bytes only. Not Android, Godot GPU, world placement, or driving acceptance.','models':models,'checks_detail':checks}
json.dump(result,open(ROOT+'/evidence/glb_validation.json','w'),indent=2)
print(json.dumps({k:result[k] for k in ['passed','checks','failures']}));raise SystemExit(1 if failures else 0)

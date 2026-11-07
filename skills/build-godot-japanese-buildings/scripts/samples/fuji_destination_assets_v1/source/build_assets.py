"""Original offline mesh authoring; no downloaded geometry or paid provider.
Coordinates authored in metres, Godot Y-up, front +Z. Export Blender glTF Y-up.
"""
import bpy, bmesh, math, json, os, hashlib, random
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT,'project/assets/fuji_destinations')
os.makedirs(OUT+'/models',exist_ok=True)
PALETTE={
 'cedar':(0.55,0.39,0.26,1), 'charcoal':(0.22,0.29,0.29,1),
 'plaster':(0.86,0.83,0.73,1),'stone':(0.48,0.54,0.48,1),
 'vermilion':(0.70,0.28,0.16,1),'field':(0.50,0.59,0.30,1),
 'water':(0.36,0.57,0.55,1),'bamboo':(0.67,0.57,0.36,1)}
def linear_color(c): return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c[:3])+(c[3],)
MATS={}
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for name,color in PALETTE.items():
 color=linear_color(color)
 m=bpy.data.materials.new(name); m.diffuse_color=color; m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=.93
 MATS[name]=m
class Mesh:
 def __init__(self): self.verts=[];self.faces=[];self.mats=[];self.cols=[];self.proxies=[];self.shelters=[]
 def face(self,vs,mat,ex=1,tint=1):
  tint=max(0,min(1,tint))
  n=len(self.verts); self.verts.extend(vs); self.faces.append(tuple(range(n,n+len(vs))));self.mats.append(mat);self.cols.append((tint,tint,tint,ex))
 def box(self,p,s,mat,ex=1,tint=1):
  x,y,z=p; a,b,c=[v/2 for v in s]
  vs=[(x+u*a,y+v*b,z+w*c) for u,v,w in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
  for f in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(0,1,5,4),(3,7,6,2)]: self.face([vs[i] for i in f],mat,ex,tint)
 def proxy(self,name,p,s):self.proxies.append({'name':name,'position':list(p),'size':list(s),'kind':'box','vehicle_surface':False})
 def cylinder(self,a,b,r,mat,ex=1,n=8,r2=None,tint=1,end_mat=None):
  a=Vector(a);b=Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,1,0)))
  if u.length<.01:u=axis.cross(Vector((1,0,0)))
  u.normalize();v=axis.cross(u).normalized(); r2=r if r2 is None else r2
  pts1=[a+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for i in range(n)]
  pts2=[b+r2*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for i in range(n)]
  for i in range(n): j=(i+1)%n; self.face([pts1[i],pts1[j],pts2[j],pts2[i]],mat,ex,tint)
  self.face(list(reversed(pts1)),end_mat or mat,ex,tint);self.face(pts2,end_mat or mat,ex,tint)
 def roof(self,x,z,w,d,eave,ridge,mat='charcoal',ex=1):
  # Hipped four planes, closed 22cm fascia, deliberately broad low-poly silhouette.
  a=(x-w/2,eave,z-d/2);b=(x+w/2,eave,z-d/2);c=(x+w/2,eave,z+d/2);f=(x-w/2,eave,z+d/2)
  r1=(x-w*.27,ridge,z);r2=(x+w*.27,ridge,z)
  for face in [(a,b,r2,r1),(b,c,r2),(c,f,r1,r2),(f,a,r1)]:self.face(face,mat,ex)
  bottom=[(p[0],p[1]-.22,p[2]) for p in [a,b,c,f]]
  for i in range(4): j=(i+1)%4;self.face(([a,b,c,f][i],[a,b,c,f][j],bottom[j],bottom[i]),mat,ex,.86)
  self.face(bottom,mat,0,.7)
  self.box((x,ridge+.10,z),(w*.57,.23,.25),mat,ex,.91)
 def rock(self,p,s,mat='stone',ex=1):
  x,y,z=p;w,h,d=s;n=7
  lo=[(x+w*.5*math.cos(i*math.tau/n),y,z+d*.5*math.sin(i*math.tau/n)) for i in range(n)]
  hi=[(x+w*.35*math.cos(i*math.tau/n+.16),y+h,z+d*.33*math.sin(i*math.tau/n+.16)) for i in range(n)]
  for i in range(n):j=(i+1)%n;self.face((lo[i],lo[j],hi[j],hi[i]),mat,ex,1+(i%3-1)*.06)
  self.face(hi,mat,ex,1.08);self.face(list(reversed(lo)),mat,0)
 def append(self,other,p=(0,0,0),yaw=0):
  cs,sn=math.cos(yaw),math.sin(yaw)
  def tr(v):return (p[0]+v[0]*cs+v[2]*sn,p[1]+v[1],p[2]-v[0]*sn+v[2]*cs)
  for face,mat,col in zip(other.faces,other.mats,other.cols): self.face([tr(other.verts[i]) for i in face],mat,col[3],col[0])
  # Compiled packs are VISUAL ONLY; separate module proxies are opt-in.
 def stats(self):
  vs=[tuple(v) for v in self.verts]; tri=sum(len(f)-2 for f in self.faces)
  return {'triangles':tri,'vertices_before_export':len(vs),'surfaces':len(set(self.mats)),'aabb_min':[min(v[i] for v in vs) for i in range(3)],'aabb_max':[max(v[i] for v in vs) for i in range(3)],'snow_exposed_faces':sum(c[3]>0 for c in self.cols),'sheltered_faces':sum(c[3]==0 for c in self.cols)}
 def export(self,name):
  mesh=bpy.data.meshes.new(name); mesh.from_pydata([(v[0],-v[2],v[1]) for v in self.verts],[],self.faces);mesh.update()
  names=sorted(set(self.mats))
  for n in names:mesh.materials.append(MATS[n])
  color=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
  for poly,mat,col in zip(mesh.polygons,self.mats,self.cols):
   poly.material_index=names.index(mat)
   for li in poly.loop_indices:color.data[li].color=col
  # Primitive winding fixes are deterministic and offline only.
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
  bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
  ob['original_authoring']='Original offline procedural low-poly geometry';ob['units']='metres';ob['not_terrain_placed']=True
  bpy.ops.export_scene.gltf(filepath=OUT+'/models/'+name+'.glb',export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_attributes=True,export_vertex_color='ACTIVE',export_all_vertex_colors=False)
  ob.hide_set(True)

def onsen(detail):
 m=Mesh();m.box((0,.25,0),(16,.5,9),'stone',0);m.box((0,2.2,-.35),(14.5,3.4,6.7),'plaster',0)
 m.box((0,.68,3.5),(15.3,.34,2.3),'cedar',0)
 m.box((0,.15,4.8),(4,.3,.6),'stone',0);m.box((0,.15,5.3),(4,.3,.4),'stone',1);m.box((0,.38,4.55),(3.6,.45,.6),'stone',0)
 for x in [-7,-3.5,0,3.5,7]:
  m.box((x,2.05,3.2),(.22,3.4,.28),'cedar',0);m.box((x,2.05,-3.6),(.22,3.4,.25),'cedar',0)
 for y in [1.05,3.46]:m.box((0,y,3.18),(14.8,.20,.2),'cedar',0)
 for x in [-5.25,-1.8,1.8,5.25]:
  m.box((x,2.23,3.33),(2.9,1.72,.09),'charcoal',0)
  for k in range(5 if detail else 2):m.box((x-1.2+k*2.4/(4 if detail else 1),2.22,3.40),(.065,1.72,.065),'bamboo',0)
  m.box((x,2.2,3.43),(2.9,.065,.06),'bamboo',0)
 # Offset door interrupts the repeated bays, warm hanging split curtain, no logo.
 m.box((0,1.85,3.52),(2.5,2.35,.1),'cedar',0)
 for x in [-.61,.61]:m.box((x,2.45,3.62),(1.16,.96,.035),'vermilion',0,.88)
 m.box((0,3.02,3.65),(2.6,.12,.14),'bamboo',0)
 m.roof(0,0,17.1,10.2,3.9,6.0)
 if detail:
  for x in [-4,-2,0,2,4]:
   m.cylinder((x,4.02,5.02),(x,5.98,.06),.035,'charcoal',1,n=4,tint=1.08)
  for z in [1,2,3,4,5]:
   half=4.617+3.933*z/5.1;y=6-2.1*z/5.1+.025
   m.cylinder((-half,y,z),(half,y,z),.025,'charcoal',1,n=4,tint=1.05)
  for x in [-6.8,6.8]:
   m.box((x,1.37,4.0),(.75,1.1,.62),'bamboo',0);m.box((x,1.98,4.0),(.84,.13,.72),'charcoal',0)
 # Side slatted privacy service screen.
 for z in ([-2.6,-1.9,-1.2,-.5,.2,.9,1.6] if detail else [-2.2,-.4,1.4]):m.box((7.35,1.8,z),(.14,2.4,.16),'cedar',0)
 m.proxy('inn_solid',(0,2.05,-.4),(14.5,4.1,6.7))
 m.shelters=[{'position':[0,3.9,0],'size':[17.1,.25,10.2],'roof_top_y':6.215,'register_once':True}]
 return m

def bath(detail):
 m=Mesh();m.box((0,.16,0),(7,.32,5.5),'stone');m.box((0,.45,0),(5.4,.12,3.6),'water',0)
 for x,z in [(-3,0),(3,0)]:m.box((x,.6,z),(.5,1.2,5.2),'stone')
 for x,z in [(0,-2.4),(0,2.4)]:m.box((x,.6,z),(5.5,1.2,.5),'stone')
 if detail:
  for i in range(10):m.rock((-2.7+i*.6,.96,2.4),(.7,.38,.62))
  for i in range(7):m.rock((3,.96,-2+i*.65),(.6,.32,.7))
 m.box((0,1.5,-3.05),(7,2.6,.12),'cedar')
 for x in ([-3,-2,-1,0,1,2,3] if detail else [-3,0,3]):m.box((x,1.6,-2.94),(.1,2.8,.09),'bamboo')
 m.proxy('bath_boundary',(0,.85,0),(7,1.7,5.5));m.proxy('privacy_screen',(0,1.4,-3.0),(7,2.8,.3));return m

def shed(detail):
 m=Mesh();m.box((0,.18,0),(9.8,.36,7),'stone',0)
 for x in [-4.35,0,4.35]:
  for z in [-2.8,2.8]:m.box((x,2.2,z),(.28,4.1,.28),'cedar',0)
 m.box((0,1.75,-2.95),(9.1,3.2,.17),'cedar',0)
 for y in ([.7,1.4,2.1,2.8,3.5] if detail else [1.0,2.8]):m.box((0,y,-2.82),(9.2,.09,.08),'bamboo',0,.85)
 for x in [-4.35,4.35]:
  m.box((x,3.9,0),(.24,.22,6.6),'cedar',0)
  m.cylinder((x,2.85,2.8),(x,3.9,1.6),.10,'cedar',0,n=4)
 m.roof(0,0,11,8,4.15,5.3)
 m.proxy('back_wall',(0,1.85,-2.95),(9.2,3.7,.25))
 for x in [-4.35,0,4.35]:
  for z in [-2.8,2.8]:m.proxy('post_%s_%s'%(x,z),(x,2.1,z),(.4,4.2,.4))
 m.shelters=[{'position':[0,4.15,0],'size':[11,.25,8],'roof_top_y':5.515,'register_once':True}]
 return m

def logs(detail,rows=3):
 m=Mesh();r=.32
 for row in range(rows):
  for j in range(5-row):
   x=(j-(4-row)/2)*.68;y=.35+row*.57
   m.cylinder((x,y,-2.5),(x,y,2.5+(j%2)*.12),r,'cedar',1,n=8 if detail else 5,tint=.92+(j%3)*.07,end_mat='bamboo')
   if detail:m.cylinder((x,y,2.525+(j%2)*.12),(x,y,2.53+(j%2)*.12),.12,'cedar',0,n=6,tint=1.24)
 for z in [-1.85,1.85]:m.box((0,.15,z),(3.9,.3,.28),'charcoal')
 m.proxy('timber_pile',(0,(.68+rows*.57)/2,0),(3.6,.68+rows*.57,5.4));return m

def bench(detail):
 m=Mesh()
 for x in [-1.04,1.04]:
  m.box((x,.35,0),(.16,.7,.66),'charcoal');m.box((x,.93,-.25),(.12,1.2,.12),'charcoal')
 for z in ([-.25,0,.25] if detail else [0]):m.box((0,.72,z),(2.7,.11,.21 if detail else .72),'cedar')
 for y in ([1.0,1.25] if detail else [1.12]):m.box((0,y,-.30),(2.7,.18 if detail else .42,.12),'cedar')
 m.proxy('bench',(0,.7,0),(2.8,1.4,.8));return m

def rail(detail):
 m=Mesh()
 for x in [-1.5,1.5]:m.box((x,.7,0),(.14,1.4,.14),'charcoal')
 for y in [.5,1.23]:m.box((0,y,0),(3.0,.095,.095),'cedar')
 if detail:
  for x in [-.9,-.3,.3,.9]:m.box((x,.8,0),(.045,.62,.045),'charcoal')
 m.proxy('rail',(0,.7,0),(3.1,1.4,.2));return m

def deck(detail):
 m=Mesh();m.box((0,.25,0),(12,.5,8),'stone')
 for z in ([i*.29-3.77 for i in range(27)] if detail else [0]):m.box((0,.55,z),(11.7,.12,.275 if detail else 7.7),'cedar')
 # Assemble continuous rails once: shared posts must not duplicate coplanar faces.
 for x in [-5.9,-2.95,0,2.95,5.9]:m.box((x,1.3,-3.9),(.14,1.4,.14),'charcoal')
 for y in [1.1,1.83]:m.box((0,y,-3.9),(11.8,.095,.095),'cedar')
 for x in [-5.9,5.9]:
  for z in [-1.4,1.1,3.6]:m.box((x,1.3,z),(.14,1.4,.14),'charcoal')
  for y in [1.1,1.83]:m.box((x,y,-.15),(.095,.095,7.5),'cedar')
 if detail:
  for x in [-5.4+i*.6 for i in range(19)]:m.box((x,1.4,-3.9),(.045,.62,.045),'charcoal')
  for x in [-5.9,5.9]:
   for z in [-3.3+i*.6 for i in range(11)]:m.box((x,1.4,z),(.045,.62,.045),'charcoal')
 for x in [-3.7,3.7]:m.append(bench(detail),(x,.6,-2.45),math.pi)
 m.proxy('deck_platform',(0,.305,0),(12,.61,8))
 m.proxy('deck_back_rail',(0,1.3,-3.9),(12,1.4,.24))
 for x in [-5.9,5.9]:m.proxy('deck_side_rail',(x,1.3,-.15),(.24,1.4,7.5))
 return m

def sign(detail):
 m=Mesh()
 for x in [-1.2,1.2]:m.box((x,1.2,0),(.16,2.4,.16),'cedar')
 m.box((0,1.8,0),(2.8,1.65,.16),'cedar');m.box((0,1.8,.09),(2.55,1.4,.025),'plaster')
 # Readable as a contour/orientation map without claiming real labels.
 for pts in [[(-1,1.4),(-.5,2.1),(0,1.7),(.5,2.3),(1,1.5)],[(-1,1.25),(-.3,1.65),(.2,1.3),(.8,1.8)]]:
  for a,b in zip(pts,pts[1:]):m.cylinder((a[0],a[1],.115),(b[0],b[1],.115),.026,'field',0,n=4)
 m.proxy('map_sign',(0,1.3,0),(2.8,2.6,.3));return m

def shrine(detail):
 m=Mesh();m.box((0,.25,0),(6.5,.5,5),'stone',0);m.box((0,.65,0),(5.8,.3,4.6),'cedar',0)
 m.box((0,2.1,-.25),(4.8,2.65,3.6),'plaster',0)
 for x in [-2.4,-.8,.8,2.4]:m.box((x,2.1,1.6),(.18,2.85,.22),'cedar',0)
 m.box((0,2,1.74),(2.5,2.1,.10),'charcoal',0)
 for x in ([-1,-.6,-.2,.2,.6,1] if detail else [-1,0,1]):m.box((x,2,1.82),(.065,2.1,.06),'bamboo',0)
 for y in [1.05,2.95]:m.box((0,y,1.85),(4.9,.17,.2),'cedar',0)
 for i in range(3):m.box((0,.10+i*.13,2.7-i*.35),(2.8,.2+i*.26,.42),'stone',0)
 m.roof(0,0,7.2,6.4,3.6,5.25)
 # Restrained red beam accents, asymmetrical side shutter.
 m.box((0,3.3,1.78),(5.4,.14,.18),'vermilion',0)
 for x in [-2.65,2.65]:m.box((x,1.15,1.85),(.18,1.05,.18),'cedar',0)
 if detail:
  m.cylinder((-1.4,2.95,2.12),(1.4,2.95,2.12),.075,'bamboo',0,n=6)
  for x in [-.8,0,.8]:m.box((x,2.7,2.12),(.07,.38,.035),'plaster',0)
  for z in [-1.2,-.6,0,.6]:m.box((2.46,2,z),(.1,1.7,.07),'cedar',0)
 m.proxy('shrine_solid',(0,1.8,-.25),(4.9,3.6,3.7));m.shelters=[{'position':[0,3.6,0],'size':[7.2,.25,6.4],'roof_top_y':5.465,'register_once':True}];return m

def torii(detail):
 m=Mesh()
 for x in [-2.2,2.2]:
  m.cylinder((x,0,0),(x*.94,4.6,0),.21,'vermilion',1,n=8,r2=.17)
  m.cylinder((x,0,0),(x,.42,0),.28,'charcoal',1,n=8)
 m.box((0,3.55,0),(5.6,.27,.25),'vermilion');m.box((0,4.36,0),(6.25,.34,.40),'vermilion')
 m.box((0,4.6,0),(6.7,.17,.54),'charcoal')
 for s in [-1,1]:m.cylinder((s*2.8,4.62,0),(s*3.45,4.77,0),.12,'charcoal',1,n=4)
 m.box((0,4.0,0),(.25,.8,.25),'vermilion')
 m.box((0,4.0,.17),(.55,.65,.08),'cedar',0)
 for x in [-2.2,2.2]:m.proxy('torii_post',(x,2.3,0),(.6,4.6,.6))
 return m

def lantern(detail):
 m=Mesh();m.box((0,.15,0),(.9,.3,.9),'stone');m.cylinder((0,.3,0),(0,1.1,0),.19,'stone',1,n=6,r2=.15)
 m.box((0,1.16,0),(.65,.15,.65),'stone');m.box((0,1.5,0),(.48,.55,.48),'charcoal',0)
 for x in [-.24,.24]:
  for z in [-.24,.24]:m.box((x,1.5,z),(.09,.65,.09),'stone')
 m.roof(0,0,.95,.95,1.83,2.05,'stone');m.cylinder((0,2.05,0),(0,2.26,0),.13,'stone',1,n=6,r2=.03)
 return m

def paddy(detail):
 m=Mesh();m.box((0,-.08,0),(12,.16,8),'field');m.box((0,.055,0),(11,.09,7),'water')
 for x in [-5.75,5.75]:m.box((x,.16,0),(.5,.32,8),'field')
 for z in [-3.75,3.75]:m.box((0,.16,z),(11,.32,.5),'field')
 if detail:
  # 192 authored clumps; closed 8-triangle grass silhouettes, no runtime generation.
  for i in range(16):
   for j in range(12):
    x=-5+i*.66;z=-3.1+j*.56;h=.44+(i+j)%3*.045
    leaves=[([(x-.11,.10,z),(x+.11,.10,z),(x+.07,.10+h,z+.03),(x,.10,z+.04)],'field',1.12), ([(x,.10,z-.10),(x,.10,z+.10),(x-.04,.10+h*.88,z-.04),(x-.04,.10,z)],'field',1.0)]
    for pts,mat,tint in leaves:
     for f in [(0,1,2),(0,3,1),(1,3,2),(2,3,0)]:m.face([pts[k] for k in f],mat,1,tint)
 else:
  for i in range(8):m.box((-4.7+i*1.34,.17,0),(.24,.2,6.6),'field')
 return m

def bridge(detail,length=14,width=6.6):
 m=Mesh();m.box((0,-.31,0),(width,.5,length),'cedar')
 if not detail:m.box((0,-.03,0),(width,.06,length),'cedar')
 if detail:
  count=int(length/.36);spacing=length/count
  for i in range(count):m.box((0,-.03,-length/2+(i+.5)*spacing),(width-.12,.06,spacing-.025),'bamboo',1,.88+(i%3)*.045)
 for x in [-width/2+.12,width/2-.12]:
  m.box((x,.85,0),(.14,.16,length),'cedar');m.box((x,1.35,0),(.17,.14,length),'cedar')
  for z in [-length/2+i*length/6 for i in range(7)]:m.box((x,.7,z),(.22,1.55,.22),'charcoal')
  m.box((x,-.6,0),(.3,.45,length),'charcoal')
 # Decorative bridge has NO driveable collision. Single owner bridge slab is a separate disabled template.
 m.proxy('bridge_support_template',(0,-.28,0),(width,.56,length));m.proxies[-1]['vehicle_surface']=True
 m.proxies[-1]['disabled_until_verified']=True
 for x in [-width/2+.12,width/2-.12]:m.proxy('bridge_rail',(x,.8,0),(.28,1.6,length))
 return m

BUILDERS={'onsen_inn':onsen,'onsen_bath':bath,'forestry_shed':shed,'timber_stack':logs,'timber_stack_low':lambda d:logs(d,1),'timber_stack_high':lambda d:logs(d,4),'viewpoint_deck':deck,'bench':bench,'rail_3m':rail,'map_sign':sign,'shrine_hall':shrine,'torii':torii,'stone_lantern':lantern,'paddy_tile':paddy,'timber_bridge_14m':bridge,'country_bridge_9m':lambda d:bridge(d,9,6.1)}
PACKS={
 'onsen_assembly':[('onsen_inn',(0,0,0),0),('onsen_bath',(12.3,0,-.5),0),('bench',(-7,0,6),0),('map_sign',(9.2,0,6),-.3)],
 'forestry_assembly':[('forestry_shed',(0,0,-4),0),('timber_stack_low',(-8.5,0,2),math.pi/2),('timber_stack',(7.6,0,1.8),0),('timber_stack_high',(7.6,0,-4.8),0)],
 'viewpoint_assembly':[('viewpoint_deck',(0,0,0),0),('map_sign',(0,.6,-2.8),0)],
 'shrine_fields_assembly':[('shrine_hall',(0,0,-7),0),('torii',(0,0,1),0),('stone_lantern',(-3.2,0,-1.5),0),('stone_lantern',(3.2,0,-1.5),0),('paddy_tile',(-11,0,1),0),('paddy_tile',(11,0,1),0),('paddy_tile',(-11,0,10),0),('paddy_tile',(11,0,10),0)]}
manifest={'schema':1,'name':'Fuji foothill destination modules','version':'0.1.0-guarded','units':'metres','front_axis':'+Z','up_axis':'+Y','placement_status':'LOCAL ASSET STAGING ONLY; NOT WORLD PLACEMENT','palette_color_space':'sRGB; Blender/GLB factors convert to linear, Godot source_color uniforms use sRGB','materials':PALETTE,'modules':{},'assemblies':{},'provenance':{'geometry':'Original authored mathematical primitives and low-poly mesh construction in source/build_assets.py','third_party_assets':[],'paid_generation':False,'reference':'Approved Fuji masterplan v3 for setting and constraints; no pixels copied into textures','license':'Original project work; no external asset license restrictions introduced'},'integration_gate':['No world terrain/road ownership changes','Do not enable collision until terrain support and ownership verified','Register exactly 3 rectangular shelters if all three buildings active; global system cap remains 16','Bind weather to project climate only through later adapter; visual shader has no physics effects','Android performance and actual driving still required']}
cache={}
for detail in [True,False]:
 lod=0 if detail else 1
 for name,fn in BUILDERS.items():
  m=fn(detail);cache[(name,lod)]=m;m.export(name+'_lod'+str(lod))
  if lod==0:manifest['modules'][name]={'lods':{},'collision_proxies':m.proxies,'shelters':m.shelters,'origin_note':'Base at y=0; bridge continuous support template and board top y=0; paddy base extends -0.16m'}
  manifest['modules'][name]['lods'][str(lod)]=dict(m.stats(),file='models/'+name+'_lod'+str(lod)+'.glb')
 for name,items in PACKS.items():
  m=Mesh()
  for model,pos,yaw in items:m.append(cache[(model,lod)],pos,yaw)
  m.export(name+'_lod'+str(lod))
  if lod==0:manifest['assemblies'][name]={'lods':{},'visual_only':True,'layout':[{'module':a,'position':b,'yaw':c} for a,b,c in items]}
  manifest['assemblies'][name]['lods'][str(lod)]=dict(m.stats(),file='models/'+name+'_lod'+str(lod)+'.glb')
with open(OUT+'/asset_manifest.json','w') as f:json.dump(manifest,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/source/fuji_destination_library.blend')
print('ASSET_BUILD_COMPLETE',json.dumps({k:v['lods']['0']['triangles'] for k,v in manifest['assemblies'].items()}))

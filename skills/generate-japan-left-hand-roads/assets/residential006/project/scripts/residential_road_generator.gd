@tool
class_name ResidentialRoadGenerator
extends Node3D
## Reusable, data-driven road surface builder. All dimensions are metres.
## Inputs: Curve3D centreline, road/footway dimensions, driveway stations, and
## an optional height Callable(x,z). Top surfaces and colliders share exact faces.
## v1 supports a non-self-intersecting residential street with simple side drives.
## General intersections, road-road joining and automatic parcel planning are out of scope.
var samples: Array = []
var options: Dictionary = {}
var surfaces: Dictionary = {}
var metrics: Dictionary = {}
var port_faces: Dictionary = {}
var _triangles: Dictionary = {}
var _normals: Dictionary = {}
var _materials: Dictionary = {}

func build(config: Dictionary, height_sampler: Callable = Callable()) -> Dictionary:
 for child in get_children():
  remove_child(child)
  child.free()
 options=config.duplicate(true)
 samples=[];surfaces={};_triangles={};_normals={};port_faces={}
 var curve: Curve3D=options.curve
 var length=curve.get_baked_length()
 var spacing=float(options.get('sample_spacing',.4))
 var count=int(ceil(length/spacing))
 for i in count+1:
  var station=length*float(i)/count
  var p=curve.sample_baked(station,true)
  var before=curve.sample_baked(maxf(0.,station-.1),true)
  var after=curve.sample_baked(minf(length,station+.1),true)
  var forward=(after-before)*Vector3(1,0,1)
  assert(forward.length()>.00001,'Degenerate centreline tangent')
  forward=forward.normalized()
  if height_sampler.is_valid():p.y=float(height_sampler.call(p.x,p.z))
  samples.append({'p':p,'forward':forward,'right':forward.cross(Vector3.UP),'s':station})
 if height_sampler.is_valid():
  var raw=samples.duplicate(true)
  var smoothing=float(options.get('grade_smoothing_m',4.))
  for i in samples.size():
   var y=0.;var wsum=0.
   for j in range(maxi(0,i-int(ceil(smoothing/spacing))),mini(samples.size(),i+int(ceil(smoothing/spacing))+1)):
    var w=maxf(0.,1.-absf(float(raw[j].s)-float(raw[i].s))/smoothing)
    y+=raw[j].p.y*w;wsum+=w
   samples[i].p.y=y/maxf(wsum,.00001)
 # Insert all opening and ramp stations so dimension changes cannot skip a sample.
 var inserts=[]
 for d in options.get('driveways',[]):
  for off in [-d.width/2.-options.curb_ramp_length,-d.width/2.,0.,d.width/2.,d.width/2.+options.curb_ramp_length]:
   var s=clampf(float(d.station)+off,0.,length)
   var row=at(s)
   if not samples.any(func(a):return absf(float(a.s)-s)<.00001) and not inserts.any(func(a):return absf(float(a.s)-s)<.00001):inserts.append(row)
 samples.append_array(inserts)
 samples.sort_custom(func(a,b):return a.s<b.s)
 _make_materials()
 var half=float(options.road_width)*.5
 for i in samples.size()-1:
  var a=samples[i];var b=samples[i+1]
  _ribbon('asphalt',a,b,-half,0.,0)
  _ribbon('asphalt',a,b,0.,half,0)
  for side in [-1,1]:
   var sw=sidewalk_width(side)
   if sw>0.:
    _ribbon('footway',a,b,float(side)*half,float(side)*(half+sw),1)
    _curb(a,b,float(side)*half,side)
    _outer_face(a,b,float(side)*(half+sw),side)
   else:
    var blocked=false
    for port in options.get('driveways',[]):
     if int(port.side)==side and absf((float(a.s)+float(b.s))*.5-float(port.station))<float(port.width)*.5:blocked=true
    if not blocked:_ribbon('shoulder',a,b,float(side)*half,float(side)*(half+float(options.get('shoulder_width',.3))),0)
 for d in options.get('driveways',[]):
  var side=int(d.side);var start=half+sidewalk_width(side);var end=half+float(d.length)
  assert(end>start and d.width>0.,'A driveway must extend beyond its footway')
  # Reuse the exact street edge stations. Curved ports therefore share vertices,
  # rather than laying an independently sampled driveway on top of the road.
  var before_count=_triangles.get('driveway',PackedVector3Array()).size()
  var rows=[]
  for row in samples:
   if float(row.s)>=float(d.station)-float(d.width)*.5-.00001 and float(row.s)<=float(d.station)+float(d.width)*.5+.00001:rows.append(row)
  var along=maxi(2,int(ceil((end-start)/spacing)))
  for j in rows.size()-1:
   for k in along:
    var u=float(k)/along;var v=float(k+1)/along
    _quad('driveway',connector_point(rows[j],u,d),connector_point(rows[j+1],u,d),connector_point(rows[j+1],v,d),connector_point(rows[j],v,d))
  port_faces[str(d.id)]=_triangles.driveway.slice(before_count)
 var collision_identical=true;var vertex_count=0
 for kind in _triangles:
  var arr=[];arr.resize(Mesh.ARRAY_MAX)
  arr[Mesh.ARRAY_VERTEX]=_triangles[kind];arr[Mesh.ARRAY_NORMAL]=_normals[kind]
  var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arr);mesh.surface_set_material(0,_materials[kind])
  var mi=MeshInstance3D.new();mi.name=kind;mi.mesh=mesh;add_child(mi);mi.owner=self
  var body=StaticBody3D.new();body.name=kind+'_support';body.collision_layer=1;body.collision_mask=0;body.set_meta('world_surface',kind);add_child(body);body.owner=self
  var cs=CollisionShape3D.new();cs.name='ExactVisibleTriangles';cs.shape=mesh.create_trimesh_shape();body.add_child(cs);cs.owner=self
  assert(cs.shape.get_faces()==mesh.get_faces(),'Visual/collision geometry mismatch')
  surfaces[kind]=mi;vertex_count+=mesh.get_faces().size()
 var max_grade=0.
 for i in samples.size()-1:max_grade=maxf(max_grade,absf(samples[i+1].p.y-samples[i].p.y)/maxf(.00001,samples[i+1].s-samples[i].s))
 metrics={'length_m':length,'stations':samples.size(),'road_width_m':options.road_width,'left_footway_width_m':sidewalk_width(-1),'right_footway_width_m':sidewalk_width(1),'curb_height_m':options.curb_height,'opening_ramp_length_m':options.curb_ramp_length,'driveway_count':options.get('driveways',[]).size(),'visible_and_collision_faces_identical':collision_identical,'triangles':vertex_count/3,'max_longitudinal_grade_percent':max_grade*100.,'surface_types':surfaces.keys(),'scope':'Single residential centreline and simple side drives; no general intersections, junction unions or streaming integration'}
 return metrics

func at(station: float) -> Dictionary:
 var s=clampf(station,0.,float(samples[-1].s))
 for i in samples.size()-1:
  if s<=float(samples[i+1].s)+.000001:
   var a=samples[i];var b=samples[i+1];var t=(s-float(a.s))/maxf(.000001,float(b.s)-float(a.s))
   var f=a.forward.lerp(b.forward,t).normalized()
   return {'s':s,'p':a.p.lerp(b.p,t),'forward':f,'right':f.cross(Vector3.UP)}
 return samples[-1].duplicate()

func sidewalk_width(side: int) -> float:
 return float(options.get('left_footway_width' if side<0 else 'right_footway_width',0.))
func road_height(row: Dictionary,lateral: float) -> float:
 return row.p.y-absf(lateral)*float(options.get('road_crossfall',.015))
func point(row: Dictionary,lateral: float,y: float) -> Vector3:
 var p: Vector3=row.p+row.right*lateral;p.y=y;return p
func drive_height(row: Dictionary,lateral: float,d: Dictionary) -> float:
 var half=float(options.road_width)*.5;var start=road_height(row,half)
 var center=at(float(d.station))
 var end=float(d.end_height)+(row.p.y-center.p.y)
 return lerpf(start,end,clampf((absf(lateral)-half)/float(d.length),0.,1.))
func connector_point(row: Dictionary,t: float,d: Dictionary) -> Vector3:
 var side=float(d.side);var half=float(options.road_width)*.5;var width=sidewalk_width(int(side))
 var lateral=side*(half+width)
 var start=point(row,lateral,drive_height(row,lateral,d))
 if not d.has('end_position'):
  var l=side*lerpf(half+width,half+float(d.length),t)
  return point(row,l,drive_height(row,l,d))
 var center=at(float(d.station));var forward: Vector3=d.get('end_forward',center.right*side)
 forward=(forward*Vector3(1,0,1)).normalized()
 var across=forward.cross(Vector3.UP)*(-side)
 var offset=float(row.s)-float(d.station)
 var target: Vector3=d.end_position+across*offset
 # End port can sample an existing public-road edge or a building landing plane.
 target.y=float(d.end_height)+(float(row.p.y)-float(center.p.y))*float(d.get('end_grade_inherit',0.))
 if d.has('end_height_sampler'):target.y=float(d.end_height_sampler.call(target.x,target.z))
 var run=start.distance_to(target)
 var p1=start+row.right*side*run*.34;var p2=target-forward*run*.34
 var p=start*(1.-t)*(1.-t)*(1.-t)+p1*3.*t*(1.-t)*(1.-t)+p2*3.*t*t*(1.-t)+target*t*t*t
 p.y=lerpf(start.y,target.y,t)
 return p
func footway_height(row: Dictionary,lateral: float) -> float:
 var half=float(options.road_width)*.5
 var y=road_height(row,half)+float(options.curb_height)-(absf(lateral)-half)*float(options.get('footway_crossfall',.008))
 for d in options.get('driveways',[]):
  if signf(lateral)!=signf(float(d.side)):continue
  var dist=maxf(0.,absf(float(row.s)-float(d.station))-float(d.width)*.5)
  if dist>=float(options.curb_ramp_length):continue
  var t=clampf(dist/float(options.curb_ramp_length),0.,1.);t=t*t*(3.-2.*t)
  y=lerpf(drive_height(row,lateral,d),y,t)
 return y
func _ribbon(kind: String,a: Dictionary,b: Dictionary,l1: float,l2: float,mode: int):
 _quad(kind,point(a,l1,footway_height(a,l1) if mode==1 else road_height(a,l1)),point(b,l1,footway_height(b,l1) if mode==1 else road_height(b,l1)),point(b,l2,footway_height(b,l2) if mode==1 else road_height(b,l2)),point(a,l2,footway_height(a,l2) if mode==1 else road_height(a,l2)))
func _curb(a: Dictionary,b: Dictionary,l: float,side: int):
 _quad('curb',point(a,l,road_height(a,l)),point(b,l,road_height(b,l)),point(b,l,footway_height(b,l)),point(a,l,footway_height(a,l)),false,side)
func _outer_face(a: Dictionary,b: Dictionary,l: float,side: int):
 _quad('curb',point(a,l,road_height(a,options.road_width*.5)-.04),point(b,l,road_height(b,options.road_width*.5)-.04),point(b,l,footway_height(b,l)),point(a,l,footway_height(a,l)),false,-side)
func _quad(kind: String,a: Vector3,b: Vector3,c: Vector3,d: Vector3,up=true,side=1):
 _triangle(kind,a,b,c,up,side);_triangle(kind,a,c,d,up,side)
func _triangle(kind: String,a: Vector3,b: Vector3,c: Vector3,up=true,side=1):
 var n=-(b-a).cross(c-a)
 if n.length_squared()<1.e-12:return
 if (up and n.y<0.) or (not up and side<0):
  var tmp=b;b=c;c=tmp;n=-n
 if not _triangles.has(kind):_triangles[kind]=PackedVector3Array();_normals[kind]=PackedVector3Array()
 _triangles[kind].append_array(PackedVector3Array([a,b,c]));_normals[kind].append_array(PackedVector3Array([n.normalized(),n.normalized(),n.normalized()]))
func _make_materials():
 _materials={}
 for item in [['asphalt',Color(.12,.15,.16)],['footway',Color(.24,.235,.21)],['curb',Color(.32,.32,.29)],['driveway',Color(.20,.21,.19)],['shoulder',Color(.31,.30,.25)]]:
  var m=StandardMaterial3D.new();m.albedo_color=item[1];m.roughness=.95;m.cull_mode=BaseMaterial3D.CULL_DISABLED;_materials[item[0]]=m

## Returns the authored surface and the smoothed subgrade near this road.
## Terrain authoring can use this same profile to avoid burial/floating. It is
## not an automatic arbitrary-terrain remesher: the caller owns the terrain mesh.
func project_xz(x: float,z: float) -> Dictionary:
 var p=Vector3(x,0,z);var dist=INF;var station=0.;var closest=Vector3.ZERO
 for i in samples.size()-1:
  var a: Vector3=samples[i].p*Vector3(1,0,1);var b: Vector3=samples[i+1].p*Vector3(1,0,1)
  var t=clampf((p-a).dot(b-a)/maxf((b-a).length_squared(),.000001),0.,1.);var q=a.lerp(b,t);var d=p.distance_squared_to(q)
  if d<dist:
   dist=d;station=lerpf(samples[i].s,samples[i+1].s,t);closest=q
 var row=at(station)
 return {'row':row,'lateral':(p-closest).dot(row.right),'distance':sqrt(dist)}

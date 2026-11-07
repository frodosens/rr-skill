"""Real Geometry Nodes building previews. Python builds the node networks only.
Building base meshes are empty; all visible building geometry is produced by nodes.
No external plugin installation, no runtime generation, no claim of final game readiness.
"""
import bpy,bmesh,math,json,os,hashlib
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
PALETTE={'cedar':(.55,.39,.26,1),'charcoal':(.22,.29,.29,1),'plaster':(.86,.83,.73,1),'stone':(.48,.54,.48,1),'vermilion':(.70,.28,.16,1),'field':(.50,.59,.30,1),'water':(.36,.57,.55,1),'bamboo':(.67,.57,.36,1)}
M={}
for name,color in PALETTE.items():
 m=bpy.data.materials.new(name);m.diffuse_color=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in color[:3])+(1,);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.92;M[name]=m

def graph(store=False,detail=True):
 g=bpy.data.node_groups.new(('GN_Convenience_Store' if store else 'GN_Japanese_House')+('_LOD0' if detail else '_LOD1'),'GeometryNodeTree');g.is_modifier=True
 g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
 sockets={}
 for name,typ,val in [('Width','NodeSocketFloat',10.0),('Depth','NodeSocketFloat',7.0),('Floors','NodeSocketInt',1),('Floor Height','NodeSocketFloat',3.2),('Window Bays','NodeSocketInt',4),('Roof Rise','NodeSocketFloat',1.8),('Wall Material','NodeSocketMaterial',M['plaster'])]:
  s=g.interface.new_socket(name=name,in_out='INPUT',socket_type=typ);s.default_value=val
  limits={'Width':(14,18) if store else (6,12),'Depth':(8,10) if store else (6,10),'Floors':(1,1) if store else (1,2),'Floor Height':(3.1,3.5) if store else (2.8,3.3),'Window Bays':(4,6) if store else (2,4),'Roof Rise':(.5,.5) if store else (1.2,2.2)}
  if name in limits:s.min_value,s.max_value=limits[name]
  sockets[name]=s.identifier
 N=g.nodes;L=g.links;inp=N.new('NodeGroupInput');out=N.new('NodeGroupOutput');inp.location=(-1200,0);out.location=(1400,0)
 def n(t,label):a=N.new(t);a.label=label;a.name=label;return a
 def link(v,dst):
  if hasattr(v,'node'):L.new(v,dst)
  else:dst.default_value=v
 def mathn(op,a,b=0,label=''):
  z=n('ShaderNodeMath',label or op);z.operation=op;link(a,z.inputs[0]);link(b,z.inputs[1]);return z.outputs[0]
 def vec(x=0,y=0,z=0,label='Vector'):
  a=n('ShaderNodeCombineXYZ',label)
  for v,d in zip([x,y,z],a.inputs):link(v,d)
  return a.outputs[0]
 def trans(geo,xyz=(0,0,0),rot=(0,0,0),scale=(1,1,1),label='Place geometry'):
  a=n('GeometryNodeTransform',label);L.new(geo,a.inputs['Geometry']);link(xyz if hasattr(xyz,'node') else vec(*xyz),a.inputs['Translation']);a.inputs['Rotation'].default_value=rot;link(scale if hasattr(scale,'node') else vec(*scale),a.inputs['Scale']);return a.outputs['Geometry']
 def mat(geo,m):
  a=n('GeometryNodeSetMaterial','Assign shared material');L.new(geo,a.inputs['Geometry']);link(m if hasattr(m,'node') else M[m],a.inputs['Material']);return a.outputs[0]
 def exposure(geo,amount):
  a=n('GeometryNodeStoreNamedAttribute','Authored snow exposure');a.data_type='FLOAT_COLOR';a.domain='CORNER';a.inputs['Name'].default_value='Color';a.inputs['Value'].default_value=(1,1,1,amount);L.new(geo,a.inputs['Geometry']);return a.outputs['Geometry']
 def cube(size,at=(0,0,0),m='cedar',label='Primitive cube',snow=0):
  a=n('GeometryNodeMeshCube',label);link(size if hasattr(size,'node') else vec(*size),a.inputs['Size']);return trans(exposure(mat(a.outputs['Mesh'],m),snow),at,label=label+' position')
 def join(items,label='Join modules'):
  a=n('GeometryNodeJoinGeometry',label)
  for item in items:L.new(item,a.inputs['Geometry'])
  return a.outputs[0]
 W=inp.outputs['Width'];D=inp.outputs['Depth'];F=inp.outputs['Floors'];FH=inp.outputs['Floor Height'];B=inp.outputs['Window Bays'];R=inp.outputs['Roof Rise']
 H=mathn('MULTIPLY',F,FH,'Total wall height');halfH=mathn('MULTIPLY',H,.5);halfW=mathn('MULTIPLY',W,-.5);halfD=mathn('MULTIPLY',D,-.5);pitch=mathn('DIVIDE',W,B,'Bay spacing');ww=mathn('MULTIPLY',pitch,.63,'Window width')
 base=cube(vec(mathn('ADD',W,.5),mathn('ADD',D,.5),.3),(0,0,.15),'stone','Foundation')
 body=cube(vec(W,D,H),vec(0,0,mathn('ADD',halfH,.3)),inp.outputs['Wall Material'],'Wall volume')
 # Window primitive itself is a node assembly, not a pre-authored external mesh.
 wh=2.2 if store else 1.45
 window=[cube(vec(ww,.09,wh),m='charcoal',label='Opaque window pane')]
 for factor in ([-.5,0,.5] if detail else []):window.append(cube((.07,.14,wh+.12),vec(mathn('MULTIPLY',ww,factor),-.05,0),'bamboo','Vertical mullion'))
 for dz in ([-wh/2,wh/2] if detail else []):window.append(cube(vec(mathn('ADD',ww,.12),.14,.07),(0,-.05,dz),'cedar','Window lintel'))
 window=join(window,'One parametric window')
 tag=n('GeometryNodeStoreNamedAttribute','Tag complete window for validation');tag.data_type='BOOLEAN';tag.domain='FACE';tag.inputs['Name'].default_value='is_window';tag.inputs['Value'].default_value=True;L.new(window,tag.inputs['Geometry']);window=tag.outputs['Geometry']
 row=n('GeometryNodeMeshLine','Horizontal window points');row.mode='OFFSET';L.new(B,row.inputs['Count']);L.new(vec(mathn('ADD',halfW,mathn('MULTIPLY',pitch,.5)),mathn('SUBTRACT',halfD,.08),1.65),row.inputs['Start Location']);L.new(vec(pitch,0,0),row.inputs['Offset'])
 # Explicit floor-level selections keep doors free without deleting upper windows.
 def windows_on_points(points,exclude=None,door_width=1.45,label='Window instances'):
  a=n('GeometryNodeInstanceOnPoints',label);L.new(points,a.inputs['Points']);L.new(window,a.inputs['Instance'])
  if exclude is not None:
   p=n('GeometryNodeInputPosition','Point position for door clearance');sep=n('ShaderNodeSeparateXYZ','Point axes');L.new(p.outputs[0],sep.inputs[0])
   distance=mathn('ABSOLUTE',mathn('SUBTRACT',sep.outputs['X'],exclude))
   clear=mathn('GREATER_THAN',distance,mathn('ADD',mathn('MULTIPLY',ww,.5),door_width*.5+.18),'Keep whole window clear of doorway')
   L.new(clear,a.inputs['Selection'])
  return a.outputs['Instances']
 full=windows_on_points(row.outputs['Mesh'],label='All windows of one floor')
 floors=n('GeometryNodeMeshLine','Upper floor points');floors.mode='OFFSET';L.new(mathn('MAXIMUM',mathn('SUBTRACT',F,1),1),floors.inputs['Count']);L.new(vec(0,0,FH),floors.inputs['Start Location']);L.new(vec(0,0,FH),floors.inputs['Offset'])
 stacked=n('GeometryNodeInstanceOnPoints','Upper floor facades');L.new(floors.outputs['Mesh'],stacked.inputs['Points']);L.new(full,stacked.inputs['Instance'])
 switch=n('GeometryNodeSwitch','Only buildings above one floor');switch.input_type='GEOMETRY';L.new(mathn('GREATER_THAN',F,1),switch.inputs['Switch']);L.new(stacked.outputs['Instances'],switch.inputs['True'])
 upper=switch.outputs['Output'];front=join([windows_on_points(row.outputs['Mesh'],0,label='Entry clear ground floor'),upper],'Front windows')
 serviceX=mathn('SUBTRACT',mathn('MULTIPLY',W,.5),2.5)
 back_ground=windows_on_points(row.outputs['Mesh'],mathn('MULTIPLY',serviceX,-1),1.2,'Service clear ground floor') if store else full
 back=trans(join([back_ground,upper]),rot=(0,0,math.pi),label='Rear facade facing outward')
 allfloors=join([full,upper]);ratio=mathn('DIVIDE',D,W);side=trans(allfloors,vec(mathn('MULTIPLY',mathn('SUBTRACT',W,D),.5),0,0),(0,0,math.pi/2),vec(ratio,1,1),'Right facade outward')
 left=trans(side,rot=(0,0,math.pi),label='Left facade facing outward')
 trims=[]
 for s in [-.5,.5]:
  trims.append(cube(vec(.18,.18,H),vec(mathn('MULTIPLY',W,s),mathn('SUBTRACT',halfD,.12),mathn('ADD',halfH,.3)),'cedar','Corner beam'))
  # Scale beam height with total height, not baked coordinates.
  trims[-1]=trans(trims[-1],scale=vec(1,1,1))
 door=cube((1.45,.15,2.35),vec(0,mathn('SUBTRACT',halfD,.19),1.475),'charcoal' if store else 'cedar','Entry door')
 overhang=.4 if store else .5
 covered=overhang-.15;outside=1.05-overhang
 step=join([cube((2.3,covered,.22),vec(0,mathn('SUBTRACT',halfD,(.15+overhang)/2),.11),'stone','Sheltered entry step'),cube((2.3,outside,.22),vec(0,mathn('SUBTRACT',halfD,(overhang+1.05)/2),.11),'stone','Exposed entry step',1)])
 if not store:
  # A closed hipped roof from an eight-vertex cube, deformed by position fields.
  # Top vertices collapse into a ridge; Merge by Distance removes the coincident pair.
  roofbox=n('GeometryNodeMeshCube','Roof control cube');L.new(vec(mathn('ADD',W,1.0),mathn('ADD',D,1.0),R),roofbox.inputs['Size'])
  pos=n('GeometryNodeInputPosition','Roof control positions');sep=n('ShaderNodeSeparateXYZ','Roof cube axes');L.new(pos.outputs[0],sep.inputs[0])
  top=mathn('GREATER_THAN',sep.outputs['Z'],0,'Top vertex selector')
  rx=mathn('MULTIPLY',sep.outputs['X'],mathn('SUBTRACT',1,mathn('MULTIPLY',top,.46)))
  ry=mathn('MULTIPLY',sep.outputs['Y'],mathn('SUBTRACT',1,top))
  setp=n('GeometryNodeSetPosition','Hip and ridge field deformation');L.new(roofbox.outputs['Mesh'],setp.inputs['Geometry']);L.new(vec(rx,ry,sep.outputs['Z']),setp.inputs['Position'])
  merge=n('GeometryNodeMergeByDistance','Weld collapsed ridge vertices');merge.inputs['Distance'].default_value=.0001;L.new(setp.outputs['Geometry'],merge.inputs['Geometry'])
  roof=trans(exposure(mat(merge.outputs['Geometry'],'charcoal'),1),vec(0,0,mathn('ADD',mathn('ADD',H,.3),mathn('MULTIPLY',R,.5))),label='Place closed hip roof')
  fascia=cube(vec(mathn('ADD',W,1.0),mathn('ADD',D,1.0),.16),vec(0,0,mathn('ADD',H,.28)),'charcoal','Roof eave fascia')
  roof=join([roof,fascia],'Roof and eave')
  ridge=cube(vec(mathn('MULTIPLY',mathn('ADD',W,1.0),.54),.20,.20),vec(0,0,mathn('ADD',mathn('ADD',H,.36),R)),'charcoal','Ridge cap',1)
  curtain=cube((1.5,.04,.65),vec(0,mathn('SUBTRACT',halfD,.30),2.55),'vermilion','Entry curtain')
  parts=[base,body,front,back,side,left,door,step,roof,ridge,curtain]+trims
 else:
  roof=cube(vec(mathn('ADD',W,.8),mathn('ADD',D,.8),.3),vec(0,0,mathn('ADD',H,.45)),'charcoal','Flat shop roof',1)
  fascia=cube(vec(mathn('ADD',W,.5),.35,.7),vec(0,mathn('SUBTRACT',halfD,.24),mathn('ADD',H,.3)),'plaster','Shop fascia',1)
  stripe=cube(vec(mathn('ADD',W,.52),.38,.17),vec(0,mathn('SUBTRACT',halfD,.26),mathn('ADD',H,.55)),'water','Unbranded accent stripe')
  text=n('GeometryNodeStringToCurves','Editable store label');text.inputs['String'].default_value='STORE';text.inputs['Size'].default_value=.55
  real=n('GeometryNodeRealizeInstances','Realize label curves');L.new(text.outputs['Curve Instances'],real.inputs[0]);fill=n('GeometryNodeFillCurve','Fill label');L.new(real.outputs[0],fill.inputs[0]);letter=trans(exposure(mat(fill.outputs[0],'charcoal'),0),vec(-1.25,mathn('SUBTRACT',halfD,.44),mathn('ADD',H,.02)),(math.pi/2,0,0),label='Position store lettering')
  backD=mathn('MULTIPLY',D,.5)
  service=cube((1.2,.15,2.1),vec(serviceX,mathn('ADD',backD,.12),1.35),'cedar','Rear service door')
  rearstep=join([cube((1.8,.25,.22),vec(serviceX,mathn('ADD',backD,.275),.11),'stone','Covered service step'),cube((1.8,.65,.22),vec(serviceX,mathn('ADD',backD,.725),.11),'stone','Exposed service step',1)])
  parts=[base,body,front,back,side,left,door,step,roof,fascia,stripe,service,rearstep]+([letter] if detail else [])
 result=join(parts,'Complete node generated building');real=n('GeometryNodeRealizeInstances','Realize for preview and future export');L.new(result,real.inputs[0]);L.new(real.outputs[0],out.inputs['Geometry'])
 # Arrange a navigable node graph with semantic labels for review.
 for i,a in enumerate([a for a in N if a not in [inp,out]]):a.location=(-900+(i%12)*210,650-(i//12)*190)
 return g,sockets

OUT=ROOT+'/project/assets/fuji_destinations'
os.makedirs(OUT+'/models',exist_ok=True)
PARAMS=[('house_a_single',False,{'Width':8,'Depth':6,'Floors':1,'Floor Height':3.1,'Window Bays':3,'Roof Rise':1.7,'Wall Material':M['plaster']}),('house_b_two_floor',False,{'Width':9,'Depth':7,'Floors':2,'Floor Height':3.0,'Window Bays':3,'Roof Rise':1.7,'Wall Material':M['plaster']}),('house_c_timber',False,{'Width':7,'Depth':7.5,'Floors':2,'Floor Height':2.8,'Window Bays':3,'Roof Rise':1.6,'Wall Material':M['cedar']}),('convenience_store',True,{'Width':16,'Depth':8,'Floors':1,'Floor Height':3.1,'Window Bays':6,'Roof Rise':.5,'Wall Material':M['plaster']})]
GRAPHS={(store,lod):graph(store,lod==0) for store in (False,True) for lod in (0,1)}
manifest={'schema':1,'name':'Fuji Geometry Nodes modular buildings','version':'0.2.0-guarded','units':'metres','up_axis':'+Y','front_axis':'+Z','placement_status':'UNPLACED ASSETS; NO WORLD ACCEPTANCE','materials':PALETTE,'modules':{},'assemblies':{},'provenance':{'geometry':'Original Blender Geometry Nodes, authored offline with Python-created node graphs. No external model or texture.','runtime_geometry_nodes':False,'source_sha256':hashlib.sha256(open(__file__,'rb').read()).hexdigest()}}
proof={'blender_version':bpy.app.version_string,'graphs':{},'modules':{},'tests':[]}
contracts={'status':'EXPORTED LOCAL GLB; ENGINE/SCENE ACCEPTANCE SEPARATE','units':'metres','axes':'Godot/glTF +Y up; +Z front','modules':{}}
for (st,lod),(g,sockets) in GRAPHS.items():proof['graphs'][g.name]={'nodes':len(g.nodes),'links':len(g.links),'socket_ids':sockets}
all_sources=[]

def evaluate(ob):
 bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();return bpy.data.meshes.new_from_object(ob.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)

def bounds(mesh):
 p=[tuple(v.co) for v in mesh.vertices];lo=[min(q[i] for q in p) for i in range(3)];hi=[max(q[i] for q in p) for i in range(3)]
 return [lo[0],lo[2],-hi[1]],[hi[0],hi[2],-lo[1]]

def check_door_clearance(mesh,params,store):
 attr=mesh.attributes.get('is_window');assert attr and attr.domain=='FACE'
 # Check actual evaluated window faces, including trim, against actual doorway rectangles.
 W,D=params['Width'],params['Depth'];checks=0
 for face in mesh.polygons:
  if not attr.data[face.index].value:continue
  pts=[mesh.vertices[i].co for i in face.vertices];xs=[v.x for v in pts];ys=[v.y for v in pts];zs=[v.z for v in pts]
  for doorx,side,width,top in [(0,-1,1.45,2.65)]+([(W/2-2.5,1,1.2,2.4)] if store else []):
   if not all(side*y>D/2+.001 for y in ys):continue
   if min(zs)>=top or max(zs)<=.3:continue
   overlap=min(max(xs),doorx+width/2)-max(min(xs),doorx-width/2)
   assert overlap<=1e-5,(ob.name,'window intersects doorway',overlap)
   checks+=1
 assert checks>0
 return checks

for name,store,params in PARAMS:
 W,D=params['Width'],params['Depth'];H=params['Floors']*params['Floor Height'];overhang=.4 if store else .5
 data={'lods':{},'collision_proxies':[{'name':'DISABLED_building_solid','position':[0,(H+.3)/2,0],'size':[W,H+.3,D],'kind':'box','vehicle_surface':False}],'shelters':[],'origin_note':'Local base y0, +Z entry; preview transforms excluded'}
 for lod in (0,1):
  g,sockets=GRAPHS[(store,lod)];inp=bpy.data.meshes.new(name+'_empty_input');ob=bpy.data.objects.new(name+'_gn_lod'+str(lod),inp);bpy.context.collection.objects.link(ob);mod=ob.modifiers.new('Geometry Nodes original source','NODES');mod.node_group=g
  for key,value in params.items():mod[sockets[key]]=value
  all_sources.append(ob);mesh=evaluate(ob);checks=check_door_clearance(mesh,params,store);proof['tests'].append({'test':'evaluated_door_window_exclusion','module':name,'lod':lod,'checked_faces':checks,'passed':True})
  # Remove zero-area faces created by the roof ridge weld, then recalculate winding.
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update();mesh.calc_loop_triangles()
  color=mesh.color_attributes.get('Color');assert color and color.domain=='CORNER';mesh.color_attributes.active_color=color
  for poly in mesh.polygons:
   poly.use_smooth=False
   # Roof underside never receives snow even if its parent component is exposed.
   if poly.normal.z<.18:
    for li in poly.loop_indices:color.data[li].color=(1,1,1,0)
  for value in color.data:assert value.color[3] in (0,1)
  lo,hi=bounds(mesh);snowfaces=sum(color.data[p.loop_start].color[3]>.5 for p in mesh.polygons)
  filename=name+'_lod'+str(lod)+'.glb';stat={'file':'models/'+filename,'triangles':len(mesh.loop_triangles),'surfaces':len({p.material_index for p in mesh.polygons}),'aabb_min':lo,'aabb_max':hi,'snow_exposed_faces':snowfaces}
  data['lods'][str(lod)]=stat
  baked=bpy.data.objects.new(name+'_lod'+str(lod),mesh);bpy.context.collection.objects.link(baked);bpy.ops.object.select_all(action='DESELECT');baked.select_set(True);bpy.context.view_layer.objects.active=baked
  bpy.ops.export_scene.gltf(filepath=OUT+'/models/'+filename,export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_attributes=True,export_vertex_color='ACTIVE',export_all_vertex_colors=False)
  bpy.data.objects.remove(baked,do_unlink=True);bpy.data.meshes.remove(mesh)
  ob.hide_set(True);ob.hide_render=True
  proof['modules'][ob.name]={'input_vertices':len(inp.vertices),'modifier_type':mod.type,'graph':g.name,'parameters':{k:(v.name if hasattr(v,'name') else v) for k,v in params.items()},'lod_stats':stat}
 assert data['lods']['1']['triangles']<data['lods']['0']['triangles']
 assert data['lods']['0']['triangles']<=(2800 if store else 2000)
 assert data['lods']['1']['triangles']<=(900 if store else 600)
 roof_top=data['lods']['0']['aabb_max'][1]
 data['shelters']=[{'position':[0,H+.3,0],'size':[W+2*overhang,.25,D+2*overhang],'roof_top_y':roof_top,'register_once':True,'status':'Descriptor only, not registered; verify total active capacity and world transform'}]
 manifest['modules'][name]=data
 contracts['modules'][name]={'aabb_min_godot':data['lods']['0']['aabb_min'],'aabb_max_godot':data['lods']['0']['aabb_max'],'front_entry_center_godot':[0,1.475,D/2+.19],'outer_step_front_godot':[0,.22,D/2+1.05],'foundation_top_y':.3,'door_width':1.45,'loading_anchor':{'door_center_godot':[W/2-2.5,1.35,-D/2-.12],'outer_step_front_godot':[W/2-2.5,.22,-D/2-1.05],'width':1.2,'height':2.1,'outward_axis':'-Z'} if store else None,'parameters':{k:(v.name if hasattr(v,'name') else v) for k,v in params.items()},'lods':data['lods'],'shelters':data['shelters'],'collision':'Disabled box template; enable only under scene collision owner','site_placement':None}
# Actual parameter update on the retained source graph: 8m to12m then restore.
ob=all_sources[0];mod=ob.modifiers[0];sid=GRAPHS[(False,0)][1]['Width'];m=evaluate(ob);lo,hi=bounds(m);before=hi[0]-lo[0];bpy.data.meshes.remove(m);mod[sid]=12;ob.update_tag();m=evaluate(ob);lo,hi=bounds(m);after=hi[0]-lo[0];bpy.data.meshes.remove(m);mod[sid]=8;ob.update_tag();bpy.context.view_layer.update();assert abs(after-before-4)<1e-5
proof['tests'].append({'test':'Width8_to12_then_restore','width_before':before,'width_after':after,'passed':True})
proof['status']='PASS_GEOMETRY_NODES_EVALUATION_EXPORT_ONLY'
json.dump(manifest,open(OUT+'/asset_manifest.json','w'),indent=2);json.dump(contracts,open(ROOT+'/evidence/module_contracts.json','w'),indent=2);json.dump(proof,open(ROOT+'/evidence/geometry_nodes_proof.json','w'),indent=2)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/source/japanese_buildings_geometry_nodes_v2.blend')
print('GN_ASSET_BUILD_COMPLETE',json.dumps({n:{lod:d['triangles'] for lod,d in m['lods'].items()} for n,m in manifest['modules'].items()}))

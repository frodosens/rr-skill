import bpy,os,math,random,json
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
contract=json.load(open(ROOT+'/evidence/hotel_site_contract.json'))
assert contract.get('status')=='LOCAL MASSING DESIGN ONLY; WORLD TRANSFORM UNSET', 'Actual v3 build required before rendering'
bpy.ops.wm.open_mainfile(filepath=ROOT+'/source/hotel_massing.blend')
for o in bpy.context.scene.objects:o.hide_render=o.name!='hotel_compound_lod0';o.hide_set(False)
def point(v):return (v[0],-v[2],v[1])
def mat(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=.95;return m
road=mat('CONCEPT_only_asphalt',(.10,.13,.135,1));white=mat('CONCEPT_only_marking',(.75,.77,.68,1));grass=mat('CONCEPT_only_ground',(.34,.42,.24,1));path=mat('CONCEPT_only_walkway',(.38,.43,.36,1));trunk=mat('CONCEPT_tree_trunk',(.12,.085,.055,1));leafs=[mat('CONCEPT_tree_canopy_'+str(i),c) for i,c in enumerate([(.075,.15,.12,1),(.12,.22,.16,1),(.16,.27,.19,1)])]
def box(name,at,size,material):
 bpy.ops.mesh.primitive_cube_add(size=1,location=point(at));o=bpy.context.object;o.name=name;o.dimensions=(size[0],size[2],size[1]);o.data.materials.append(material);return o
box('CONCEPT_flat_study_ground',(0,-.12,15),(120,.2,130),grass)
box('CONCEPT_street_no_collision',(0,.025,23),(80,.10,6),road)
box('CONCEPT_opposite_parking_no_collision',(0,.035,39.5),(32,.12,19),road)
for x in [-14,14]:box('CONCEPT_parking_connection',(x,.04,29),(4,.12,6),road)
box('CONCEPT_entry_walk',(0,.08,17.1),(5,.12,5.8),path)
box('CONCEPT_crossing_walk',(0,.08,28),(2.8,.12,4),path)
loading=contract['loading_rect_xz']
box('CONCEPT_loading_area',((loading[0]+loading[1])/2,.035,(loading[2]+loading[3])/2),(loading[1]-loading[0],.12,loading[3]-loading[2]),road)
for z in [20.35+i*1.12 for i in range(6)]:box('CONCEPT_pedestrian_crossing',(0,.093,z),(4,.025,.55),white)
parking=contract['parking_design']
for row_index,(row_start,row_end) in enumerate(parking['stall_rows_z']):
 for center_x in parking['active_bay_centers_by_row'][row_index]:
  for edge_x in [center_x-1.4,center_x+1.4]:box('CONCEPT_active_stall_edge',(edge_x,.11,(row_start+row_end)/2),(.065,.025,5.5),white)
  box('CONCEPT_active_stall_end',(center_x,.11,row_start if row_index==0 else row_end),(2.8,.025,.07),white)
# Two central front bays removed: 2.8 m corridor plus 1.4 m buffers each side.
box('CONCEPT_reserved_no_parking_buffers',(0,.10,32.75),(5.6,.04,5.5),path)
box('CONCEPT_central_pedestrian_corridor',(0,.13,30.75),(2.8,.035,9.5),white)
# Current project blue car, generated from its real source, not a generic guessed scale.
old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=ROOT+'/models/current_blue_rally_reference.glb');new=set(bpy.data.objects)-old
rootcars=[o for o in new if o.parent not in new];carroot=rootcars[0]
placements=[tuple(p) for p in contract['parking_design']['preview_parked_cars_x_z_yaw']]+[tuple(parking['forecourt_scale_reference_x_z_yaw'])]
# Copy the imported object hierarchy while sharing mesh data.
def clone_tree(src,parent=None):
 o=src.copy();bpy.context.collection.objects.link(o);o.parent=parent
 for child in src.children:clone_tree(child,o)
 return o
for idx,(x,z,yaw) in enumerate(placements):
 o=carroot if idx==0 else clone_tree(carroot);o.location=point((x,.10,z));o.rotation_euler=(0,0,-yaw)
r=random.Random(41);trees=[]
for z in range(-24,59,9):
 for x in [-36,43]:
  if 17<z<29:continue
  trees.append((x+r.uniform(-2,2),z+r.uniform(-2,2)))
for x in range(-36,45,8):
 for z in [-27,59]:trees.append((x+r.uniform(-2,2),z+r.uniform(-2,2)))
for x,z in trees:
 h=r.uniform(9,14);bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.25,depth=h*.65,location=point((x,h*.325,z)));bpy.context.object.data.materials.append(trunk);bpy.context.object.name='CONCEPT_existing_forest_placeholder'
 for j in range(3):
  radius=(3.5-j*.7)*r.uniform(.87,1.12);depth=h*.53;yc=h*.40+j*h*.18
  bpy.ops.mesh.primitive_cone_add(vertices=7,radius1=radius,radius2=.08,depth=depth,location=point((x,yc,z)));o=bpy.context.object;o.name='CONCEPT_existing_forest_placeholder';o.data.materials.append(leafs[r.randrange(3)])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=False;scene.render.resolution_x=1440;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.73,.79,.79,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
bpy.ops.object.light_add(type='SUN',location=(0,0,30));sun=bpy.context.object;sun.rotation_euler=(.5,-.35,-.6);sun.data.energy=1.6;sun.data.angle=.12
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
shots=[('hotel_street_parking_forest_massing',(95,85,125),(0,2,12),110),('hotel_roadside_vehicle_scale',(38,15,61),(0,4,4),69)]
for name,eye,target,scale in shots:
 cam.location=point(eye);cam.rotation_euler=(Vector(point(target))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=ROOT+'/renders/'+name+'.png';bpy.ops.render.render(write_still=True)
json.dump({'status':'Unplaced design massing; conceptual flat ground/street/parking/forest placeholders only','samples':16,'threads':2,'car_dimensions_file':'evidence/vehicle_reference_dimensions.json','hotel_dimensions_file':'evidence/hotel_site_contract.json','images':[s[0]+'.png' for s in shots],'limitations':['No actual terrain fit; candidate site has known grading conflicts','No road alignment changes, no physical collision, no driving acceptance','Forest trees are illustrative placeholders, not confirmed removals or plantings','Parking counts and lane widths are design dimensions, swept paths not tested']},open(ROOT+'/evidence/site_render_manifest.json','w'),indent=2)

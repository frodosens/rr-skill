"""Actual GLB re-import preview, no world placement. CPU only, two threads externally."""
import bpy,os,json,hashlib,math
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE=ROOT+'/project/assets/fuji_destinations'
manifest=json.load(open(BASE+'/asset_manifest.json'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
models={};model_hashes={};amount_nodes=[]
for name,data in manifest['modules'].items():
 for lod in [0,1]:
  key=name+'_lod'+str(lod);path=BASE+'/'+data['lods'][str(lod)]['file'];model_hashes[key]=hashlib.sha256(open(path,'rb').read()).hexdigest()
  old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=path);new=set(bpy.data.objects)-old;meshes=[o for o in new if o.type=='MESH'];assert len(meshes)==1
  models[key]=meshes[0];meshes[0].hide_render=True
# One explicit shared Blender material per palette, matching runtime Color.a exposure.
materials={}
for name,c in manifest['materials'].items():
 mat=bpy.data.materials.new('PREVIEW_'+name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');l.new(p.outputs['BSDF'],out.inputs['Surface']);p.inputs['Roughness'].default_value=.94
 vc=n.new('ShaderNodeVertexColor');vc.layer_name='Color';geom=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');l.new(geom.outputs['Normal'],sep.inputs[0])
 ramp=n.new('ShaderNodeMapRange');ramp.interpolation_type='SMOOTHSTEP';ramp.clamp=True;ramp.inputs['From Min'].default_value=.18;ramp.inputs['From Max'].default_value=.8;l.new(sep.outputs['Z'],ramp.inputs['Value'])
 mask=n.new('ShaderNodeMath');mask.operation='MULTIPLY';l.new(ramp.outputs['Result'],mask.inputs[0]);l.new(vc.outputs['Alpha'],mask.inputs[1])
 amount=n.new('ShaderNodeMath');amount.operation='MULTIPLY';l.new(mask.outputs[0],amount.inputs[0]);amount.inputs[1].default_value=0;amount_nodes.append(amount)
 mix=n.new('ShaderNodeMixRGB');l.new(amount.outputs[0],mix.inputs[0]);mix.inputs[1].default_value=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c[:3])+(1,);mix.inputs[2].default_value=(.88,.92,.89,1);l.new(mix.outputs[0],p.inputs['Base Color']);materials[name]=mat
for ob in models.values():
 for i,m in enumerate(ob.data.materials):ob.data.materials[i]=materials[m.name.split('.')[0]]
# Actual project blue-car visual for scale; presentation only.
carfile=os.path.abspath(ROOT+'/references/current_blue_rally_reference.glb')
old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=carfile);cars=list(set(bpy.data.objects)-old);car_roots=[o for o in cars if o.parent not in cars]
for o in car_roots:o.location=(11,-19,.02);o.rotation_euler.z=math.pi/2
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.location.z=-.025;floor.name='STUDIO_ONLY';fm=bpy.data.materials.new('STUDIO_FLOOR');fm.diffuse_color=(.55,.58,.43,1);floor.data.materials.append(fm)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=False;scene.render.resolution_x=1440;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.73,.79,.79,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
bpy.ops.object.light_add(type='SUN',location=(0,0,15));sun=bpy.context.object;sun.rotation_euler=(.5,-.35,-.6);sun.data.energy=1.6;sun.data.angle=.12
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
positions={'house_a_single':(-14,2,0),'house_b_two_floor':(0,3,0),'house_c_timber':(13,2,0),'convenience_store':(0,-14,0)}
receipts=[]
def render(tag,snow=0,lod=0,single=None,rear=False):
 for ob in models.values():ob.hide_render=True
 keys=[]
 for name,pos in positions.items():
  if single and single!=name:continue
  key=name+'_lod'+str(lod);ob=models[key];ob.hide_render=False;ob.location=(0,0,0) if single else pos;keys.append(key)
 for ob in cars:ob.hide_render=bool(single)
 for n in amount_nodes:n.inputs[1].default_value=snow
 fm.diffuse_color=(.76,.81,.78,1) if snow else (.55,.58,.43,1)
 if single:
  eye=(20,22,12) if rear else (20,-24,12);target=(0,0,1.5);scale=23
 else:eye=(42,-57,42);target=(0,-5,2);scale=51
 cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 path=ROOT+'/renders/'+tag+'.png';scene.render.filepath=path;bpy.ops.render.render(write_still=True)
 receipts.append({'image':tag+'.png','sha256':hashlib.sha256(open(path,'rb').read()).hexdigest(),'snow':snow,'lod':lod,'glb_sources':{k:model_hashes[k] for k in keys}})
render('01_buildings_day')
render('02_buildings_snow',1)
render('03_store_front_snow',1,single='convenience_store')
render('04_store_service_rear',0,single='convenience_store',rear=True)
render('05_buildings_lod1',0,lod=1)
json.dump({'renderer':'Blender Cycles CPU','samples':24,'input':'Actual re-imported GLB files, not original source objects','scope':'Studio actual geometry preview, no terrain or Godot GPU evidence','receipts':receipts},open(ROOT+'/evidence/render_manifest.json','w'),indent=2)
print('RENDER_COMPLETE',len(receipts))

#!/usr/bin/env python3
"""Create a tiny deterministic synthetic saved-surface fixture. Not project evidence."""
from pathlib import Path
import argparse,hashlib,json
from bundle_paths import fresh_output

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root):
    project=root/'project';base=project/'assets/world/fuji_v3';base.mkdir(parents=True)
    generation='synthetic-skill-fixture-v1';rows=[];resources=[]
    def rect(cid,ident,kind,x0,z0,x1,z1,y=0):
        name=ident+'_'+cid.replace(':','_')+'_asphalt.tscn'
        relative='assets/world/fuji_v3/'+name;path=project/relative
        # Native minimal flat visible/support surface; the two JSON triangles are
        # analytic fixture inputs, not a claimed native export of the real game.
        path.write_text('[gd_scene load_steps=3 format=3]\n\n'
          '[sub_resource type="PlaneMesh" id="Plane"]\nsize = Vector2(%s, %s)\n\n'
          '[sub_resource type="BoxShape3D" id="Support"]\nsize = Vector3(%s, 0.1, %s)\n\n'
          '[node name="SyntheticSupport" type="MeshInstance3D"]\n'
          'position = Vector3(%s, %s, %s)\nmesh = SubResource("Plane")\n\n'
          '[node name="Body" type="StaticBody3D" parent="."]\n\n'
          '[node name="Shape" type="CollisionShape3D" parent="Body"]\n'
          'position = Vector3(0, -0.05, 0)\nshape = SubResource("Support")\n'
          %(x1-x0,z1-z0,x1-x0,z1-z0,(x0+x1)/2,y,(z0+z1)/2))
        resource='res://'+relative;digest=sha(path)
        resources.append({'chunk_id':cid,'path':resource,'sha256':digest})
        vs=[[x0,y,z0],[x1,y,z0],[x1,y,z1],[x0,y,z1]]
        for index,tri in enumerate([[vs[0],vs[1],vs[2]],[vs[0],vs[2],vs[3]]]):
            rows.append({'generation_id':generation,'chunk_id':cid,'resource_path':resource,
                'resource_sha256':digest,'source_id':ident,'source_kind':kind,'triangle_index':index,
                'vertices':tri,'visual_support':True,'collision_owner':True})
    for x in [3,4]:
        for z in [-11,-10,-9]:rect(f'{x}:{z}','ground','terrain_ground',x*128,z*128,(x+1)*128,(z+1)*128)
    roads=[{'id':'paddy_lane','width':6.5,'points':[[420,0,-1380],[420,0,-1050]],'surface':'asphalt','bidirectional':True},
           {'id':'forest_return','width':6.5,'points':[[580,0,-1380],[580,0,-1050]],'surface':'asphalt','bidirectional':True}]
    for road in roads:
        x=road['points'][0][0];cx=int(x//128)
        for z in [-11,-10,-9]:rect(f'{cx}:{z}',road['id'],'road_surface',x-3.25,max(z*128,-1380),x+3.25,min((z+1)*128,-1050))
    triangles=root/'surface_triangles.jsonl'
    triangles.write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in rows))
    write(base/'layout_values.json',{'generation_id':generation,'roads':roads,'bridges':[]})
    write(base/'exclusions.json',{'polygons':[],'pois':[]})
    write(base/'surface_catalog.json',{'generation_id':generation,'resources':resources,
        'triangle_export':{'sha256':sha(triangles)},'validation_status':'SYNTHETIC_FIXTURE_ONLY',
        'world_acceptance_status':'NOT_APPLICABLE_SYNTHETIC_FIXTURE'})
    write(root/'fixture_manifest.json',{'synthetic':True,'source_generation':generation,
        'triangle_sha256':sha(triangles),'layout_sha256':sha(base/'layout_values.json'),
        'triangles':len(rows),'scope':'Tiny flat synthetic fixture. Not the G007 world, not independent source review, native road driving or GPU/phone proof.'})
    
    print(json.dumps({'fixture':str(root),'triangles':len(rows),'triangle_sha256':sha(triangles)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    build(fresh_output(p.parse_args().output))

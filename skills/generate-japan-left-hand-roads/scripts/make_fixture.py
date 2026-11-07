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
    roads=[{'id':'fixture_road','width':6.5,'points':[[8,0,64],[376,0,64]],'surface':'asphalt','bidirectional':True}]
    for x in range(3):rect(f'{x}:0','fixture_road','road_surface',max(8,x*128),60.75,min(376,(x+1)*128),67.25)
    # The actual other-road polygon interrupts paint, independent of broad masks.
    rect('0:0','junction_fixture','road_surface',98,58,106,70)
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
    rules={'schema_version':1,'generation':'synthetic-markings016-fixture','source_generation':generation,
        'layout_sha256':sha(base/'layout_values.json'),'triangle_sha256':sha(triangles),
        'protected_owner_ids':['2:0'],'routes':[{'road_id':'fixture_road','start_m':4.,'end_m':364.,'two_way_left_traffic_design':True}],
        'edge':{'enabled':True,'minimum_road_width_m':4.,'width_m':.15,'paint_center_inset_m':.30,'color_linear':[.70,.72,.75,1.]},
        'center':{'enabled':True,'minimum_road_width_m':6.,'width_m':.15,'dash_m':3.,'gap_m':5.,'phase_m':0.},
        'geometry':{'vertical_lift_m':.008,'junction_clearance_m':.75,'area_epsilon_m2':1e-9,'minimum_up_normal':.9,'maximum_unsupported_area_m2':.003}}
    write(root/'marking_rules016.json',rules)
    print(json.dumps({'fixture':str(root),'triangles':len(rows),'triangle_sha256':sha(triangles)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    build(fresh_output(p.parse_args().output))

#!/usr/bin/env python3
"""Run portable synthetic tests; optional Godot check is explicitly separate."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
def digests(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True,help='New/empty test work directory outside the skill')
    p.add_argument('--godot',help='Optional Godot binary: headless input/LOD checks only')
    a=p.parse_args()
    from bundle_paths import fresh_output
    work=fresh_output(a.output);before=digests(ROOT/'assets');checks=[]
    def run(script,*args,fail=False):
        cmd=[sys.executable,str(ROOT/'scripts'/script),*map(str,args)]
        result=subprocess.run(cmd,cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=120)
        (work/(str(len(checks))+'_'+script+'.log')).write_text(result.stdout)
        if (result.returncode==0)==fail:raise RuntimeError(f'Unexpected exit {result.returncode}: {cmd}\n{result.stdout[-3000:]}')
        checks.append({'command':script,'expected_failure':fail,'exit_code':result.returncode})
    run('test_output_guards.py','--output',work/'output-guards')
    for suffix in ['a','b']:
        run('generate_branching_trees.py','--output',work/('trees_'+suffix))
    assert digests(work/'trees_a')==digests(work/'trees_b'),'Tree determinism'
    run('generate_branching_trees.py','--output',work/'trees_a','--check')
    run('validate_tree_glbs.py','--input',work/'trees_a')
    run('bake_bare_forest_card.py','--output',work/'bare.svg')
    run('bake_bare_forest_card.py','--output',work/'bare.svg','--check')
    fixture=ROOT/'assets/fixture';project=fixture/'project';tri=fixture/'surface_triangles.jsonl'
    run('make_fixture.py','--output',work/'rebuilt_fixture')
    assert digests(work/'rebuilt_fixture')==digests(fixture),'Bundled fixture reproducibility'
    for suffix in ['a','b']:
        run('place_forest009.py','--project',project,'--frozen-project',project,'--triangles',tri,'--output',work/('forest_'+suffix))
    assert digests(work/'forest_a')==digests(work/'forest_b'),'Placement determinism'
    placements=json.loads((work/'forest_a/output/placements.json').read_text())
    assert len(placements['items'])>100 and set(i['kind'] for i in placements['items'])=={'tree','grass','rock','shrub'}
    for item in placements['items']:
        assert item['position'][1]<=min(item['support_height_range']) and item['owner'] in placements['target_chunks']
    run('build_ground_field011.py','--project',project,'--triangles',tri,'--output',work/'ground')
    from PIL import Image
    image=Image.open(work/'ground/project/assets/world/ground011/ground_field011.png')
    assert image.size==(512,768) and image.mode=='RGB'
    report=json.loads((work/'ground/evidence/field_report011.json').read_text());assert report['missing_pixels']==0 and not report['geometry_change'] and not report['collision_change']
    digest=hashlib.sha256(tri.read_bytes()).hexdigest()
    run('safety009.py','--project',project,'--triangles',tri,'--expected-triangle-sha256',digest,'--output',work/'safety')
    safety=json.loads((work/'safety/safety_report009.json').read_text());assert safety['probe_count']>100 and safety['summary']['signs']>0
    bad=work/'bad_triangles.jsonl';bad.write_bytes(tri.read_bytes()+b'\n')
    run('place_forest009.py','--project',project,'--frozen-project',project,'--triangles',bad,'--output',work/'bad_forest',fail=True)
    run('build_ground_field011.py','--project',project,'--triangles',bad,'--output',work/'bad_ground',fail=True)
    run('safety009.py','--project',project,'--triangles',bad,'--expected-triangle-sha256',digest,'--output',work/'bad_safety',fail=True)
    run('place_forest009.py','--project',project,'--frozen-project',project,'--triangles',tri,'--output',project/'forbidden',fail=True)
    assert digests(ROOT/'assets')==before,'Input assets modified'
    native={'status':'NOT_RUN','scope':'No Godot executable requested'}
    if a.godot:
        template=ROOT/'assets/grass_wind027/project';copy=work/'grass/project';shutil.copytree(template,copy)
        (work/'grass/evidence').mkdir();(work/'grass/captures').mkdir()
        home=work/'home';home.mkdir();env={**os.environ,'HOME':str(home),'XDG_DATA_HOME':str(home/'data'),'XDG_CACHE_HOME':str(home/'cache'),'XDG_CONFIG_HOME':str(home/'config')}
        result=subprocess.run([a.godot,'--headless','--path',str(copy),'--script','res://tools/test_grass.gd'],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        (work/'grass_headless.log').write_text(result.stdout)
        assert result.returncode==0,result.stdout[-4000:]
        native=json.loads((work/'grass/evidence/tests.json').read_text());assert native['status']=='PASS'
    result={'status':'PASS','commands':checks,'placement_count':len(placements['items']),'safety_signs':safety['summary']['signs'],'godot':native,'scope':'Synthetic local packaging, deterministic geometry, input hash rejection and optional headless grass invariants. No production world/native surface readback/rendering/driving/phone proof.'}
    (work/'smoke_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

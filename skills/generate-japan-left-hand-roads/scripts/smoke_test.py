#!/usr/bin/env python3
"""Exercise actual marking generation with tiny standalone synthetic inputs."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
from bundle_paths import fresh_output
ROOT=Path(__file__).resolve().parents[1]
def digests(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    work=fresh_output(p.parse_args().output);checks=[];fixture=ROOT/'assets/fixture';before=digests(fixture)
    def run(script,*args,fail=False):
        result=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=120)
        (work/(str(len(checks))+'_'+script+'.log')).write_text(result.stdout)
        if (result.returncode==0)==fail:raise RuntimeError(result.stdout[-4000:])
        checks.append({'script':script,'expected_failure':fail,'exit_code':result.returncode})
    run('check_conventions.py','--self-test')
    run('make_fixture.py','--output',work/'rebuilt_fixture');assert digests(work/'rebuilt_fixture')==before
    common=['--source-project',fixture/'project','--triangles',fixture/'surface_triangles.jsonl','--rules',fixture/'marking_rules016.json']
    for suffix in ['a','b']:run('generate_markings016.py',*common,'--output',work/suffix)
    assert digests(work/'a')==digests(work/'b'),'Non-deterministic outputs'
    run('audit_geometry016.py','--bundle',work/'a')
    report=json.loads((work/'a/output/generation_report016.json').read_text())
    assert report['status']=='GEOMETRY_READY' and report['triangles']>0 and report['owners']==['0:0','1:0']
    stats=report['road_statistics']['fixture_road']['types'];assert set(stats)=={'edge_left','edge_right','center_dash'}
    assert all(s['protected_owner_removed_m2']>0 and s['junction_removed_m2']>0 for s in stats.values())
    assert all(s['unsupported_area_m2']<1e-7 for s in stats.values())
    # Independent route-phase check in an unclipped section of the second owner.
    witness=json.loads((work/'a/output/support_witness016.json').read_text());meshes={p.stem.removeprefix('mesh_').replace('_',':'):json.loads(p.read_text()) for p in (work/'a/output/meshes').glob('*.json')}
    count=0
    for row in witness:
        if row['marking_kind']!='center_dash':continue
        m=meshes[row['owner']];uv=m['uv2'][row['vertex_offset']:row['vertex_offset']+3]
        s=sum(v[1] for v in uv)/3;assert -1e-5<=s%8<=3.00001,'Dash phase reset at owner border'
        count+=row['owner']=='1:0'
    assert count>0
    bad=json.loads((fixture/'marking_rules016.json').read_text());bad['triangle_sha256']='0'*64
    bad_path=work/'bad_rules.json';bad_path.write_text(json.dumps(bad))
    run('generate_markings016.py','--source-project',fixture/'project','--triangles',fixture/'surface_triangles.jsonl','--rules',bad_path,'--output',work/'bad',fail=True)
    run('generate_markings016.py',*common,'--output',fixture/'project/forbidden',fail=True)
    assert digests(fixture)==before,'Input fixture modified'
    result={'status':'PASS','commands':checks,'owners':report['owners'],'triangles':report['triangles'],'verified':['determinism','source hash rejection','read-only source guard','full emitted area/support audit','actual junction interruption','protected owner omission','global dash phase across owners'],'scope':'Synthetic generator-only evidence. No native baking/weather/main-world/driving/phone proof.'}
    (work/'smoke_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

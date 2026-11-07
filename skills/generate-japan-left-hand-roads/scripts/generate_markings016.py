#!/usr/bin/env python3
"""Exact saved-triangle-supported, explicitly scoped white road guidance.

Never writes to --source-project. Outputs are an additive resource overlay.
All paint polygons are clipped against the actual supporting road triangles;
vertex Y comes from that same triangle, not from the ideal road spline.
"""
from __future__ import annotations
import argparse, bisect, collections, hashlib, json, math, sys, struct
from pathlib import Path
from bundle_paths import fresh_output
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, substring, triangulate
from shapely.strtree import STRtree

def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,separators=(',',':'))+'\n')
def polygons(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for q in getattr(g,'geoms',[]) for p in polygons(q)]
def height(row,x,z):
    a,b,c=row['vertices'];d=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
    u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/d
    v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/d
    return a[1]*u+b[1]*v+c[1]*(1-u-v)
def normal(row):
    a,b,c=row['vertices'];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    length=math.sqrt(sum(x*x for x in n));return [x/length*(1 if n[1]>0 else -1) for x in n]
class Road:
    def __init__(self,r):
        self.r=r;self.line=LineString([(p[0],p[2]) for p in r['points']]);self.points=list(self.line.coords);self.stations=[0.]
        for a,b in zip(self.points,self.points[1:]):self.stations.append(self.stations[-1]+math.dist(a,b))
    def uv(self,x,z):
        s=self.line.project(Point(x,z));i=min(len(self.points)-2,max(0,bisect.bisect_right(self.stations,s)-1))
        a,b=self.points[i:i+2];dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
        # UV2 signed lateral / planar station in metres, the paint shader contract.
        return [((x-a[0])*(-dz)+(z-a[1])*dx)/length,s]

def generate(project,triangles,cfg_path,output):
    ROOT=fresh_output(output,project,triangles,cfg_path)
    cfg=json.loads(cfg_path.read_text());asset=ROOT/'project/assets/world/road_markings016';asset.mkdir(parents=True,exist_ok=True)
    layout_path=project/'assets/world/fuji_v3/layout_values.json';layout=json.loads(layout_path.read_text())
    assert sha(layout_path)==cfg['layout_sha256'];assert sha(triangles)==cfg['triangle_sha256']
    assert layout['generation_id']==cfg['source_generation']
    roads={r['id']:Road(r) for r in layout['roads']};protected=set(cfg['protected_owner_ids']);selected={r['road_id'] for r in cfg['routes']}
    scopes={};ribbons={};stats={};all_masks=[];outside_ranges=[]
    for spec in cfg['routes']:
        rid=spec['road_id'];road=roads[rid];r=road.r;start,end=spec['start_m'],spec['end_m']
        assert r['surface']=='asphalt' and 0<=start<end and start<road.line.length,(rid,road.line.length)
        if end>road.line.length+1e-6:
            outside_ranges.append({'road_id':rid,'requested_end_m':end,'actual_road_end_xz_m':road.line.length,'unsupported_end_range_m':[road.line.length,end],'action':'Stop at actual source-road endpoint; no extrapolation.'})
            end=road.line.length
        line=substring(road.line,start,min(end,road.line.length));scopes[rid]=line.buffer(r['width']/2+3,cap_style=2,join_style=2)
        marks={};edge=cfg['edge'];center=cfg['center']
        if edge['enabled'] and r['width']>=edge['minimum_road_width_m']:
            for side,sign in [('edge_left',1),('edge_right',-1)]:
                offset=sign*(r['width']/2-edge['paint_center_inset_m'])
                marks[side]=line.offset_curve(offset,join_style=2).buffer(edge['width_m']/2,cap_style=2,join_style=2)
        if center['enabled'] and r['width']>=center['minimum_road_width_m'] and r['bidirectional'] and spec.get('two_way_left_traffic_design') is True:
            ds=[];period=center['dash_m']+center['gap_m'];phase=center['phase_m'];i=math.floor((start-phase)/period)
            while phase+i*period<end:
                a=max(start,phase+i*period);b=min(end,phase+i*period+center['dash_m'])
                if b>a:ds.append(substring(road.line,a,b).buffer(center['width_m']/2,cap_style=2,join_style=2))
                i+=1
            marks['center_dash']=unary_union(ds)
        ribbons[rid]=marks;all_masks.extend(marks.values());stats[rid]={'range_xz_m':[start,end],'road_width_m':r['width'],'route_length_xz_m':road.line.length,'types':{}}
    search=unary_union(list(scopes.values()));search_bounds=search.bounds
    rows=[];source_files={};forbidden=[];forbidden_sources=collections.Counter();ignored_protected=0
    with triangles.open() as f:
        for ln in f:
            r=json.loads(ln)
            if not (r['visual_support'] and r['collision_owner']) or r['source_kind']!='road_surface':continue
            if r['chunk_id'] in protected:ignored_protected+=1;continue
            v=r['vertices'];xs=[p[0] for p in v];zs=[p[2] for p in v]
            if max(xs)<search_bounds[0] or min(xs)>search_bounds[2] or max(zs)<search_bounds[1] or min(zs)>search_bounds[3]:continue
            poly=Polygon([(p[0],p[2]) for p in v])
            if poly.area<1e-10 or not poly.intersects(search):continue
            assert r['generation_id']==cfg['source_generation']
            # Asphalt support only. Never silently apply the asphalt palette to timber/stone/gravel.
            if not r['resource_path'].endswith('_asphalt.tscn'):continue
            r['_poly']=poly;rows.append(r);source_files[r['resource_path']]=r['resource_sha256']
    for path,digest in source_files.items():assert sha(project/path.removeprefix('res://'))==digest, 'Changed actual support '+path
    for cid in protected:
        x,z=map(int,cid.split(':'));forbidden.append(box(x*128,z*128,(x+1)*128,(z+1)*128))
    protected_geometry=unary_union(forbidden)
    tree=STRtree([r['_poly'] for r in rows]);chunks={};witness=[];eps=cfg['geometry']['area_epsilon_m2'];lift=cfg['geometry']['vertical_lift_m']
    unsupported=[];junctions={};numeric_culls=0
    for rid,marks in ribbons.items():
        road=roads[rid];other=[r['_poly'] for r in rows if r['source_id']!=rid]
        # Real saved other-road / junction / platform polygons, not broad layout circles.
        actual_interrupt=unary_union(other).buffer(cfg['geometry']['junction_clearance_m']) if other else Polygon()
        junctions[rid]={'source_ids':sorted({r['source_id'] for r in rows if r['source_id']!=rid and r['_poly'].intersects(scopes[rid])}), 'clearance_m':cfg['geometry']['junction_clearance_m']}
        for kind,raw in marks.items():
            eligible=raw.difference(protected_geometry).difference(actual_interrupt);covered=[];tri_count=0;indices=[]
            for idx in tree.query(eligible):
                row=rows[int(idx)]
                if row['source_id']!=rid:continue
                intersection=eligible.intersection(row['_poly'])
                if intersection.is_empty:continue
                n=normal(row);assert n[1]>=cfg['geometry']['minimum_up_normal'],('steep support',rid,row['triangle_index'])
                covered.append(intersection)
                for poly in polygons(intersection):
                    if poly.area<=eps:continue
                    # Delaunay tessellation filtered against full polygon, never centroid-only.
                    for tri in triangulate(poly):
                        if tri.area<=eps or not poly.covers(tri):continue
                        xz=list(tri.exterior.coords)[:3]
                        # Godot front face is clockwise. Up normal supplied from actual support plane.
                        cross=(xz[1][0]-xz[0][0])*(xz[2][1]-xz[0][1])-(xz[1][1]-xz[0][1])*(xz[2][0]-xz[0][0])
                        if cross<0:xz[1],xz[2]=xz[2],xz[1]
                        xz=[(f32(x),f32(z)) for x,z in xz]
                        storage_cross=(xz[1][0]-xz[0][0])*(xz[2][1]-xz[0][1])-(xz[1][1]-xz[0][1])*(xz[2][0]-xz[0][0])
                        if storage_cross<=eps*2:
                            numeric_culls+=1;continue
                        cid=row['chunk_id'];assert cid not in protected
                        chunk=chunks.setdefault(cid,{'owner':cid,'vertices':[],'normals':[],'uv2':[],'color':cfg['edge']['color_linear'],'sources':{},'counts':collections.Counter()})
                        offset=len(chunk['vertices'])
                        vertices=[[float(x),f32(height(row,x,z)+lift),float(z)] for x,z in xz]
                        chunk['vertices'].extend(vertices);chunk['normals'].extend([n]*3);chunk['uv2'].extend([road.uv(x,z) for x,z in xz]);chunk['sources'][row['resource_path']]=row['resource_sha256'];chunk['counts'][rid+'/'+kind]+=1
                        witness.append({'owner':cid,'vertex_offset':offset,'road_id':rid,'marking_kind':kind,'source_resource':row['resource_path'],'source_sha256':row['resource_sha256'],'source_triangle_index':row['triangle_index'],'source_vertices':row['vertices']})
                        tri_count+=1
            got=unary_union(covered);missing=eligible.difference(got)
            stats[rid]['types'][kind]={'requested_area_m2':raw.area,'protected_owner_removed_m2':raw.intersection(protected_geometry).area,'junction_removed_m2':raw.difference(protected_geometry).intersection(actual_interrupt).area,'eligible_area_m2':eligible.area,'supported_area_m2':got.area,'unsupported_area_m2':missing.area,'paint_triangles':tri_count}
            if missing.area>cfg['geometry']['maximum_unsupported_area_m2']:
                unsupported.append({'road_id':rid,'kind':kind,'area_m2':missing.area,'bounds_xz':list(missing.bounds),'action':'Omit unsupported polygons; no map modification.'})
    mesh_dir=ROOT/'output/meshes';mesh_dir.mkdir(parents=True,exist_ok=True)
    for old in mesh_dir.glob('mesh_*.json'):old.unlink()
    for cid,chunk in chunks.items():write(mesh_dir/('mesh_'+cid.replace(':','_')+'.json'),chunk)
    write(asset/'marking_rules016.json',cfg);write(ROOT/'output/support_witness016.json',witness)
    report={'schema_version':1,'status':'GEOMETRY_READY' if not unsupported else 'GEOMETRY_READY_WITH_UNSUPPORTED_GAPS','generation':cfg['generation'],'source_project_read_only':str(project),'source_files':source_files,'layout_sha256':sha(layout_path),'triangle_sha256':sha(triangles),'rules_sha256':sha(cfg_path),'owners':sorted(chunks),'protected_owner_ids':sorted(protected),'protected_owner_triangles_ignored':ignored_protected,'road_statistics':stats,'junction_interruptions':junctions,'unsupported':unsupported,'outside_source_ranges':outside_ranges,'triangles':sum(len(c['vertices'])//3 for c in chunks.values()),'vertices':sum(len(c['vertices']) for c in chunks.values()),'batches':len(chunks),'float32_degenerate_fragments_omitted':numeric_culls,'storage':'IEEE754 float32 before native baking; degenerate rounding fragments omitted','lift_m':lift,'physics_changes':False,'acceptance':'Scoped generator proof only. Native mesh/weather checks and integrated visual review are separate.'}
    write(ROOT/'output/generation_report016.json',report);write(asset/'generation_report016.json',report)
    print(json.dumps({k:report[k] for k in ['status','owners','triangles','batches','unsupported']},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-project',type=Path,required=True)
    p.add_argument('--triangles',type=Path,required=True)
    p.add_argument('--rules',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True,help='New/empty additive overlay, separate from inputs')
    a=p.parse_args()
    generate(a.source_project.resolve(),a.triangles.resolve(),a.rules.resolve(),a.output)

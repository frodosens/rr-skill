#!/usr/bin/env python3
"""Bounded, reproducible R6/R7 safety candidate; no source geometry is edited.

Contract: safety_data009.json has world-space rail_spans (support/base points),
posts (support positions), and one-sided signs (base position, face normal).
A span is assigned by midpoint to one selected chunk; spans are split exactly at
chunk boundaries. Ground anchors are barycentrically measured, never guessed.
The companion safety_bake009.gd consumes the dictionary directly.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, Counter
import hashlib
import json
import math
import shutil
from bundle_paths import fresh_output
from pathlib import Path

CHUNKS = ['3:-11', '4:-11', '3:-10', '4:-10', '3:-9', '4:-9']
BOUNDS = [384.0, 640.0, -1408.0, -1024.0]
ROAD_IDS = ('paddy_lane', 'forest_return')
EXPECTED_TRIANGLE_SHA = '5acfbde5958bc5226270a7077216a65468688e4918268fb46e2fde1c16449eb4'
SIGN_TEXT = '橋の上は徐行\nゆずり合い\nカーブ注意\n林業ヤード\n出入口注意\n運転ヒント'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def rnd(values): return [round(float(v), 6) for v in values]
def inside(x, z, margin=0.0):
    return BOUNDS[0]+margin <= x <= BOUNDS[1]-margin and BOUNDS[2]+margin <= z <= BOUNDS[3]-margin
def chunk(x, z): return f'{math.floor(x/128)}:{math.floor(z/128)}'
def point_in_poly(x, z, vertices):
    yes = False
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if (a[1] > z) != (b[1] > z) and x < (b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]: yes = not yes
    return yes


class Surface:
    """Only actual collision-owner visual triangles. Spatial hash + XZ barycentrics."""
    def __init__(self, path):
        self.triangles = []
        self.bins = defaultdict(list)
        self.kind_counts = Counter()
        with path.open() as f:
            for line in f:
                row = json.loads(line)
                if not row['collision_owner'] or not row['visual_support']: continue
                if row['source_kind'] not in ('road_surface', 'roadside_ground', 'terrain_ground', 'bridge_deck', 'poi_platform'): continue
                vs = row['vertices']; xs = [v[0] for v in vs]; zs = [v[2] for v in vs]
                if max(xs)<BOUNDS[0]-20 or min(xs)>BOUNDS[1]+20 or max(zs)<BOUNDS[2]-20 or min(zs)>BOUNDS[3]+20: continue
                a,b,c=vs
                den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
                if abs(den)<1e-10: continue
                row['_den'] = den
                idx=len(self.triangles); self.triangles.append(row); self.kind_counts[row['source_kind']]+=1
                for ix in range(math.floor(min(xs)/8), math.floor(max(xs)/8)+1):
                    for iz in range(math.floor(min(zs)/8), math.floor(max(zs)/8)+1): self.bins[ix,iz].append(idx)

    def support(self, x, z, kinds=None, road_id=None):
        hits=[]
        for idx in self.bins.get((math.floor(x/8),math.floor(z/8)),[]):
            r=self.triangles[idx]
            if kinds and r['source_kind'] not in kinds: continue
            if road_id and r['source_id'] != road_id: continue
            a,b,c=r['vertices'];d=r['_den']
            u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/d
            v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/d
            w=1-u-v
            if min(u,v,w)<-1e-6: continue
            hits.append((u*a[1]+v*b[1]+w*c[1],r))
        if not hits: return None
        y,r=max(hits,key=lambda p:p[0])
        return {'y':round(y,6), 'resource_path':r['resource_path'], 'triangle_index':r['triangle_index'],
                'source_kind':r['source_kind'], 'source_id':r['source_id']}


class Road:
    def __init__(self, row):
        self.row=row;self.id=row['id'];self.points=row['points'];self.width=row['width'];self.s=[0.0]
        for a,b in zip(self.points,self.points[1:]): self.s.append(self.s[-1]+math.hypot(b[0]-a[0],b[2]-a[2]))
        self.length=self.s[-1]
    def at(self, station):
        import bisect
        station=max(0.0,min(self.length,station))
        i=min(len(self.s)-2,max(0,bisect.bisect_right(self.s,station)-1))
        a,b=self.points[i:i+2];f=(station-self.s[i])/(self.s[i+1]-self.s[i])
        p=[a[j]+(b[j]-a[j])*f for j in range(3)]
        n=math.hypot(b[0]-a[0],b[2]-a[2]);t=[(b[0]-a[0])/n,0.0,(b[2]-a[2])/n]
        return p,t
    def curvature(self, s):
        # Chord-based horizontal curvature, measured from source road centerline.
        a,_=self.at(s-10);b,_=self.at(s);c,_=self.at(s+10)
        ab=math.hypot(b[0]-a[0],b[2]-a[2]);bc=math.hypot(c[0]-b[0],c[2]-b[2]);ac=math.hypot(c[0]-a[0],c[2]-a[2])
        cross=(b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0])
        k=2*cross/(ab*bc*ac) if ab*bc*ac>1e-5 else 0.0
        return k


def generate(project, triangle_path, out, expected_sha, font_path, font_license):
    src=project/'assets/world/fuji_v3'
    layout=json.loads((src/'layout_values.json').read_text())
    exclusions=json.loads((src/'exclusions.json').read_text())
    hashes={p.name:sha(p) for p in (src/'layout_values.json',src/'exclusions.json',triangle_path)}
    if hashes[triangle_path.name]!=expected_sha: raise ValueError('Authoritative triangle corpus hash mismatch')
    surface=Surface(triangle_path)
    roads={r['id']:Road(r) for r in layout['roads'] if r['id'] in ROAD_IDS}
    poi_polys=[p for p in exclusions['polygons'] if p['kind'] in ('poi','junction')]
    bridge_polys={p['id']:p for p in exclusions['polygons'] if p['kind']=='bridge'}
    bridges=[b for b in layout['bridges'] if b['edge_id'] in ROAD_IDS]
    probes=[];rail_samples=defaultdict(list);rejects=Counter();signs=[]
    def excluded(x,z): return next((p['id'] for p in poi_polys if point_in_poly(x,z,p['vertices'])),None)
    for road in roads.values():
        ss=[i*2.0 for i in range(math.floor(road.length/2)+1)]+[road.length]
        for s in ss:
            p,t=road.at(s)
            if not inside(p[0],p[2]): continue
            center=surface.support(p[0],p[2],('road_surface','bridge_deck'))
            if not center: rejects['unsupported_center']+=1;continue
            k=road.curvature(s)
            for sign,side in ((1,'left'),(-1,'right')):
                left=[t[2]*sign,0,-t[0]*sign];off=road.width/2+0.65
                anchor=[p[0]+left[0]*off,0,p[2]+left[2]*off]
                support=surface.support(anchor[0],anchor[2])
                outside=[]
                for step in (2.0,4.0,8.0):
                    x=p[0]+left[0]*(road.width/2+step);z=p[2]+left[2]*(road.width/2+step)
                    h=surface.support(x,z,('terrain_ground','roadside_ground','poi_platform'))
                    outside.append({'distance_from_road_edge_m':step,'position_xz':rnd([x,z]),'support':h,
                                    'drop_from_road_m':round(center['y']-h['y'],6) if h else None})
                danger=any(o['drop_from_road_m'] is not None and o['drop_from_road_m'] >= (2.0 if o['distance_from_road_edge_m']<=4 else 3.0) for o in outside)
                bridge=None
                for b in bridges:
                    bs=road.length*b['fraction']
                    if b['edge_id']==road.id and abs(s-bs)<=b['length']/2+6:
                        bp,bt=road.at(bs);bh=surface.support(bp[0],bp[2],('road_surface','bridge_deck'),road.id)
                        poly=bridge_polys.get(b['id'])
                        if poly and bh and point_in_poly(bp[0],bp[2],poly['vertices']) and '__timber' in bh['resource_path']: bridge=b['id']
                record={'road_id':road.id,'station_m':round(s,6),'side':side,'center':rnd([p[0],center['y'],p[2]]),
                        'center_support':center,'curvature_per_m':round(k,8),'curve_radius_m':round(abs(1/k),3) if abs(k)>1e-8 else None,
                        'outside':outside,'cliff_threshold_met':danger,'bridge_id':bridge,'rail_anchor_support':support}
                probes.append(record)
                if not (danger or bridge): continue
                if not inside(anchor[0],anchor[2],0.35): rejects['rail_scope_margin']+=1;continue
                if excluded(anchor[0],anchor[2]): rejects['poi_or_junction_entry_gap']+=1;continue
                if support is None: rejects['rail_unsupported_anchor']+=1;continue
                if abs(support['y']-center['y'])>0.45: rejects['rail_anchor_height_difference']+=1;continue
                anchor[1]=support['y']
                rail_samples[(road.id,side)].append({'station_m':s,'position':anchor,'reason':'bridge_and_drop' if bridge and danger else 'bridge' if bridge else 'drop',
                                                    'bridge_id':bridge,'support':support,'max_drop_m':max((o['drop_from_road_m'] for o in outside if o['drop_from_road_m'] is not None),default=0)})
    spans=[];posts=[]
    # Segments are merged into chunk-local, station-contiguous polylines later.
    for (rid,side),samples in sorted(rail_samples.items()):
        for a,b in zip(samples,samples[1:]):
            if b['station_m']-a['station_m']>2.01: continue
            av,bv=a['position'],b['position'];ts=[0.0,1.0]
            for axis in (0,2):
                for boundary in range(math.floor(min(av[axis],bv[axis])/128)+1,math.ceil(max(av[axis],bv[axis])/128)):
                    t=(boundary*128-av[axis])/(bv[axis]-av[axis])
                    if 1e-6<t<1-1e-6:ts.append(t)
            ts=sorted(set(ts))
            for t0,t1 in zip(ts,ts[1:]):
                pa=[av[j]+(bv[j]-av[j])*t0 for j in range(3)];pb=[av[j]+(bv[j]-av[j])*t1 for j in range(3)]
                cid=chunk((pa[0]+pb[0])/2,(pa[2]+pb[2])/2)
                assert cid in CHUNKS
                s0=a['station_m']+(b['station_m']-a['station_m'])*t0;s1=a['station_m']+(b['station_m']-a['station_m'])*t1
                if spans and spans[-1]['chunk_id']==cid and spans[-1]['road_id']==rid and spans[-1]['side']==side and abs(spans[-1]['station_end_m']-s0)<0.001:
                    span=spans[-1];span['points'].append(rnd(pb));span['station_end_m']=round(s1,6)
                    span['max_measured_drop_m']=round(max(span['max_measured_drop_m'],a['max_drop_m'],b['max_drop_m']),6)
                else:
                    spans.append({'id':f'rail_{len(spans):03d}','chunk_id':cid,'road_id':rid,'side':side,
                                  'reason':a['reason'],'bridge_id':a['bridge_id'],'station_start_m':round(s0,6),'station_end_m':round(s1,6),
                                  'max_measured_drop_m':round(max(a['max_drop_m'],b['max_drop_m']),6),'points':[rnd(pa),rnd(pb)]})
    # Independent supported posts, <=4 m apart; endpoint posts only where exact support exists.
    seen=set()
    for span in spans:
        for i,p in enumerate(span['points']):
            if i%2 and i!=len(span['points'])-1:continue
            key=tuple(round(v,3) for v in p)
            if key in seen:continue
            h=surface.support(p[0],p[2])
            if h is None:raise ValueError('Rail endpoint lost support')
            seen.add(key);posts.append({'id':f'post_{len(posts):03d}','chunk_id':chunk(p[0]-1e-7,p[2]-1e-7) if chunk(p[0],p[2]) not in CHUNKS else chunk(p[0],p[2]),
                                       'span_id':span['id'],'position':rnd([p[0],h['y'],p[2]]),'support':h})
    def add_sign(road,s,direction,kind,text,reason):
        p,t=road.at(s);t=[a*direction for a in t];left=[t[2],0,-t[0]]
        # Always left of the approaching traffic, never in the roadway or POI access.
        for offset in (road.width/2+1.6,road.width/2+2.1,road.width/2+2.6):
            x,z=p[0]+left[0]*offset,p[2]+left[2]*offset
            if not inside(x,z,1.5) or excluded(x,z):continue
            h=surface.support(x,z,('terrain_ground','roadside_ground','poi_platform'))
            center=surface.support(p[0],p[2],('road_surface','bridge_deck'))
            if h is None or center is None or abs(h['y']-center['y'])>1.2:continue
            if any(math.hypot(q['position'][0]-x,q['position'][2]-z)<14 for q in signs):continue
            signs.append({'id':f'sign_{len(signs):03d}','chunk_id':chunk(x,z),'position':rnd([x,h['y'],z]),'normal':rnd([-t[0],0,-t[2]]),
                          'kind':kind,'text_ja':text,'supplement_ja':'運転ヒント','road_id':road.id,'station_m':round(s,6),'approach_direction':direction,
                          'placement_side':'left_of_approaching_traffic','offset_from_center_m':offset,'support':h,'reason':reason,
                          'regulatory':False,'width_m':2.4,'height_m':1.55,'board_center_height_m':2.25})
            return True
        rejects['sign_no_safe_supported_left_anchor']+=1;return False
    for b in bridges:
        road=roads[b['edge_id']];s=road.length*b['fraction'];bp,_=road.at(s)
        if not inside(bp[0],bp[2]):continue
        for direction in (1,-1):add_sign(road,s-direction*(b['length']/2+20),direction,'bridge_slow','橋の上は徐行\nゆずり合い',{'bridge_id':b['id'],'advance_m':20,'purpose':'non-regulatory bridge caution; no priority assigned'})
    # Radius below 250 m warrants a caution here, not the much stronger sharp-turn claim.
    for road in roads.values():
        values=[q for q in probes if q['road_id']==road.id and q['side']=='left' and q['curve_radius_m'] and 20<q['station_m']<road.length-20]
        if not values:continue
        most=min(values,key=lambda q:q['curve_radius_m'])
        if most['curve_radius_m']<250:
            for direction in (1,-1):
                add_sign(road,most['station_m']-direction*24,direction,'curve_warning','カーブ注意',
                         {'target_station_m':most['station_m'],'radius_m':most['curve_radius_m'],'turn_sign':1 if most['curvature_per_m']*direction>0 else -1})
    for road,s,d in ((roads['paddy_lane'],roads['paddy_lane'].length-48,1),(roads['forest_return'],48,-1)):
        add_sign(road,s,d,'yard_entry','林業ヤード\n出入口注意',{'poi_id':'forestry_yard','purpose':'entry awareness; no stop control or turnaround invented'})
    data={'schema_version':1,'generation_id':'forest-pcg009-safety-candidate','coordinate_system':'Godot world XYZ metres, absolute node coordinates',
          'scope':{'chunks':CHUNKS,'bounds_xz':BOUNDS,'roads':list(ROAD_IDS),'no_road_or_terrain_edits':True,'new_water':False},
          'font_resource':'res://assets/world/forest009/safety_signs009.otf','rail_spans':spans,'posts':posts,'signs':signs,
          'rail_geometry':{'beam_height_m':0.78,'beam_vertical_size_m':0.3,'beam_depth_m':0.16,'post_height_m':1.05,'post_width_m':0.12,
                           'collider':'merged closed-box beam and post triangle faces, one StaticBody3D per chunk','continuous':True},
          'summary':{'rail_spans':len(spans),'rail_segments':sum(len(s['points'])-1 for s in spans),'posts':len(posts),'signs':len(signs),
                     'rail_length_m':round(sum(sum(math.dist(a,b) for a,b in zip(s['points'],s['points'][1:])) for s in spans),3)}}
    report={'schema_version':1,'source_hashes':hashes,'triangle_source':str(triangle_path),'scope':data['scope'],'summary':data['summary'],
            'method':{'station_spacing_m':2,'rail_offset_from_center_m':3.9,'actual_support':'XZ barycentric interpolation on collision-owner visual source triangles',
                      'cliff_rule':'Drop >=2 m at edge+2/4 m OR >=3 m at edge+8 m. Missing support is unknown, not a fabricated cliff.',
                      'bridge_rule':'Original bridge tag AND bridge center in exclusion AND actual timber surface; protect deck and 6 m approach transition.',
                      'curve_rule':'Circumradius of three source-centerline positions at station +/-10 m. Caution below 250 m. No sharp-turn claim unless below 45 m.',
                      'entry_gaps':'All original POI and junction footprints remain free from rail anchors and signs.'},
            'selected_triangle_counts':dict(surface.kind_counts),'probe_count':len(probes),'measured_cliff_side_samples':sum(q['cliff_threshold_met'] for q in probes),
            'unmeasured_outer_samples':sum(o['support'] is None for q in probes for o in q['outside']),
            'rejections':dict(rejects),'minimum_curve_radius_m':min((q['curve_radius_m'] for q in probes if q['curve_radius_m']),default=None),
            'maximum_measured_drop_m':max((o['drop_from_road_m'] for q in probes for o in q['outside'] if o['drop_from_road_m'] is not None),default=None),
            'junction_decision':'forestry_yard_gate joins only paddy_lane and forest_return endpoints. POI platform is not a verified new road junction. No stop sign, legal priority or U-turn permission invented.',
            'limits':['Game-scene safety dressing, not legal or crash-performance certification.','Static source-triangle checks; parent must verify current catalog scene hashes and Godot collision/render behavior.',
                      'Bridge is existing graybox timber deck. No river, terrain cut, new bridge engineering, or new turnaround is authored.',
                      'Safety is bounded to the selected six chunks; it does not claim full-world cliff coverage.','Japanese label font must be bundled; labels are front-face only and are explicitly game driving hints.'],
            'tests':{},'probes':probes}
    # Geometry and sign intent acceptance checks run before any output is written.
    assert all(p['chunk_id'] in CHUNKS and inside(p['position'][0],p['position'][2]) for p in posts)
    assert all(inside(p[0],p[2]) for span in spans for p in span['points'])
    assert all(not excluded(p['position'][0],p['position'][2]) for p in posts+signs)
    for q in signs:
        p,t=roads[q['road_id']].at(q['station_m']);d=q['approach_direction'];t=[a*d for a in t]
        assert q['normal'][0]*t[0]+q['normal'][2]*t[2]<-0.999
        assert (q['position'][0]-p[0])*t[2]-(q['position'][2]-p[2])*t[0]>roads[q['road_id']].width/2
    for span in spans:
        assert all(math.dist(a,b)<2.1 for a,b in zip(span['points'],span['points'][1:]))
        for a,b in zip(span['points'],span['points'][1:]):
            for f in (0.25,0.5,0.75):
                p=[a[j]+(b[j]-a[j])*f for j in range(3)]
                assert not excluded(p[0],p[2]),'Rail crosses protected entry'
                h=surface.support(p[0],p[2]);assert h and abs(p[1]-h['y'])<0.15,'Rail unsupported between anchors'
    report['tests']={'bounded_scope':'PASS','actual_anchor_support':'PASS','continuous_sampled_spans':'PASS','no_entry_crossing':'PASS',
                     'left_hand_sign_placement':'PASS','approach_facing_normals':'PASS','original_triangle_hash':'PASS','godot_runtime':'NOT_RUN_BY_GENERATOR'}
    out.mkdir(parents=True,exist_ok=True)
    (out/'safety_data009.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (out/'safety_report009.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    # The checked-in OFL subset is already renamed; preserve its exact bytes and notice.
    from fontTools.ttLib import TTFont
    font=TTFont(font_path,recalcTimestamp=False)
    missing=set(SIGN_TEXT.replace('\n',''))-set(chr(i) for i in font.getBestCmap())
    if missing: raise ValueError(f'Bundled font missing glyphs: {missing}')
    shutil.copy2(font_path,out/'safety_signs009.otf')
    shutil.copy2(font_license,out/'safety_signs009_LICENSE.txt')
    report['tests']['japanese_font_glyph_coverage']='PASS'
    (out/'safety_report009.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({**data['summary'],'measured_cliff_side_samples':report['measured_cliff_side_samples'],'max_drop_m':report['maximum_measured_drop_m'],
                      'min_radius_m':report['minimum_curve_radius_m'],'rejections':dict(rejects),'tests':report['tests']},ensure_ascii=False))


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--triangles',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--expected-triangle-sha256',default=EXPECTED_TRIANGLE_SHA,help='Expected reviewed source digest; default is historical G007, never silently bypassed')
    ap.add_argument('--font',type=Path,default=root/'assets/fonts/safety_signs009.otf')
    ap.add_argument('--font-license',type=Path,default=root/'assets/fonts/safety_signs009_LICENSE.txt')
    a=ap.parse_args()
    out=fresh_output(a.output,a.project,a.triangles,a.font,a.font_license)
    generate(a.project.resolve(),a.triangles.resolve(),out,a.expected_triangle_sha256,a.font,a.font_license)

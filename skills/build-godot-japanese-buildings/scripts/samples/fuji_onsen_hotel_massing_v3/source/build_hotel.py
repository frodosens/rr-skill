"""Original hotel massing design. Uses the accepted original mesh authoring helpers.
No world placement, roads, terrain, game physics or existing assets are changed.
"""
import os,json,hashlib
CORE=os.path.abspath(os.path.join(os.path.dirname(__file__),'../../fuji_destination_assets_v1/source/build_assets.py'))
# Only definitions/authoring helpers, never the former package's export loop.
exec(compile(open(CORE).read().split('BUILDERS=')[0],CORE,'exec'),globals())

def hotel(detail=True):
 m=Mesh();m.box((0,.3,0),(44,.6,26),'stone',0)
 for x in [-15,15]:m.box((x,3.8,0),(12,6.4,24),'plaster',0)
 m.box((0,3.8,-2),(18,6.4,20),'plaster',0)
 m.box((0,.73,10.5),(18,.26,5),'cedar',0)
 # Central entrance is recessed beneath the main continuous roof.
 for x in [-8.7,-4.3,0,4.3,8.7]:m.box((x,3.85,8.1),(.24,6.35,.24),'cedar',0)
 for y in [.8,3.65,6.8]:m.box((0,y,8.15),(18,.22,.22),'cedar',0)
 def frontwindow(x,y,z,w=2.2,facing=1):
  m.box((x,y,z),(w,1.65,.08),'charcoal',0)
  for dx in ([-w/2,0,w/2] if detail else [-w/2,w/2]):m.box((x+dx,y,z+.05*facing),(.075,1.75,.06),'bamboo',0)
  for dy in [-.86,.86]:m.box((x,y+dy,z+.05*facing),(w+.1,.075,.06),'cedar',0)
  if detail:m.box((x,y,z+.06*facing),(w,.06,.06),'bamboo',0)
 for side in [-1,1]:
  for x0 in [10.5,13.5,16.5,19.5]:
   for y in [2.0,5.25]:frontwindow(side*x0,y,12.08)
  for x0 in [9.1,12,15,18,20.9]:m.box((side*x0,3.8,12.12),(.18,6.4,.18),'cedar',0)
  for y in [.8,3.65,6.8]:m.box((side*15,y,12.13),(12,.20,.2),'cedar',0)
  for z in [-10,-6,-2,2,6,10]:
   for y in [2,5.25]:
    m.box((side*21.07,y,z),(.08,1.65,2.45),'charcoal',0)
    for dz in [-1.25,0,1.25] if detail else [-1.25,1.25]:m.box((side*21.13,y,z+dz),(.06,1.75,.075),'bamboo',0)
   m.box((side*21.14,3.8,z+1.5),(.16,6.4,.16),'cedar',0)
 for x in [-19.5+3*i for i in range(14)]:
  for y in [2,5.25]:frontwindow(x,y,-12.09,facing=-1)
 for y in [.8,3.65,6.8]:m.box((0,y,-12.16),(42,.2,.18),'cedar',0)
 for x in [-6.4,-2.2,2.2,6.4]:frontwindow(x,5.25,8.17,3.4)
 for x in [-6.1,6.1]:frontwindow(x,2,8.17,3.4)
 m.box((0,1.98,8.24),(4.25,2.35,.1),'cedar',0)
 for x in [-1.05,1.05]:m.box((x,2.95,8.35),(2.02,1.1,.04),'vermilion',0)
 m.box((0,3.57,8.36),(4.6,.13,.18),'bamboo',0)
 for x in [-8.4,8.4]:
  m.box((x,3.85,12.5),(.25,6.3,.25),'cedar',0)
  if detail:
   m.box((x,1.35,12.5),(.6,1,.6),'bamboo',0);m.box((x,1.9,12.5),(.72,.12,.72),'charcoal',0)
 # Step heights are display-only; vehicles use a separate verified forecourt.
 m.box((0,.31,13.3),(8,.62,.8),'stone',0)
 m.box((0,.14,14.0),(8.4,.28,.5),'stone',1)
 m.roof(0,0,44.5,27.5,7.25,10.05)
 if detail:
  for z in [3,6,9,12]:
   half=12.015+(22.25-12.015)*z/13.75;y=10.05-2.8*z/13.75+.025
   m.cylinder((-half,y,z),(half,y,z),.028,'charcoal',1,n=4,tint=.96)
  for x in [-10,-5,0,5,10]:m.cylinder((x,7.32,13.5),(x,10.06,.1),.035,'charcoal',1,n=4,tint=.97)
 for x in [-15,15]:m.proxy('guest_wing',(x,3.8,0),(12,7.0,24))
 m.proxy('reception_core',(0,3.8,-2),(18,7,20))
 m.shelters=[{'position':[0,7.25,0],'size':[44.5,.25,27.5],'roof_top_y':10.265,'register_once':True,'status':'requires integration weather verification; contiguous roof footprint, no open courtyard'}]
 return m

manifest={'schema':1,'name':'Mountain onsen hotel massing v3','version':'0.3.0-massing-only','units':'metres','up_axis':'+Y','front_axis':'+Z','placement_status':'DESIGN MASSING ONLY; NOT WORLD PLACEMENT','materials':PALETTE,'modules':{},'assemblies':{},'provenance':{'geometry':'Original Blender Python authoring using accepted low-poly palette and helper functions','external_geometry':False,'runtime_generation':False,'accepted_asset_helper_sha256':hashlib.sha256(open(CORE,'rb').read()).hexdigest()}}
for lod in [0,1]:
 m=hotel(lod==0);m.export('hotel_building_lod'+str(lod))
 if lod==0:manifest['modules']['hotel_building']={'lods':{},'collision_proxies':m.proxies,'shelters':m.shelters,'origin_note':'Hotel base at y=0; entrance faces +Z and outer step ends z14.25'}
 manifest['modules']['hotel_building']['lods'][str(lod)]=dict(m.stats(),file='models/hotel_building_lod'+str(lod)+'.glb')
 compound=Mesh();compound.append(m);compound.append(bath(lod==0),(30,0,-5));compound.append(sign(lod==0),(-7,0,17));compound.append(bench(lod==0),(13,0,16),math.pi)
 # Privacy boundaries remain low-poly, open to the sky, and outside circulation.
 compound.box((30,1.2,-1.7),(10,2.4,.2),'cedar');compound.box((35,1.2,-6.5),(.2,2.4,9.5),'cedar')
 compound.export('hotel_compound_lod'+str(lod))
 if lod==0:manifest['assemblies']['hotel_compound']={'lods':{},'visual_only':True,'layout':[{'module':'hotel_building','position':[0,0,0],'yaw':0}],'note':'Pool and garden fence are preliminary layout, not finalized site ownership'}
 manifest['assemblies']['hotel_compound']['lods'][str(lod)]=dict(compound.stats(),file='models/hotel_compound_lod'+str(lod)+'.glb')
json.dump(manifest,open(OUT+'/asset_manifest.json','w'),indent=2)
contract={'status':'LOCAL MASSING DESIGN ONLY; WORLD TRANSFORM UNSET','hotel_root':[0,0,0],'entrance_face':'+Z','entrance_outer_step_front':[0,.28,14.25],'building_AABB':manifest['modules']['hotel_building']['lods']['0'],'floors':2,'rooms':'No interior layout or room-count claim','entry_forecourt_rect_xz':[-13,13,14.25,20],'hotel_street_rect_xz':[-40,40,20,26],'street_width':6,'opposite_parking_rect_xz':[-16,16,30,49],'parking_design':json.load(open(ROOT+'/source/parking_design.json')),'loading_rect_xz':[-31,-23,-10,-2],'private_bath_garden_rect_xz':[24,38,-14,1],'forest_buffer_candidate_rect_xz':[-40,40,-26,59],'forest_policy':'Forest surrounding a local clearing; actual tree retention and terrain boundaries belong to V3 planning','world_placement':None,'verification_gates':['Actual terrain and ridge-road conflict','Cross-street pedestrian/vehicle visibility','Two current cars swept turning and reversing','Contiguous roof weather occupancy at existing shelter cap','LOD and Android render budget']}
json.dump(contract,open(ROOT+'/evidence/hotel_site_contract.json','w'),indent=2)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/source/hotel_massing.blend')
print('HOTEL_MASSING',json.dumps({'building':manifest['modules']['hotel_building']['lods'],'compound':manifest['assemblies']['hotel_compound']['lods']}))

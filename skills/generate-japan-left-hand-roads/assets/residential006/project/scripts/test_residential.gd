extends SceneTree
const GENERATOR=preload("res://scripts/residential_road_generator.gd")
const CONFIG=preload("res://scripts/demo_config.gd")
func _init():call_deferred("run")
func signature(n):
 var bytes=PackedByteArray()
 for child in n.get_children():
  if child is MeshInstance3D:bytes.append_array(child.mesh.get_faces().to_byte_array())
 return bytes.hex_encode().sha256_text()
func run():
 var road=GENERATOR.new();root.add_child(road)
 var metrics=road.build(CONFIG.config(),CONFIG.ground_height)
 var sig=signature(road);var count=road.get_child_count()
 road.build(CONFIG.config(),CONFIG.ground_height)
 assert(sig==signature(road) and count==road.get_child_count(),"Deterministic repeated build")
 var surfaces=0
 for child in road.get_children():
  if child is MeshInstance3D:
   assert(road.get_node(str(child.name)+"_support").get_child(0).shape.get_faces()==child.mesh.get_faces(),"Exact visible/collision faces")
   surfaces+=1
 assert(surfaces>2 and metrics.driveway_count==2)
 for d in road.options.driveways:
  for off in [-d.width/2.-road.options.curb_ramp_length,-d.width/2.,0.,d.width/2.,d.width/2.+road.options.curb_ramp_length]:
   assert(road.samples.any(func(a):return absf(float(a.s)-float(d.station)-off)<0.00001),"Opening/ramp station inserted")
 for i in road.samples.size()-1:assert(road.samples[i+1].s>road.samples[i].s)
 await physics_frame;await physics_frame
 var rays=0
 for station in range(1,int(road.samples[-1].s)):
  var row=road.at(float(station))
  for lateral in [-1.0,0.0,1.0]:
   var p=road.point(row,lateral,road.road_height(row,lateral))
   var hit=road.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(p+Vector3.UP,p-Vector3.UP,1))
   assert(not hit.is_empty() and absf(hit.position.y-p.y)<0.015,"Actual physics ray support")
   rays+=1
 var result={"status":"PASS","surfaces":surfaces,"physics_rays":rays,"metrics":metrics,"scope":"Synthetic single road, exact face match, deterministic rebuild and centre-lane rays. No full junction, live world, visual or vehicle-drive proof."}
 FileAccess.open("res://../evidence/residential006.json",FileAccess.WRITE).store_string(JSON.stringify(result,"  "))
 print(JSON.stringify(result));quit()

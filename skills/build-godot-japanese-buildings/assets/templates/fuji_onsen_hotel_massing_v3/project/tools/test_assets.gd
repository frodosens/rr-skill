extends SceneTree
const BASE="res://assets/fuji_destinations/"
var checks:int=0
var failures:Array=[]
var material_ids:Dictionary={}
var material_refs:Dictionary={}
var manifest:Dictionary
func _initialize() -> void: call_deferred("run")
func check(value:bool,message:String) -> void:
    checks+=1
    if not value:failures.append(message);push_error(message)
func visit(n:Node,counts:Dictionary) -> void:
    check(n.get_script()==null,"No runtime scripts on asset nodes: "+str(n.name))
    if n is MeshInstance3D:
        counts.meshes+=1
        check(n.mesh!=null,"Mesh resource present")
        var lod:=1 if str(n.get_parent().name)=="LOD1" else 0
        for i in n.mesh.get_surface_count():
            var mat=n.get_surface_override_material(i)
            check(mat is ShaderMaterial,"Shared custom palette shader")
            material_ids[mat.get_instance_id()]=mat.resource_name
            var arrays=n.mesh.surface_get_arrays(i)
            check(arrays[Mesh.ARRAY_VERTEX].size()==arrays[Mesh.ARRAY_COLOR].size(),"Vertex exposure color count matches positions")
            for color:Color in arrays[Mesh.ARRAY_COLOR]:
                check(color.a==0.0 or color.a==1.0,"Snow exposure preserved by Godot import")
            if lod==0:counts.triangles+=arrays[Mesh.ARRAY_INDEX].size()/3
        check(n.visibility_range_end>n.visibility_range_begin,"Finite positive LOD range")
    if n is CollisionShape3D:
        counts.proxies+=1
        check(n.disabled,"Collision templates disabled")
        check(n.shape is BoxShape3D,"Only simple box collision proxies")
        check(n.shape.size.x>0 and n.shape.size.y>0 and n.shape.size.z>0,"Positive proxy dimensions")
    if n is StaticBody3D:
        check(n.collision_layer==0 and n.collision_mask==0,"No active physics layer on unverified assets")
    if n is Light3D or n is GPUParticles3D or n is CPUParticles3D:
        check(false,"No new lights or particle generators in reusable modules")
    for child in n.get_children():visit(child,counts)
func run() -> void:
    manifest=JSON.parse_string(FileAccess.get_file_as_string(BASE+"asset_manifest.json"))
    for key in manifest.materials:material_refs[key]=load(BASE+"materials/"+key+".tres")
    var counts_by_asset:Dictionary={}
    for group in ["modules","assemblies"]:
        for key in manifest[group]:
            var scene:PackedScene=load(BASE+"scenes/"+key+".tscn")
            check(scene!=null,"Saved scene loads "+key)
            var instance=scene.instantiate();root.add_child(instance)
            check(instance.get_meta("integration_status")=="unplaced_asset_only","Integration guard metadata")
            var counts={"meshes":0,"proxies":0,"triangles":0}
            visit(instance,counts)
            check(counts.triangles==manifest[group][key].lods["0"].triangles,"Imported triangles match manifest "+key)
            check(counts.meshes==2,"Exactly two explicit LOD meshes "+key)
            if group=="assemblies":check(counts.proxies==0,"Visual-only assemblies do not claim terrain ownership")
            counts_by_asset[key]=counts
            instance.free()
    check(material_ids.size()==8,"Exactly 8 shared material identities across all scenes")
    var baseline:=root.get_child_count()
    for cycle in range(40):
        var staged:Array=[]
        for key in manifest.assemblies:
            var instance=load(BASE+"scenes/"+key+".tscn").instantiate();root.add_child(instance);staged.append(instance)
        for key in manifest.materials:
            var mat:ShaderMaterial=load(BASE+"materials/"+key+".tres")
            mat.set_shader_parameter("snow_amount",float(cycle%2))
        await process_frame
        for instance in staged:instance.free()
        await process_frame
        check(root.get_child_count()==baseline,"Load/unload node baseline cycle "+str(cycle))
    for key in manifest.materials:
        var mat:ShaderMaterial=load(BASE+"materials/"+key+".tres");mat.set_shader_parameter("snow_amount",0.0)
    # Packed scenes stay inert throughout cycling; no game driving/surface APIs exist here.
    var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"material_identities":material_ids.size(),"load_unload_cycles":40,"assets":counts_by_asset,"scope":"Godot 4.6.3 headless load/resource/lifecycle checks. Not GPU shader, Android, placement, or driving acceptance."}
    var file:=FileAccess.open("res://../evidence/godot_validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    print(JSON.stringify({"passed":report.passed,"checks":checks,"failures":failures,"cycles":40,"materials":material_ids.size()}))
    quit(0 if failures.is_empty() else 1)

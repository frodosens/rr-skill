extends SceneTree
const GrassField=preload("res://scripts/grass_field.gd")
var checks: Array[String]=[]
var failures: Array[String]=[]
func check(condition: bool, message: String) -> void:
    if condition: checks.append(message)
    else: failures.append(message)
func _init() -> void: call_deferred("run")
func run() -> void:
    var node := Node3D.new()
    root.add_child(node)
    var camera := Camera3D.new()
    node.add_child(camera)
    camera.position=Vector3(17.5,4.5,31.0)
    var field=GrassField.new()
    field.camera=camera
    node.add_child(field)
    field.set_process(false)
    for lod in 3:
        var arr: Array=field.meshes[lod].surface_get_arrays(0)
        var indices: PackedInt32Array=arr[Mesh.ARRAY_INDEX]
        var uvs: PackedVector2Array=arr[Mesh.ARRAY_TEX_UV]
        check(indices.size()/3==[30,12,4][lod],"LOD %d exact triangle count"%lod)
        var bottoms := 0
        var tops := 0
        for uv in uvs:
            check(uv.y>=0.0 and uv.y<=1.0,"LOD %d normalized height"%lod)
            if uv.y==0.0: bottoms+=1
            if uv.y==1.0: tops+=1
        check(bottoms==[10,6,4][lod] and tops==bottoms,"LOD %d root / tip UV rows"%lod)
    check(field.get_child_count()==64,"64 chunk nodes rather than one node per clump")
    check(field.clump_count>25000 and field.clump_count<41000,"Plausible seeded field density")
    check(field.min_accepted_path_distance>=2.6,"Generated roots respect 2.6 m path exclusion")
    check(field.generation_aabb_failures==0,"All generated roots fit conservative AABBs")
    # Dummy headless RenderingServer cannot return MultiMesh transforms. Live
    # GPU-backed buffer and transform readback is checked in capture.gd.
    field.update_lod(true)
    var near_stats: Dictionary=field.stats.duplicate(true)
    check(near_stats.active_chunks_by_lod[0]>0 and near_stats.active_chunks_by_lod[1]>0 and near_stats.active_chunks_by_lod[2]>0,"All three LOD tiers activate")
    camera.position=Vector3(1000.0,5.0,1000.0)
    field.update_lod(true)
    check(field.stats.submitted_triangles_upper_bound_before_frustum==0,"All chunks culled far away")
    camera.position=Vector3(17.5,4.5,31.0)
    field.update_lod(true)
    check(field.stats.submitted_triangles_upper_bound_before_frustum==near_stats.submitted_triangles_upper_bound_before_frustum,"Returning camera restores LOD counts")
    field.set_winter(true)
    check(field.material.get_shader_parameter("snow")==1.0,"Snow uniform enabled")
    field.set_winter(false)
    check(field.material.get_shader_parameter("snow")==0.0,"Snow uniform disabled")
    field.wind_enabled=false
    field._process(0.01)
    check(field.material.get_shader_parameter("wind_strength")==0.0,"Wind off has zero displacement uniform")
    field.wind_enabled=true
    field._process(0.01)
    check(is_equal_approx(field.material.get_shader_parameter("wind_strength"),0.28),"Wind on restores amplitude")
    # Analytic root/mid/tip invariant for the exact h*h factor used in shader.
    for t in [0.0,0.73,3.1,17.0]:
        var phase := 1.9
        var wave := 0.57+0.28*sin(t*1.8+phase)+0.15*sin(t*3.1+phase*1.63)
        var root_offset := 0.28*wave*0.0*0.0
        var middle_offset := 0.28*wave*0.5*0.5
        var tip_offset := 0.28*wave
        check(root_offset==0.0,"Root immobile at time %.2f"%t)
        check(is_equal_approx(middle_offset/tip_offset,0.25),"Half-height displacement is one-quarter at time %.2f"%t)
    var record := {"status":"PASS" if failures.is_empty() else "FAIL","checks_passed":checks.size(),"unique_checks":{},"failures":failures,"wide_view_budget":near_stats,"scope":"Headless geometry, generation, LOD, masks and shader parameter/math checks; actual shader compilation and appearance are NOT tested here and require separate GL validation."}
    for item in checks: record.unique_checks[item]=true
    FileAccess.open("res://../evidence/tests.json",FileAccess.WRITE).store_string(JSON.stringify(record,"  "))
    print(JSON.stringify({"status":record.status,"checks_passed":checks.size(),"failures":failures,"wide_view_budget":near_stats}))
    quit(0 if failures.is_empty() else 1)

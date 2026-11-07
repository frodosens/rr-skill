extends SceneTree
var game: Node3D
var records: Array[Dictionary]=[]
var failures: Array[String]=[]
func _init() -> void: call_deferred("run")
func sample_case(name: String, view: int, grass: bool, wind: bool, snow: bool) -> void:
    game.set_view(view)
    game.field.visible=grass
    game.field.wind_enabled=wind
    game.field.set_winter(snow)
    game.ground_material.albedo_color=Color("d7dfd8") if snow else Color("a2a67c")
    # Keep HUD exactly unchanged: only grass visibility/wind/weather vary.
    game.field.fixed_time=1.2
    for settle in 4: await process_frame
    var draw_samples := []
    var primitive_samples := []
    var object_samples := []
    for sample in 3:
        await process_frame
        draw_samples.append(int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)))
        primitive_samples.append(int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)))
        object_samples.append(int(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)))
    if draw_samples.min()!=draw_samples.max(): failures.append(name+": unstable draw-call samples")
    if primitive_samples.min()!=primitive_samples.max(): failures.append(name+": unstable primitive samples")
    records.append({"name":name,"view":view,"grass":grass,"wind":wind,"snow":snow,"draw_call_samples":draw_samples,"primitive_samples":primitive_samples,"rendered_object_samples":object_samples,"camera_xyz":[game.camera.position.x,game.camera.position.y,game.camera.position.z],"grass_budget_before_frustum":game.field.stats.duplicate(true)})
func run() -> void:
    if DisplayServer.get_name()=="headless":
        push_error("Actual GL rendering required")
        quit(2)
        return
    root.size=Vector2i(1280,800)
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    game=load("res://main.tscn").instantiate()
    root.add_child(game)
    game.field.fixed_time=1.2
    for warmup in 8: await process_frame
    await sample_case("wide_off",1,false,true,false)
    await sample_case("wide_on",1,true,true,false)
    await sample_case("wide_wind_off",1,true,false,false)
    await sample_case("wide_snow",1,true,true,true)
    await sample_case("close_off",2,false,true,false)
    await sample_case("close_on",2,true,true,false)
    await sample_case("overview_off",3,false,true,false)
    await sample_case("overview_on",3,true,true,false)
    var delta_by_view := {}
    for item in [["wide",0,1],["close",4,5],["overview",6,7]]:
        var a: Dictionary=records[item[1]]
        var b: Dictionary=records[item[2]]
        delta_by_view[item[0]]={"whole_scene_grass_off":a.draw_call_samples[0],"whole_scene_grass_on":b.draw_call_samples[0],"grass_draw_call_difference":b.draw_call_samples[0]-a.draw_call_samples[0],"grass_primitive_difference":b.primitive_samples[0]-a.primitive_samples[0],"grass_rendered_object_difference":b.rendered_object_samples[0]-a.rendered_object_samples[0]}
    if records[1].draw_call_samples[0]!=records[2].draw_call_samples[0]: failures.append("Wind toggle changed draw call count")
    if records[1].draw_call_samples[0]!=records[3].draw_call_samples[0]: failures.append("Snow discard changed draw call count")
    var hashes := {}
    for path in ["res://scripts/demo.gd","res://scripts/grass_field.gd","res://shaders/grass.gdshader"]: hashes[path]=FileAccess.get_sha256(path)
    var report := {"status":"PASS" if failures.is_empty() else "FAIL","failures":failures,"renderer":RenderingServer.get_video_adapter_name(),"godot_version":Engine.get_version_info().string,"resolution":[1280,800],"rendering_method":RenderingServer.get_current_rendering_method(),"measurement":"Godot Performance rendering counters; same-view grass-on minus grass-off, stable three-frame samples. Not a GPU API trace or phone benchmark.","scene_settings":{"grass_shadows":false,"sun_shadows":false,"grass_surfaces_per_mesh":1,"grass_materials_per_chunk":1,"alpha_blending":false,"extra_depth_prepass_requested":false,"hud_held_constant":true},"source_sha256":hashes,"grass_draw_calls_by_view":delta_by_view,"records":records,"target_phone_fps_measured":false,"target_phone_gpu_ms_measured":false}
    FileAccess.open("res://../evidence/draw_call_profile.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
    print(JSON.stringify({"status":report.status,"deltas":delta_by_view,"failures":failures}))
    quit(0 if failures.is_empty() else 1)

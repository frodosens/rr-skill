extends SceneTree
var game: Node3D
var captures: Array[Dictionary]=[]
var failures: Array[String]=[]
func _init() -> void:
    RenderingServer.render_loop_enabled=false
    call_deferred("run")
func snap(name: String, view: int, snow: bool, wind: bool, time: float, grass: bool=true) -> void:
    game.set_view(view)
    game.set_winter(snow)
    game.field.wind_enabled=wind
    game.field.fixed_time=time
    game.field.visible=grass
    game.update_label()
    RenderingServer.render_loop_enabled=true
    for frame in 3: await process_frame
    var path := "res://../captures/"+name+".png"
    var img := root.get_texture().get_image()
    if img.save_png(path)!=OK: failures.append("Could not save "+path)
    captures.append({"name":name,"sha256":FileAccess.get_sha256(path),"view":view,"snow":snow,"wind":wind,"wind_time":time,"grass_enabled":grass,"budget":game.field.stats.duplicate(true),"render_draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"render_primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)})
    FileAccess.open("res://../evidence/partial_captures.json",FileAccess.WRITE).store_string(JSON.stringify({"status":"IN_PROGRESS","captures":captures},"  "))
    RenderingServer.render_loop_enabled=false
func run() -> void:
    if DisplayServer.get_name()=="headless":
        push_error("Actual OpenGL display required")
        quit(2)
        return
    root.size=Vector2i(1280,800)
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    game=load("res://main.tscn").instantiate()
    root.add_child(game)
    game.field.fixed_time=1.2
    var checked := 0
    var invalid_road_roots := 0
    var invalid_bounds := 0
    for chunk in game.field.chunks:
        var n: MultiMeshInstance3D=chunk.node
        for i in n.multimesh.instance_count:
            var transform: Transform3D=n.multimesh.get_instance_transform(i)
            var p: Vector3=n.position+transform.origin
            if absf(p.x-game.field.path_center(p.z))<2.599: invalid_road_roots+=1
            if not n.multimesh.custom_aabb.has_point(transform.origin): invalid_bounds+=1
            checked+=1
    if invalid_road_roots>0: failures.append("Live grass roots encroach path")
    if invalid_bounds>0: failures.append("Live root outside expanded AABB")
    FileAccess.open("res://../evidence/live_buffers.json",FileAccess.WRITE).store_string(JSON.stringify({"instances_checked":checked,"invalid_road_roots":invalid_road_roots,"invalid_root_bounds":invalid_bounds,"renderer":RenderingServer.get_video_adapter_name()},"  "))
    if OS.get_environment("GRASS_CAPTURE_REMAINING")!="1":
        await snap("01_wide_grass",1,false,true,1.2)
        await snap("02_wide_no_grass",1,false,false,1.2,false)
        await snap("03_close_wind_off",2,false,false,1.2)
        await snap("04_close_wind_a",2,false,true,1.2)
    await snap("05_close_wind_b",2,false,true,2.4)
    await snap("06_wide_snow",1,true,true,1.2)
    await snap("07_overview",3,false,true,1.2)
    # Short animation uses deterministic simulation time. Capture speed is NOT FPS.
    if OS.get_environment("GRASS_CAPTURE_VIDEO")=="1":
        root.size=Vector2i(960,600)
        game.set_view(2)
        game.set_winter(false)
        game.field.wind_enabled=true
        game.update_label()
        RenderingServer.render_loop_enabled=true
        for frame in 36:
            game.field.fixed_time=float(frame)/12.0
            for settle in 2: await process_frame
            root.get_texture().get_image().save_png("res://../captures/wind_%03d.png"%frame)
        RenderingServer.render_loop_enabled=false
    var previously_captured := {}
    for filename in ["01_wide_grass","02_wide_no_grass","03_close_wind_off","04_close_wind_a"]:
        var path: String = "res://../captures/"+filename+".png"
        if FileAccess.file_exists(path): previously_captured[filename]=FileAccess.get_sha256(path)
    var source_hashes := {}
    for path in ["res://scripts/demo.gd","res://scripts/grass_field.gd","res://shaders/grass.gdshader"]:
        source_hashes[path]=FileAccess.get_sha256(path)
    var report := {"source_sha256":source_hashes,"previous_valid_capture_sha256":previously_captured,"status":"PASS" if failures.is_empty() else "FAIL","failures":failures,"renderer":RenderingServer.get_video_adapter_name(),"rendering_method":RenderingServer.get_current_rendering_method(),"display":DisplayServer.get_name(),"live_multimesh_instances_checked":checked,"invalid_road_roots":invalid_road_roots,"invalid_root_bounds":invalid_bounds,"captures":captures,"performance_scope":"Actual Godot GL rendering on cloud software renderer. No target-device FPS or frame-time claim."}
    FileAccess.open("res://../evidence/render.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
    print(JSON.stringify({"status":report.status,"renderer":report.renderer,"failures":failures,"captures":captures.size(),"instances":checked}))
    quit(0 if failures.is_empty() else 1)

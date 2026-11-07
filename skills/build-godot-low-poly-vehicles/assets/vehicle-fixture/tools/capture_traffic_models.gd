extends SceneTree
## Development-only model gallery, rendered with the game's Compatibility renderer.
const Visual = preload("res://scripts/traffic_vehicle_visual.gd")

func _init() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty():
		quit(1)
		return
	DirAccess.make_dir_recursive_absolute(args[0])
	root.size = Vector2i(1600, 1000)
	var world := Node3D.new()
	root.add_child(world)
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("b7c9d0")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("c6d2ce")
	env.ambient_light_energy = 0.55
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.environment = env
	world.add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-44, -32, 0)
	sun.light_color = Color("fff1d9")
	sun.light_energy = 0.85
	sun.shadow_enabled = true
	sun.shadow_opacity = 0.82
	world.add_child(sun)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200, 200)
	ground.mesh = plane
	var ground_mat := StandardMaterial3D.new()
	ground_mat.albedo_color = Color("727d77")
	ground_mat.roughness = 1.0
	ground.material_override = ground_mat
	ground.position.y = -0.018
	world.add_child(ground)
	var models: Array[Node3D] = []
	for index in range(Visual.KINDS.size()):
		var visual := Visual.create(Visual.KINDS[index])
		world.add_child(visual)
		visual.position = Vector3((index - 2) * 4.0, 0, 0)
		models.append(visual)
	var camera := Camera3D.new()
	camera.current = true
	camera.fov = 44.0
	world.add_child(camera)
	camera.position = Vector3(12, 10.5, -22)
	camera.look_at(Vector3(0, 0.7, 0))
	await capture(args[0].path_join("traffic_models_front.png"))
	camera.position = Vector3(-12, 10.5, 22)
	camera.look_at(Vector3(0, 0.7, 0))
	await capture(args[0].path_join("traffic_models_rear.png"))
	for index in range(models.size()):
		for other in models:
			other.visible = other == models[index]
		var origin := models[index].position
		camera.position = origin + Vector3(5.4, 3.0, -7.0) * (1.20 if Visual.KINDS[index] == "truck" else 1.0)
		camera.look_at(origin + Vector3.UP * (1.1 if Visual.KINDS[index] == "truck" else 0.7))
		await capture(args[0].path_join("traffic_model_%s.png" % Visual.KINDS[index]))
	world.queue_free()
	await process_frame
	quit()

func capture(path: String) -> void:
	for frame in range(4):
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(path)
	print("TRAFFIC_MODEL_CAPTURE: ", path)

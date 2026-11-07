extends SceneTree

const Visual = preload("res://scripts/traffic_vehicle_visual.gd")
var checks := 0
var failures := 0

func _init() -> void:
	call_deferred("run")

func check(condition: bool, label: String) -> void:
	checks += 1
	if condition:
		print("PASS: ", label)
	else:
		failures += 1
		push_error("FAIL: " + label)

func inspect_mesh(mesh: Mesh) -> Dictionary:
	var triangles := 0
	var normals_ok := true
	var winding_ok := true
	var opaque := true
	for surface in range(mesh.get_surface_count()):
		var material := mesh.surface_get_material(surface) as StandardMaterial3D
		opaque = opaque and material != null and material.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		triangles += int(vertices.size() / 3)
		for normal in normals:
			normals_ok = normals_ok and normal.is_finite() and absf(normal.length() - 1.0) < 0.001
		for index in range(0, vertices.size(), 3):
			var normal := (vertices[index + 2] - vertices[index]).cross(vertices[index + 1] - vertices[index]).normalized()
			winding_ok = winding_ok and normal.dot(normals[index]) > 0.90
	return {"triangles": triangles, "normals": normals_ok, "winding": winding_ok, "opaque": opaque}

func run() -> void:
	var colors: Dictionary = {}
	var silhouettes: Dictionary = {}
	for kind in Visual.KINDS:
		var scene := load("res://scenes/traffic/%s.tscn" % kind) as PackedScene
		check(scene != null, "%s reusable scene exists" % kind)
		var visual := scene.instantiate() as Node3D
		root.add_child(visual)
		await process_frame
		var body := visual.get_node("Chassis") as MeshInstance3D
		var wheels := visual.get_node("FourRollingWheels") as MultiMeshInstance3D
		var body_info := inspect_mesh(body.mesh)
		var wheel_info := inspect_mesh(wheels.multimesh.mesh)
		var triangles: int = body_info.triangles + wheel_info.triangles * 4
		var surfaces := body.mesh.get_surface_count() + wheels.multimesh.mesh.get_surface_count()
		check(triangles <= Visual.MAX_TRIANGLES, "%s triangle budget: %d <= %d" % [kind, triangles, Visual.MAX_TRIANGLES])
		check(surfaces <= Visual.MAX_DRAW_SURFACES, "%s draw surface budget: %d <= %d" % [kind, surfaces, Visual.MAX_DRAW_SURFACES])
		check(body_info.normals and wheel_info.normals, "%s normals finite and normalized" % kind)
		check(body_info.winding and wheel_info.winding, "%s front-face winding matches normals" % kind)
		check(body_info.opaque and wheel_info.opaque, "%s opaque mobile materials only" % kind)
		check(wheels.multimesh.physics_interpolation_quality == MultiMesh.INTERP_QUALITY_HIGH, "%s wheels preserve rotation/scale between physics ticks" % kind)
		check(visual.get_child_count() == 2 and wheels.multimesh.instance_count == 4, "%s chassis plus four batched wheels" % kind)
		check(visual.find_children("*", "Light3D", true, false).is_empty() and visual.find_children("*", "CollisionObject3D", true, false).is_empty(), "%s visual adds no lights or physics" % kind)
		check(not visual.is_processing() and not visual.is_physics_processing(), "%s visual has no autonomous frame callbacks" % kind)
		var bounds := body.mesh.get_aabb()
		var wheel_bounds := wheels.multimesh.mesh.get_aabb()
		for index in range(4):
			bounds = bounds.merge(visual.wheel_transforms[index] * wheel_bounds)
		var declared := Visual.dimensions(kind)
		check(bounds.position.x >= -declared.x * 0.5 - 0.015 and bounds.end.x <= declared.x * 0.5 + 0.015 and bounds.position.z >= -declared.z * 0.5 - 0.015 and bounds.end.z <= declared.z * 0.5 + 0.015 and bounds.end.y <= declared.y + 0.015, "%s model fits declared road clearance %s; actual %s" % [kind, declared, bounds])
		check(absf(bounds.position.y) <= 0.001, "%s tire contact plane is y=0" % kind)
		var other := Visual.create(kind)
		root.add_child(other)
		check(other.get_node("Chassis").mesh == body.mesh and other.get_node("FourRollingWheels").multimesh.mesh == wheels.multimesh.mesh, "%s duplicate instances share geometry" % kind)
		var old_transform: Transform3D = visual.wheel_transforms[0]
		var old_energy: float = body.get_surface_override_material(Visual.TAILLAMP).emission_energy_multiplier
		visual.set_motion(10.0, 0.3, 1.0, 1.0 / 60.0)
		check(not visual.wheel_transforms[0].basis.is_equal_approx(old_transform.basis), "%s wheels roll and steer" % kind)
		check(visual.wheel_transforms[0].origin.is_equal_approx(old_transform.origin), "%s wheel motion preserves mount points" % kind)
		check(body.get_surface_override_material(Visual.TAILLAMP).emission_energy_multiplier > old_energy, "%s independent brake lamps brighten" % kind)
		check(is_equal_approx(other.get_node("Chassis").get_surface_override_material(Visual.TAILLAMP).emission_energy_multiplier, old_energy), "%s braking does not affect another car" % kind)
		var valid_transform: Transform3D = visual.wheel_transforms[0]
		visual.set_motion(NAN, 0.0, 0.0, 0.016)
		check(visual.wheel_transforms[0].is_equal_approx(valid_transform), "%s invalid motion cannot corrupt wheels" % kind)
		var swept_bounds_ok := true
		var wheel_vertices := PackedVector3Array()
		for surface in range(wheels.multimesh.mesh.get_surface_count()):
			wheel_vertices.append_array(wheels.multimesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX])
		for steer in [-0.55, -0.275, 0.0, 0.275, 0.55]:
			for roll_step in range(20):
				visual.wheel_roll = float(roll_step) * TAU / 20.0
				visual.set_motion(0.0, steer, 0.0, 0.0)
				for transform: Transform3D in visual.wheel_transforms:
					for vertex in wheel_vertices:
						var point := transform * vertex
						swept_bounds_ok = swept_bounds_ok and absf(point.x) <= declared.x * 0.5 + 0.001 and absf(point.z) <= declared.z * 0.5 + 0.001 and point.y >= -0.001 and point.y <= declared.y + 0.001
		check(swept_bounds_ok, "%s dimensions include full steering and rolling sweep" % kind)
		colors[Visual.default_color(kind).to_html()] = true
		silhouettes[str(declared)] = true
		other.queue_free()
		visual.queue_free()
		await process_frame
	check(colors.size() == 5 and silhouettes.size() == 5, "five distinct palettes and vehicle proportions")
	var custom := Visual.create("not_a_kind")
	root.add_child(custom)
	check(custom.kind == "sedan_a", "unknown variant uses safe sedan fallback")
	custom.configure("hatchback", Color("704a81"))
	check(custom.kind == "hatchback" and custom.get_child_count() == 2 and custom.get_node("Chassis").get_surface_override_material(Visual.PAINT).albedo_color.is_equal_approx(Color("704a81")), "reconfiguration changes model and paint without duplicate geometry nodes")
	custom.queue_free()
	await process_frame
	print("RESULT: %d/%d traffic visual checks passed" % [checks - failures, checks])
	quit(1 if failures else 0)

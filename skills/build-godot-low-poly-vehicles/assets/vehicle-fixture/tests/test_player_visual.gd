extends SceneTree
const Player = preload("res://scripts/player_vehicle_visual.gd")
var failures := 0

func check(value: bool, label: String) -> void:
	if not value:
		failures += 1
		push_error(label)

func _init() -> void:
	call_deferred("run")

func run() -> void:
	var result := Player.create()
	var other := Player.create()
	var visual: Node3D = result.visual
	root.add_child(visual)
	root.add_child(other.visual)
	check(result.wheels.size() == 4 and result.front_wheels.size() == 2, "Wheel binding counts")
	for wheel in result.wheels:
		check(wheel.get_node_or_null("Spinner") != null, "Independent wheel spinner")
		check(is_equal_approx(absf(wheel.position.x), 0.91) and is_equal_approx(wheel.position.y, 0.38), "Chassis wheel mounts preserved")
	for wheel in result.front_wheels:
		check(is_equal_approx(wheel.position.z, -1.35), "Front axle selection")
	var triangles := 0
	var materials := {}
	var meshes := visual.find_children("*", "MeshInstance3D", true, false)
	for node in meshes:
		var mesh: Mesh = node.mesh
		for surface in range(mesh.get_surface_count()):
			var material := node.get_active_material(surface) as StandardMaterial3D
			materials[material] = true
			check(material != null and material.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED, "Opaque material")
			var arrays := mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var indices := PackedInt32Array()
			if arrays[Mesh.ARRAY_INDEX] != null:
				indices = arrays[Mesh.ARRAY_INDEX]
			var count := indices.size() if not indices.is_empty() else vertices.size()
			triangles += int(count / 3)
			for vertex in vertices:
				check(vertex.is_finite(), "Finite vertex")
			for normal in normals:
				check(normal.is_finite() and absf(normal.length() - 1.0) < 0.001, "Unit normal")
			for start in range(0, count, 3):
				var a := indices[start] if not indices.is_empty() else start
				var b := indices[start + 1] if not indices.is_empty() else start + 1
				var c := indices[start + 2] if not indices.is_empty() else start + 2
				var face := (vertices[c] - vertices[a]).cross(vertices[b] - vertices[a])
				check(face.length_squared() > 1e-12 and face.normalized().dot(normals[a]) > 0.90, "Nondegenerate clockwise facet")
	check(triangles <= 3500 and meshes.size() <= 22 and materials.size() <= 7, "Player visual budget")
	var tail: Material = result.tail_lights[0].get_active_material(0)
	var other_tail: Material = other.tail_lights[0].get_active_material(0)
	check(tail != other_tail, "Brake materials isolated between vehicles")
	print("PLAYER_VISUAL: triangles=%d meshes=%d materials=%d failures=%d" % [triangles, meshes.size(), materials.size(), failures])
	visual.free()
	other.visual.free()
	quit(0 if failures == 0 else 1)

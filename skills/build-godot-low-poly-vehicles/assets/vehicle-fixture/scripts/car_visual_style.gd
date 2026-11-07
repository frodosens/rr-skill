extends RefCounted
## Restrained low-poly materials: broad highlights and small, flat chamfers.
## This is a one-time visual pass. It adds no lights, physics or frame updates.

static func apply(visual: Node3D) -> void:
	if visual.has_meta("stylized_materials"):
		return
	var paint := _material("Body paint", Color("6b100c"), 0.0, 0.48, 0.22)
	var rubber := _material("Matte rubber and trim", Color("18222a"), 0.0, 0.88, 0.18)
	var glass := _material("Opaque blue grey glass", Color("142830"), 0.0, 0.27, 0.42)
	var metal := _material("Satin wheel metal", Color("73818a"), 0.85, 0.46, 0.4)
	var lamp := _material("Frosted headlamp", Color("6d7c80"), 0.0, 0.48, 0.2)
	var plate := _material("Matte registration plate", Color("707b80"), 0.0, 0.82, 0.12)
	var meshes := visual.find_children("*", "MeshInstance3D", true, false)
	for item in meshes:
		var mesh := item as MeshInstance3D
		var old := mesh.material_override as StandardMaterial3D
		if old == null:
			continue
		if old.emission_enabled:
			# The driving code keeps controlling the existing lamp's emission energy.
			# A darker lens remains red when braking instead of clipping to pink.
			old.albedo_color = Color("a82426")
			old.emission = Color("550a05")
			old.metallic = 0.0
			old.roughness = 0.45
			old.metallic_specular = 0.2
			old.resource_name = "Restrained red tail lamp"
		elif is_equal_approx(old.metallic, 0.22):
			mesh.material_override = paint
			if mesh.mesh is ArrayMesh:
				mesh.mesh = _body_mesh()
				mesh.name = "FacetedBody"
			elif mesh.mesh is BoxMesh:
				var size: Vector3 = mesh.mesh.size
				if size.is_equal_approx(Vector3(0.07, 0.6, 0.07)):
					mesh.position = Vector3(signf(mesh.position.x) * 0.695, 1.01, -0.42)
					mesh.rotation.x = atan2(0.44, 0.54)
					size.y = Vector2(0.44, 0.54).length()
				elif size.is_equal_approx(Vector3(0.07, 0.5, 0.08)):
					mesh.position = Vector3(signf(mesh.position.x) * 0.695, 1.01, 0.76)
					mesh.rotation.x = -atan2(0.24, 0.54)
					size.y = Vector2(0.24, 0.54).length()
				mesh.mesh = _chamfered_box(size, minf(0.045, minf(size.x, minf(size.y, size.z)) * 0.24))
		elif is_equal_approx(old.metallic, 0.7):
			mesh.material_override = glass
			mesh.mesh = _cabin_mesh()
			mesh.rotation.x = 0.0
			mesh.name = "SlopedGlazing"
		elif is_equal_approx(old.metallic, 0.8):
			mesh.material_override = metal
		elif is_equal_approx(old.metallic, 0.5):
			mesh.material_override = plate if mesh.position.z > 2.0 else lamp
			if mesh.position.z < 0.0 and mesh.mesh is BoxMesh:
				# Seat the lens in the front fascia rather than above the bonnet.
				mesh.position.y = 0.55
				mesh.position.z = -2.205
				mesh.mesh = _chamfered_box(mesh.mesh.size, 0.018)
		else:
			mesh.material_override = rubber
	visual.set_meta("stylized_materials", true)

static func _material(label: String, color: Color, metallic: float, roughness: float, specular: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.resource_name = label
	# Godot Color properties use sRGB values; no extra manual gamma conversion.
	material.albedo_color = color
	material.metallic = metallic
	material.roughness = roughness
	material.metallic_specular = specular
	material.cull_mode = BaseMaterial3D.CULL_BACK
	return material

static func _polygon(st: SurfaceTool, points: Array[Vector3], normal: Vector3) -> void:
	for i in range(1, points.size() - 1):
		var a := points[0]
		var b := points[i]
		var c := points[i + 1]
		# Godot's front faces use clockwise winding.
		if (b - a).cross(c - a).dot(normal) > 0.0:
			var swap := b
			b = c
			c = swap
		for point in [a, b, c]:
			st.set_normal(normal.normalized())
			st.add_vertex(point)

static func _chamfered_box(size: Vector3, bevel: float) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var half := size * 0.5
	var inner := half - Vector3.ONE * bevel
	# Six broad planes, twelve small bevel planes, eight triangular corners.
	for axis in range(3):
		var j := (axis + 1) % 3
		var k := (axis + 2) % 3
		for sign_value in [-1.0, 1.0]:
			var face: Array[Vector3] = []
			for corner in [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]:
				var point := Vector3.ZERO
				point[axis] = half[axis] * sign_value
				point[j] = inner[j] * corner.x
				point[k] = inner[k] * corner.y
				face.append(point)
			var normal := Vector3.ZERO
			normal[axis] = sign_value
			_polygon(st, face, normal)
	for axis in range(3):
		var j := (axis + 1) % 3
		var k := (axis + 2) % 3
		for sj in [-1.0, 1.0]:
			for sk in [-1.0, 1.0]:
				var face: Array[Vector3] = []
				for end in [-1.0, 1.0]:
					var a := Vector3.ZERO
					a[axis] = inner[axis] * end
					a[j] = half[j] * sj
					a[k] = inner[k] * sk
					var b := a
					b[j] = inner[j] * sj
					b[k] = half[k] * sk
					if end < 0.0:
						face.append(a)
						face.append(b)
					else:
						face.append(b)
						face.append(a)
				var normal := Vector3.ZERO
				normal[j] = sj
				normal[k] = sk
				_polygon(st, face, normal)
	for sx in [-1.0, 1.0]:
		for sy in [-1.0, 1.0]:
			for sz in [-1.0, 1.0]:
				var corner := Vector3(sx, sy, sz)
				var face: Array[Vector3] = []
				for axis in range(3):
					var point := inner * corner
					point[axis] = half[axis] * corner[axis]
					face.append(point)
				_polygon(st, face, corner)
	return st.commit()

static func _body_ring(width: float, top: float, z: float) -> Array[Vector3]:
	return [Vector3(-width + 0.12, 0.34, z), Vector3(-width, 0.44, z), Vector3(-width, top - 0.1, z), Vector3(-width + 0.13, top, z), Vector3(width - 0.13, top, z), Vector3(width, top - 0.1, z), Vector3(width, 0.44, z), Vector3(width - 0.12, 0.34, z)]

static func _body_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var sections := [Vector3(0.75, 0.62, -2.15), Vector3(0.94, 0.78, -1.6), Vector3(0.96, 0.83, 0.65), Vector3(0.88, 0.76, 2.02)]
	for i in range(sections.size() - 1):
		var a: Vector3 = sections[i]
		var b: Vector3 = sections[i + 1]
		var first := _body_ring(a.x, a.y, a.z)
		var second := _body_ring(b.x, b.y, b.z)
		for j in range(first.size()):
			var k := (j + 1) % first.size()
			var normal := (second[j] - first[j]).cross(first[k] - first[j]).normalized()
			_polygon(st, [first[j], first[k], second[k], second[j]], normal)
	var front: Vector3 = sections[0]
	var rear: Vector3 = sections[-1]
	_polygon(st, _body_ring(front.x, front.y, front.z), Vector3.FORWARD)
	_polygon(st, _body_ring(rear.x, rear.y, rear.z), Vector3.BACK)
	return st.commit()

static func _cabin_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var lower: Array[Vector3] = [Vector3(-0.73, -0.27, -0.76), Vector3(0.73, -0.27, -0.76), Vector3(0.73, -0.27, 0.76), Vector3(-0.73, -0.27, 0.76)]
	var upper: Array[Vector3] = [Vector3(-0.66, 0.27, -0.32), Vector3(0.66, 0.27, -0.32), Vector3(0.66, 0.27, 0.52), Vector3(-0.66, 0.27, 0.52)]
	for i in range(4):
		var k := (i + 1) % 4
		var normal := (upper[i] - lower[i]).cross(lower[k] - lower[i]).normalized()
		_polygon(st, [lower[i], lower[k], upper[k], upper[i]], normal)
	_polygon(st, upper, Vector3.UP)
	_polygon(st, lower, Vector3.DOWN)
	return st.commit()

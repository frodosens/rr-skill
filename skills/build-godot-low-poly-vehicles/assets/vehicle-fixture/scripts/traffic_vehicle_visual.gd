extends Node3D
## Five shared low-poly traffic silhouettes. Local -Z is forward; tires touch y=0.
## Geometry is built once per kind and shared. No lights, physics, textures or
## automatic frame processing: the traffic controller calls set_motion().

const KINDS := ["taxi", "truck", "sedan_a", "sedan_b", "hatchback"]
const PAINT := 0
const TRIM := 1
const GLASS := 2
const METAL := 3
const HEADLAMP := 4
const TAILLAMP := 5
const MAX_TRIANGLES := 1400
const MAX_DRAW_SURFACES := 8
# Finite, shared civil-traffic paints. Taxi yellow is deliberately not recycled.
const POOL_PAINTS := [Color("3b677f"), Color("945438"), Color("a6a18b"), Color("477b63"), Color("bdc6c2"), Color("263b52"), Color("343c42"), Color("8a3b3b"), Color("8e999e"), Color("9a8469")]

@export_enum("taxi", "truck", "sedan_a", "sedan_b", "hatchback") var kind := "sedan_a"
var wheel_roll := 0.0
var current_paint := Color.WHITE
var pool_palette_index := -1
# CPU transforms remain inspectable with Godot's dummy/headless renderer.
var wheel_transforms: Array[Transform3D] = []
var _wheel_radius := 0.33
var _wheel_positions: Array[Vector3] = []
var _wheels: MultiMeshInstance3D
var _body: MeshInstance3D
var _tail_material: StandardMaterial3D
var _built := false
static var _body_cache: Dictionary = {}
static var _wheel_cache: Dictionary = {}
static var _materials: Array[StandardMaterial3D] = []
static var _paint_cache: Dictionary = {}

static func dimensions(model_kind: String) -> Vector3:
	var size := _geometry_dimensions(model_kind)
	# Includes the complete ±0.55 rad front-wheel steering/rolling envelope.
	# Keep mounts tied to the fixed body dimensions, not this clearance width.
	size.x += 0.40 if model_kind == "truck" else 0.30
	return size

static func _geometry_dimensions(model_kind: String) -> Vector3:
	match model_kind:
		"taxi": return Vector3(2.10, 1.65, 4.60)
		"truck": return Vector3(2.35, 2.85, 6.20)
		"sedan_b": return Vector3(2.15, 1.55, 4.85)
		"hatchback": return Vector3(1.98, 1.62, 3.90)
	return Vector3(2.06, 1.48, 4.35)

static func default_color(model_kind: String) -> Color:
	match model_kind:
		"taxi": return Color("b68a18")
		"truck": return Color("945438")
		"sedan_b": return Color("a6a18b")
		"hatchback": return Color("477b63")
	return Color("3b677f")

static func create(model_kind: String) -> Node3D:
	var visual := load("res://scripts/traffic_vehicle_visual.gd").new() as Node3D
	visual.configure(model_kind)
	return visual

func _ready() -> void:
	if not _built:
		configure(kind)

func configure(model_kind: String, color: Color = Color.TRANSPARENT) -> void:
	kind = model_kind if model_kind in KINDS else "sedan_a"
	for child in get_children():
		remove_child(child)
		child.free()
	_ensure_materials()
	# Warm the bounded palette once; pool reuse never allocates a material.
	for choice: Color in POOL_PAINTS:
		_paint_material(choice)
	current_paint = default_color(kind) if color.a <= 0.0 or kind == "taxi" else color
	pool_palette_index = -1
	var paint_material := _paint_material(current_paint)
	if not _body_cache.has(kind):
		_body_cache[kind] = _build_body(kind)
	_body = MeshInstance3D.new()
	_body.name = "Chassis"
	_body.mesh = _body_cache[kind]
	_body.set_surface_override_material(PAINT, paint_material)
	_tail_material = _materials[TAILLAMP].duplicate() as StandardMaterial3D
	_body.set_surface_override_material(TAILLAMP, _tail_material)
	add_child(_body)
	_wheel_radius = 0.43 if kind == "truck" else (0.32 if kind == "hatchback" else 0.33)
	var wheel_key := str(_wheel_radius)
	if not _wheel_cache.has(wheel_key):
		_wheel_cache[wheel_key] = _build_wheel(_wheel_radius)
	_wheels = MultiMeshInstance3D.new()
	_wheels.name = "FourRollingWheels"
	var instances := MultiMesh.new()
	instances.transform_format = MultiMesh.TRANSFORM_3D
	instances.mesh = _wheel_cache[wheel_key]
	# Slerp rotating wheel bases instead of shrinking them between physics ticks.
	instances.physics_interpolation_quality = MultiMesh.INTERP_QUALITY_HIGH
	instances.instance_count = 4
	_wheels.multimesh = instances
	add_child(_wheels)
	var size := _geometry_dimensions(kind)
	var x := size.x * 0.5 - 0.16
	var front := -size.z * (0.31 if kind == "truck" else 0.30)
	var rear := size.z * (0.30 if kind == "truck" else 0.28)
	_wheel_positions = [Vector3(-x, _wheel_radius, front), Vector3(x, _wheel_radius, front), Vector3(-x, _wheel_radius, rear), Vector3(x, _wheel_radius, rear)]
	wheel_roll = 0.0
	wheel_transforms.resize(4)
	_built = true
	set_meta("traffic_kind", kind)
	set_meta("dimensions", dimensions(kind))
	set_meta("local_forward", Vector3.FORWARD)
	set_motion(0.0, 0.0, 0.0, 0.0)

static func _paint_material(color: Color) -> StandardMaterial3D:
	_ensure_materials()
	var key := color.to_html(false)
	if not _paint_cache.has(key):
		var material := _materials[PAINT].duplicate() as StandardMaterial3D
		material.resource_name = "Traffic paint " + key
		material.albedo_color = Color(color.r, color.g, color.b, 1.0)
		_paint_cache[key] = material
	return _paint_cache[key]

func set_pool_color(reuse_index: int) -> void:
	if not _built or kind == "taxi":
		return
	pool_palette_index = posmod(reuse_index + KINDS.find(kind) * 3, POOL_PAINTS.size())
	current_paint = POOL_PAINTS[pool_palette_index]
	# Only swap the chassis paint binding. Geometry, wheel state and each car's
	# brake material remain unchanged. Never mutate a shared paint resource.
	_body.set_surface_override_material(PAINT, _paint_cache[current_paint.to_html(false)])

func set_motion(speed_mps: float, steering_angle: float, braking: float, delta: float) -> void:
	if not _built:
		return
	if not is_finite(speed_mps) or not is_finite(steering_angle) or not is_finite(braking) or not is_finite(delta):
		return
	# Forward (-Z) travel rotates wheels about local -X.
	wheel_roll = fposmod(wheel_roll - speed_mps * clampf(delta, 0.0, 0.1) / _wheel_radius, TAU)
	var steer := clampf(steering_angle, -0.55, 0.55)
	for index in range(4):
		var basis := Basis(Vector3.UP, steer if index < 2 else 0.0) * Basis(Vector3.RIGHT, wheel_roll)
		wheel_transforms[index] = Transform3D(basis, _wheel_positions[index])
		_wheels.multimesh.set_instance_transform(index, wheel_transforms[index])
	_tail_material.emission_energy_multiplier = lerpf(0.22, 1.3, clampf(braking, 0.0, 1.0))

static func _ensure_materials() -> void:
	if not _materials.is_empty():
		return
	var colors := [Color.WHITE, Color("19232a"), Color("203c47"), Color("939d9c"), Color("c6c9b5"), Color("a52a25")]
	var labels := ["Traffic satin paint", "Traffic rubber and trim", "Traffic opaque glazing", "Traffic satin metal", "Traffic headlamp lens", "Traffic brake lens"]
	for index in range(colors.size()):
		var material := StandardMaterial3D.new()
		material.resource_name = labels[index]
		material.albedo_color = colors[index]
		material.vertex_color_use_as_albedo = true
		material.roughness = 0.90 if index == TRIM else (0.30 if index == GLASS else 0.55)
		material.metallic = 0.35 if index == METAL else 0.0
		material.metallic_specular = 0.20 if index != GLASS else 0.35
		material.cull_mode = BaseMaterial3D.CULL_BACK
		if index == TAILLAMP:
			material.emission_enabled = true
			material.emission = Color("5b0904")
			material.emission_energy_multiplier = 0.22
		_materials.append(material)

static func _builders() -> Array[SurfaceTool]:
	var result: Array[SurfaceTool] = []
	for slot in range(_materials.size()):
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		st.set_material(_materials[slot])
		result.append(st)
	return result

static func _finish(builders: Array[SurfaceTool]) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	for st in builders:
		st.commit(mesh)
	return mesh

static func _polygon(st: SurfaceTool, points: Array[Vector3], normal: Vector3, tint: Color = Color.WHITE) -> void:
	for index in range(1, points.size() - 1):
		var a := points[0]
		var b := points[index]
		var c := points[index + 1]
		if (b - a).cross(c - a).dot(normal) > 0.0:
			var swap := b
			b = c
			c = swap
		for point in [a, b, c]:
			st.set_normal(normal.normalized())
			st.set_color(tint)
			st.add_vertex(point)

static func _box(st: SurfaceTool, center: Vector3, size: Vector3, tint: Color = Color.WHITE) -> void:
	var half := size * 0.5
	for axis in range(3):
		var j := (axis + 1) % 3
		var k := (axis + 2) % 3
		for side in [-1.0, 1.0]:
			var corners: Array[Vector3] = []
			for corner in [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]:
				var point := center
				point[axis] += half[axis] * side
				point[j] += half[j] * corner.x
				point[k] += half[k] * corner.y
				corners.append(point)
			var normal := Vector3.ZERO
			normal[axis] = side
			_polygon(st, corners, normal, tint)

static func _ring(half_width: float, bottom: float, top: float, z: float) -> Array[Vector3]:
	var bevel := 0.09
	return [Vector3(-half_width + bevel, bottom, z), Vector3(-half_width, bottom + bevel, z), Vector3(-half_width, top - bevel, z), Vector3(-half_width + bevel, top, z), Vector3(half_width - bevel, top, z), Vector3(half_width, top - bevel, z), Vector3(half_width, bottom + bevel, z), Vector3(half_width - bevel, bottom, z)]

static func _loft(st: SurfaceTool, sections: Array[Vector3], bottom: float) -> void:
	for index in range(sections.size() - 1):
		var a := sections[index]
		var b := sections[index + 1]
		var first := _ring(a.x, bottom, a.y, a.z)
		var second := _ring(b.x, bottom, b.y, b.z)
		for j in range(first.size()):
			var k := (j + 1) % first.size()
			var normal := (second[j] - first[j]).cross(first[k] - first[j]).normalized()
			_polygon(st, [first[j], first[k], second[k], second[j]], normal)
	_polygon(st, _ring(sections[0].x, bottom, sections[0].y, sections[0].z), Vector3.FORWARD)
	_polygon(st, _ring(sections[-1].x, bottom, sections[-1].y, sections[-1].z), Vector3.BACK)

static func _cabin(builders: Array[SurfaceTool], width: float, floor_y: float, roof_y: float, front: float, back: float, roof_front: float, roof_back: float) -> void:
	var roof_width := width - 0.13
	var lower: Array[Vector3] = [Vector3(-width, floor_y, front), Vector3(width, floor_y, front), Vector3(width, floor_y, back), Vector3(-width, floor_y, back)]
	var upper: Array[Vector3] = [Vector3(-roof_width, roof_y, roof_front), Vector3(roof_width, roof_y, roof_front), Vector3(roof_width, roof_y, roof_back), Vector3(-roof_width, roof_y, roof_back)]
	for i in range(4):
		var next := (i + 1) % 4
		var normal := (upper[i] - lower[i]).cross(lower[next] - lower[i]).normalized()
		_polygon(builders[GLASS], [lower[i], lower[next], upper[next], upper[i]], normal)
		# Painted edge pillars are inset onto the glazed planes, with no transparency.
		var along := (lower[next] - lower[i]).normalized() * 0.065
		var top_along := (upper[next] - upper[i]).normalized() * 0.065
		_polygon(builders[PAINT], [lower[i] + normal * 0.005, lower[i] + along + normal * 0.005, upper[i] + top_along + normal * 0.005, upper[i] + normal * 0.005], normal)
		_polygon(builders[PAINT], [lower[next] - along + normal * 0.006, lower[next] + normal * 0.006, upper[next] + normal * 0.006, upper[next] - top_along + normal * 0.006], normal)
	_box(builders[PAINT], Vector3(0, roof_y + 0.025, (roof_front + roof_back) * 0.5), Vector3(roof_width * 2.0 + 0.035, 0.055, roof_back - roof_front + 0.035))
	for side in [-1.0, 1.0]:
		var center_z := lerpf(roof_front, roof_back, 0.52)
		_polygon(builders[TRIM], [Vector3(side * (width + 0.005), floor_y, center_z - 0.045), Vector3(side * (width + 0.005), floor_y, center_z + 0.045), Vector3(side * (roof_width + 0.005), roof_y, center_z + 0.045), Vector3(side * (roof_width + 0.005), roof_y, center_z - 0.045)], Vector3(side, 0.2, 0).normalized())

static func _build_body(model_kind: String) -> ArrayMesh:
	var b := _builders()
	var size := _geometry_dimensions(model_kind)
	var half_width := size.x * 0.5 - 0.18
	var half_length := size.z * 0.5
	if model_kind == "truck":
		_build_truck(b)
	else:
		var hatch := model_kind == "hatchback"
		var long_sedan := model_kind == "sedan_b"
		var top := 0.90 if hatch else 0.85
		_loft(b[PAINT], [Vector3(half_width - 0.08, top - 0.10, -half_length + 0.04), Vector3(half_width, top, -half_length + 0.48), Vector3(half_width, top + 0.025, half_length - 0.62), Vector3(half_width - 0.06, top - 0.035, half_length - 0.04)], 0.34)
		var roof := 1.51 if hatch else (1.44 if long_sedan else 1.37)
		var front := -0.97 if hatch else (-1.02 if long_sedan else -0.95)
		var back := 1.83 if hatch else (1.24 if long_sedan else 1.11)
		var roof_front := -0.47 if hatch else (-0.43 if long_sedan else -0.34)
		var roof_back := 1.25 if hatch else (0.85 if long_sedan else 0.69)
		_cabin(b, half_width - 0.12, top + 0.025, roof, front, back, roof_front, roof_back)
		for side in [-1.0, 1.0]:
			_box(b[TRIM], Vector3(side * (half_width + 0.005), 0.49, 0), Vector3(0.035, 0.09, size.z - 0.50))
			var mirror_x := size.x * 0.5 - 0.065
			var stalk_start := half_width - 0.19
			_box(b[TRIM], Vector3(side * (stalk_start + mirror_x) * 0.5, 1.005, front + 0.14), Vector3(mirror_x - stalk_start, 0.035, 0.055))
			_box(b[PAINT], Vector3(side * (size.x * 0.5 - 0.065), 1.02, front + 0.14), Vector3(0.13, 0.13, 0.24))
			for z in [0.1, 0.86]:
				_box(b[METAL], Vector3(side * (half_width + 0.009), 0.87, z), Vector3(0.025, 0.033, 0.16))
			if hatch:
				_box(b[TAILLAMP], Vector3(side * (half_width - 0.12), 0.73, half_length - 0.045), Vector3(0.20, 0.19, 0.055))
			else:
				_box(b[TAILLAMP], Vector3(side * (half_width - 0.21), 0.69, half_length - 0.035), Vector3(0.39 if long_sedan else 0.31, 0.13, 0.06))
			_box(b[HEADLAMP], Vector3(side * (half_width - 0.21), 0.64, -half_length + 0.035), Vector3(0.35 if long_sedan else 0.29, 0.14, 0.06))
		_box(b[TRIM], Vector3(0, 0.49, -half_length + 0.035), Vector3(half_width * 1.65, 0.12, 0.06))
		_box(b[TRIM], Vector3(0, 0.47, half_length - 0.04), Vector3(half_width * 1.68, 0.10, 0.06))
		_box(b[TRIM], Vector3(0, 0.68, -half_length + 0.025), Vector3(0.48 if long_sedan else 0.35, 0.12, 0.04))
		_box(b[METAL], Vector3(0, 0.66, half_length - 0.02), Vector3(0.30, 0.105, 0.025))
		if hatch:
			_box(b[TRIM], Vector3(0, 1.515, 1.25), Vector3(1.30, 0.035, 0.18))
		elif long_sedan:
			_box(b[METAL], Vector3(0, 0.81, half_length - 0.045), Vector3(1.43, 0.025, 0.035))
		if model_kind == "taxi":
			_build_taxi_details(b, half_width)
	return _finish(b)

static func _build_taxi_details(b: Array[SurfaceTool], half_width: float) -> void:
	_box(b[TRIM], Vector3(0, 1.435, 0.12), Vector3(0.64, 0.055, 0.31))
	_box(b[HEADLAMP], Vector3(0, 1.535, 0.12), Vector3(0.57, 0.15, 0.24))
	# Small geometric TAXI letters on both sides of the roof sign; no font/texture.
	var letters := ["111010010010010", "010101111101101", "101101010101101", "111010010010111"]
	for side in [-1.0, 1.0]:
		var z: float = 0.12 + side * 0.121
		for letter in range(4):
			for row in range(5):
				for col in range(3):
					if letters[letter][row * 3 + col] != "1":
						continue
					var x: float = (-0.222 + letter * 0.12 + col * 0.029) * side
					var y := 1.58 - row * 0.023
					_polygon(b[TRIM], [Vector3(x, y, z), Vector3(x + 0.026 * side, y, z), Vector3(x + 0.026 * side, y - 0.021, z), Vector3(x, y - 0.021, z)], Vector3(0, 0, side))
		_box(b[TRIM], Vector3(side * (half_width + 0.006), 0.75, 0.23), Vector3(0.018, 0.11, 1.84))
		for tile in range(12):
			var center_z := -0.62 + tile * 0.15
			_box(b[HEADLAMP], Vector3(side * (half_width + 0.018), 0.723 if tile % 2 == 0 else 0.777, center_z), Vector3(0.012, 0.051, 0.074))

static func _build_truck(b: Array[SurfaceTool]) -> void:
	_loft(b[PAINT], [Vector3(0.94, 1.25, -3.04), Vector3(1.02, 1.37, -2.72), Vector3(1.02, 1.37, -1.20)], 0.47)
	_cabin(b, 0.92, 1.36, 2.10, -2.94, -1.28, -2.59, -1.32)
	_box(b[TRIM], Vector3(0, 0.54, 0.73), Vector3(1.72, 0.22, 4.56))
	# Short delivery box, contrasting warm grey and a faceted overhanging roof.
	_loft(b[METAL], [Vector3(1.075, 2.79, -1.08), Vector3(1.09, 2.83, -0.95), Vector3(1.09, 2.83, 2.93), Vector3(1.04, 2.77, 3.04)], 0.86)
	for side in [-1.0, 1.0]:
		_box(b[TRIM], Vector3(side * 1.015, 1.63, -2.58), Vector3(0.28, 0.035, 0.045))
		_box(b[TRIM], Vector3(side * 1.155, 1.68, -2.58), Vector3(0.04, 0.24, 0.22))
		_box(b[PAINT], Vector3(side * 1.09, 1.23, 0.93), Vector3(0.015, 0.22, 3.78))
		for height in [1.0, 1.55, 2.28, 2.66]:
			_box(b[METAL], Vector3(side * 1.097, height, 0.95), Vector3(0.014, 0.03, 3.84), Color(0.77, 0.79, 0.77))
		_box(b[HEADLAMP], Vector3(side * 0.70, 0.96, -3.065), Vector3(0.32, 0.22, 0.06))
		_box(b[TAILLAMP], Vector3(side * 0.85, 0.70, 3.065), Vector3(0.27, 0.18, 0.06))
		_box(b[TRIM], Vector3(side * 0.51, 1.80, 3.047), Vector3(0.025, 1.61, 0.028))
		_box(b[TRIM], Vector3(side * 1.03, 0.66, -1.45), Vector3(0.13, 0.11, 0.52))
	_box(b[TRIM], Vector3(0, 1.78, 3.06), Vector3(0.025, 1.76, 0.025))
	_box(b[TRIM], Vector3(0, 0.58, -3.06), Vector3(2.0, 0.17, 0.07))
	_box(b[TRIM], Vector3(0, 0.62, 3.07), Vector3(2.0, 0.12, 0.06))
	_box(b[TRIM], Vector3(0, 1.04, -3.065), Vector3(0.72, 0.28, 0.04))
	_box(b[METAL], Vector3(0, 0.77, -3.08), Vector3(0.35, 0.11, 0.025))

static func _build_wheel(radius: float) -> ArrayMesh:
	var rubber := SurfaceTool.new()
	rubber.begin(Mesh.PRIMITIVE_TRIANGLES)
	rubber.set_material(_materials[TRIM])
	var metal := SurfaceTool.new()
	metal.begin(Mesh.PRIMITIVE_TRIANGLES)
	metal.set_material(_materials[METAL])
	var sections: Array[Vector2] = [Vector2(-0.12, radius * 0.89), Vector2(-0.09, radius), Vector2(0.09, radius), Vector2(0.12, radius * 0.89)]
	for index in range(sections.size() - 1):
		for step in range(10):
			var a := TAU * float(step) / 10.0 + PI / 10.0
			var c := TAU * float(step + 1) / 10.0 + PI / 10.0
			var first := sections[index]
			var second := sections[index + 1]
			var points: Array[Vector3] = [Vector3(first.x, sin(a) * first.y, cos(a) * first.y), Vector3(second.x, sin(a) * second.y, cos(a) * second.y), Vector3(second.x, sin(c) * second.y, cos(c) * second.y), Vector3(first.x, sin(c) * first.y, cos(c) * first.y)]
			var normal := (points[1] - points[0]).cross(points[2] - points[0]).normalized()
			_polygon(rubber, points, normal)
	for side in [-1.0, 1.0]:
		var disc: Array[Vector3] = []
		for step in range(10):
			var angle := TAU * float(step) / 10.0 + PI / 10.0
			disc.append(Vector3(side * 0.12, sin(angle) * radius * 0.89, cos(angle) * radius * 0.89))
		_polygon(rubber, disc, Vector3(side, 0, 0))
		var rim: Array[Vector3] = []
		for step in range(10):
			var angle := TAU * float(step) / 10.0 + PI / 10.0
			rim.append(Vector3(side * 0.122, sin(angle) * radius * 0.57, cos(angle) * radius * 0.57))
		_polygon(metal, rim, Vector3(side, 0, 0))
		for spoke in range(5):
			var angle := TAU * float(spoke) / 5.0
			var p := Vector3(side * 0.124, sin(angle) * radius * 0.39, cos(angle) * radius * 0.39)
			var tangent := Vector3(0, cos(angle), -sin(angle)) * 0.027
			var radial := Vector3(0, sin(angle), cos(angle)) * radius * 0.14
			_polygon(rubber, [p - radial - tangent, p + radial - tangent, p + radial + tangent, p - radial + tangent], Vector3(side, 0, 0))
	return _finish([rubber, metal])

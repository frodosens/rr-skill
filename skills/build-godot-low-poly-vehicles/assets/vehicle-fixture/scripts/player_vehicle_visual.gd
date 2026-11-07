extends RefCounted
## Original stylized, low-poly interpretation of a blue wide-body rally hatch.
## Visual only: the existing player chassis, contacts and drivetrain are reused.
## No manufacturer logos, third-party meshes, textures, lights or live generators.

const RED_COUPE := "red_coupe"
const BLUE_RALLY := "blue_rally"
const VEHICLE_IDS := [RED_COUPE, BLUE_RALLY]
const VEHICLE_LABELS := ["RED COUPE", "BLUE RALLY"]
const Style = preload("res://scripts/car_visual_style.gd")

var _surfaces: Dictionary = {}
var _materials: Dictionary = {}

static func create() -> Dictionary:
	var builder := new()
	return builder._build()

func _make_materials() -> void:
	_materials = {
		"RallyBluePaint": Style._material("Rally blue paint", Color("0a318b"), 0.10, 0.46, 0.26),
		"DarkTrim": Style._material("Matte rubber and trim", Color("17232b"), 0.0, 0.9, 0.16),
		"OpaqueGlass": Style._material("Opaque blue grey glazing", Color("213846"), 0.0, 0.31, 0.35),
		"GoldAlloy": Style._material("Satin gold wheel alloy", Color("8d6c2e"), 0.55, 0.43, 0.38),
		"LampLens": Style._material("Frosted clear lamp lens", Color("748a96"), 0.0, 0.40, 0.26),
		"SteelDetail": Style._material("Satin steel details", Color("52606b"), 0.60, 0.58, 0.28),
		"TailLens": Style._material("Restrained red tail lamp", Color("992524"), 0.0, 0.45, 0.2),
	}
	var tail := _materials["TailLens"] as StandardMaterial3D
	tail.emission_enabled = true
	tail.emission = Color("550a05")
	tail.emission_energy_multiplier = 0.4

func _build() -> Dictionary:
	_make_materials()
	var visual := Node3D.new()
	visual.name = "BlueRallyVisual"
	visual.set_meta("vehicle_id", BLUE_RALLY)
	visual.set_meta("inspiration", "2007–2010 GR wide-body rally hatch; original low-poly interpretation")
	visual.set_meta("stylized_materials", true)
	visual.set_meta("rear_widebody", true)
	_body_shell()
	_front_details()
	_greenhouse()
	_rear_details()
	_side_details()
	_flush(visual)
	var tails: Array[MeshInstance3D] = []
	for side in [-1.0, 1.0]:
		_box("TailLens", Vector3(0.39, 0.13, 0.055), Vector3(side * 0.66, 0.89, 2.045))
		var tail_mesh := _flush(visual)[0] as MeshInstance3D
		tail_mesh.name = "TailLampLeft" if side < 0.0 else "TailLampRight"
		tails.append(tail_mesh)
	var wheels: Array[Node3D] = []
	var front: Array[Node3D] = []
	for side in [-1.0, 1.0]:
		for z in [-1.35, 1.31]:
			var pivot := Node3D.new()
			pivot.name = ("Front" if z < 0.0 else "Rear") + ("LeftWheel" if side < 0.0 else "RightWheel")
			pivot.position = Vector3(side * 0.91, 0.38, z)
			visual.add_child(pivot)
			var spinner := Node3D.new()
			spinner.name = "Spinner"
			pivot.add_child(spinner)
			_wheel(side)
			_flush(spinner)
			wheels.append(pivot)
			if z < 0.0:
				front.append(pivot)
	return {"visual": visual, "wheels": wheels, "front_wheels": front, "tail_lights": tails}

func _surface(material: String) -> SurfaceTool:
	if not _surfaces.has(material):
		var surface := SurfaceTool.new()
		surface.begin(Mesh.PRIMITIVE_TRIANGLES)
		_surfaces[material] = surface
	return _surfaces[material]

func _face(material: String, points: Array[Vector3], normal: Vector3) -> void:
	# Derive each flat facet normal from the geometry; the hint chooses outward.
	for index in range(1, points.size() - 1):
		var facet := (points[index] - points[0]).cross(points[index + 1] - points[0])
		if facet.length_squared() < 0.00000001:
			continue
		facet = facet.normalized()
		if facet.dot(normal) < 0.0:
			facet = -facet
		Style._polygon(_surface(material), [points[0], points[index], points[index + 1]], facet)

func _quad(material: String, a: Vector3, b: Vector3, c: Vector3, d: Vector3, normal: Vector3) -> void:
	_face(material, [a, b, c, d], normal)

func _box(material: String, size: Vector3, at: Vector3, rotation: Vector3 = Vector3.ZERO) -> void:
	var basis := Basis.from_euler(rotation)
	var half := size * 0.5
	for axis in range(3):
		var j := (axis + 1) % 3
		var k := (axis + 2) % 3
		for side in [-1.0, 1.0]:
			var points: Array[Vector3] = []
			for corner in [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]:
				var p := Vector3.ZERO
				p[axis] = half[axis] * side
				p[j] = half[j] * corner.x
				p[k] = half[k] * corner.y
				points.append(at + basis * p)
			var normal := Vector3.ZERO
			normal[axis] = side
			_face(material, points, basis * normal)

func _flush(parent: Node3D) -> Array[MeshInstance3D]:
	var meshes: Array[MeshInstance3D] = []
	for key: String in _surfaces:
		var mesh := MeshInstance3D.new()
		mesh.name = key
		mesh.mesh = _surfaces[key].commit()
		mesh.material_override = _materials[key]
		parent.add_child(mesh)
		meshes.append(mesh)
	_surfaces.clear()
	return meshes

func _width(z: float) -> float:
	var width := 0.88
	for wheel_z in [-1.35, 1.31]:
		# Rear haunches spread farther into the quarter panel than the fronts.
		# Keep the wheels/contact track unchanged and the full body under 2.2 m.
		var rear: bool = wheel_z > 0.0
		var flare := 0.20 if rear else 0.13
		var reach := 0.85 if rear else 0.65
		width = maxf(width, 0.88 + flare * maxf(0.0, 1.0 - absf(z - wheel_z) / reach))
	if z < -1.86:
		width = lerpf(0.81, 0.91, clampf((z + 2.16) / 0.30, 0.0, 1.0))
	if z > 1.83:
		width = lerpf(0.93, 0.84, clampf((z - 1.83) / 0.23, 0.0, 1.0))
	return width

func _arch_bottom(z: float) -> float:
	for wheel_z in [-1.35, 1.31]:
		var d := absf(z - wheel_z)
		if d <= 0.44:
			return 0.38 + sqrt(maxf(0.0, 0.44 * 0.44 - d * d))
	return 0.33

func _belt_height(z: float) -> float:
	return lerpf(0.76, 0.95, clampf((z + 2.16) / 1.1, 0.0, 1.0)) if z < -1.06 else 0.95

func _body_shell() -> void:
	var zs: Array[float] = [-2.16, -1.86, -1.79, -1.73, -1.59, -1.35, -1.11, -0.97, -0.91, -0.68, 0.0, 0.35, 0.46, 0.64, 0.87, 0.93, 1.07, 1.31, 1.55, 1.69, 1.75, 1.83, 2.06]
	for side in [-1.0, 1.0]:
		for i in range(zs.size() - 1):
			var za := zs[i]
			var zb := zs[i + 1]
			var wa := _width(za)
			var wb := _width(zb)
			var ya := _arch_bottom(za)
			var yb := _arch_bottom(zb)
			var ta := _belt_height(za)
			var tb := _belt_height(zb)
			_quad("RallyBluePaint", Vector3(side * wa, ya, za), Vector3(side * wb, yb, zb), Vector3(side * wb, tb - 0.1, zb), Vector3(side * wa, ta - 0.1, za), Vector3(side, 0, 0))
			_quad("RallyBluePaint", Vector3(side * wa, ta - 0.1, za), Vector3(side * wb, tb - 0.1, zb), Vector3(side * (wb - 0.10), tb, zb), Vector3(side * (wa - 0.10), ta, za), Vector3(side, 1.0, 0).normalized())
			# Narrow return surface gives a real wheel-opening edge, not black decals.
			_quad("DarkTrim", Vector3(side * wa, ya, za), Vector3(side * (wa - 0.07), ya, za), Vector3(side * (wb - 0.07), yb, zb), Vector3(side * wb, yb, zb), Vector3(0, -1, 0))
		for wheel_z in [-1.35, 1.31]:
			var rear: bool = wheel_z > 0.0
			var outer_radius := 0.535 if rear else 0.49
			for segment in range(10):
				var a := PI * float(segment) / 10.0
				var b := PI * float(segment + 1) / 10.0
				var za: float = wheel_z + cos(a) * 0.445
				var zb: float = wheel_z + cos(b) * 0.445
				var oza: float = wheel_z + cos(a) * outer_radius
				var ozb: float = wheel_z + cos(b) * outer_radius
				var inner_a: float = minf(1.085, _width(za) + 0.03) if rear else 1.005
				var inner_b: float = minf(1.085, _width(zb) + 0.03) if rear else 1.005
				var outer_a: float = _width(oza) - 0.01 if rear else 0.985
				var outer_b: float = _width(ozb) - 0.01 if rear else 0.985
				var pa := Vector3(side * inner_a, 0.38 + sin(a) * 0.445, za)
				var pb := Vector3(side * inner_b, 0.38 + sin(b) * 0.445, zb)
				var qa := Vector3(side * outer_a, 0.38 + sin(a) * outer_radius, oza)
				var qb := Vector3(side * outer_b, 0.38 + sin(b) * outer_radius, ozb)
				_quad("RallyBluePaint", pa, pb, qb, qa, Vector3(side, 0, 0))
				if rear:
					# A small inner return gives the wider flare thickness from behind.
					_quad("DarkTrim", pa, pb, pb - Vector3(side * 0.045, 0, 0), pa - Vector3(side * 0.045, 0, 0), Vector3(0, -sin((a + b) * 0.5), -cos((a + b) * 0.5)))
	# Top faces retain the broad bonnet and compact five-door rear deck.
	for i in range(zs.size() - 1):
		var za := zs[i]
		var zb := zs[i + 1]
		_quad("RallyBluePaint", Vector3(-_width(za) + 0.10, _belt_height(za), za), Vector3(_width(za) - 0.10, _belt_height(za), za), Vector3(_width(zb) - 0.10, _belt_height(zb), zb), Vector3(-_width(zb) + 0.10, _belt_height(zb), zb), Vector3.UP)
	_box("RallyBluePaint", Vector3(1.66, 0.42, 0.15), Vector3(0, 0.54, -2.09))
	_box("RallyBluePaint", Vector3(1.68, 0.52, 0.16), Vector3(0, 0.64, 1.98))
	_box("DarkTrim", Vector3(1.40, 0.05, 3.95), Vector3(0, 0.31, -0.01))

func _front_details() -> void:
	# Low central grille and swept, two-element headlamp shapes.
	_face("DarkTrim", [Vector3(-0.46, 0.74, -2.176), Vector3(0.46, 0.74, -2.176), Vector3(0.38, 0.57, -2.176), Vector3(-0.38, 0.57, -2.176)], Vector3.FORWARD)
	_box("RallyBluePaint", Vector3(0.82, 0.028, 0.018), Vector3(0, 0.65, -2.19))
	_box("DarkTrim", Vector3(0.96, 0.17, 0.02), Vector3(0, 0.43, -2.178))
	_box("DarkTrim", Vector3(1.72, 0.045, 0.20), Vector3(0, 0.29, -2.1))
	for side in [-1.0, 1.0]:
		_face("LampLens", [Vector3(side * 0.44, 0.75, -2.197), Vector3(side * 0.80, 0.75, -2.197), Vector3(side * 0.82, 0.64, -2.197), Vector3(side * 0.51, 0.61, -2.197)], Vector3.FORWARD)
		_face("LampLens", [Vector3(side * 0.80, 0.75, -2.197), Vector3(side * 0.91, 0.79, -1.96), Vector3(side * 0.91, 0.68, -1.96), Vector3(side * 0.82, 0.64, -2.197)], Vector3(side, 0, -0.2).normalized())
		_box("SteelDetail", Vector3(0.018, 0.10, 0.013), Vector3(side * 0.64, 0.69, -2.209))
		_box("DarkTrim", Vector3(0.20, 0.17, 0.025), Vector3(side * 0.65, 0.44, -2.178))
		_disk_z("LampLens", 0.052, Vector3(side * 0.65, 0.44, -2.196), 10)
		_box("SteelDetail", Vector3(0.16, 0.018, 0.025), Vector3(side * 0.65, 0.54, -2.195))
	# Integrated tapered bonnet scoop, with a low dark intake and blue upper lip.
	_quad("RallyBluePaint", Vector3(-0.36, 1.055, -1.28), Vector3(0.36, 1.055, -1.28), Vector3(0.27, 0.962, -0.78), Vector3(-0.27, 0.962, -0.78), Vector3.UP)
	_box("DarkTrim", Vector3(0.63, 0.075, 0.022), Vector3(0, 1.00, -1.284))
	_box("RallyBluePaint", Vector3(0.72, 0.026, 0.026), Vector3(0, 1.047, -1.29))
	for side in [-1.0, 1.0]:
		_face("RallyBluePaint", [Vector3(side * 0.36, 0.95, -1.28), Vector3(side * 0.36, 1.055, -1.28), Vector3(side * 0.27, 0.962, -0.78)], Vector3(side, 0, 0))

func _greenhouse() -> void:
	# The whole cabin is a five-door hatch profile with properly sloped glass.
	var lower: Array[Vector3] = [Vector3(-0.78, 0.95, -0.72), Vector3(0.78, 0.95, -0.72), Vector3(0.79, 0.98, 1.89), Vector3(-0.79, 0.98, 1.89)]
	var upper: Array[Vector3] = [Vector3(-0.67, 1.47, -0.19), Vector3(0.67, 1.47, -0.19), Vector3(0.69, 1.47, 1.24), Vector3(-0.69, 1.47, 1.24)]
	for i in range(4):
		var j := (i + 1) % 4
		var n := (upper[i] - lower[i]).cross(lower[j] - lower[i]).normalized()
		_quad("OpaqueGlass", lower[i], lower[j], upper[j], upper[i], n)
	_quad("RallyBluePaint", upper[0], upper[1], upper[2], upper[3], Vector3.UP)
	_box("RallyBluePaint", Vector3(1.36, 0.055, 1.44), Vector3(0, 1.49, 0.51))
	for side in [-1.0, 1.0]:
		_beam("RallyBluePaint", Vector3(side * 0.785, 0.96, -0.72), Vector3(side * 0.675, 1.48, -0.19), 0.055)
		_beam("RallyBluePaint", Vector3(side * 0.79, 0.98, 1.89), Vector3(side * 0.69, 1.48, 1.24), 0.10)
		_beam("DarkTrim", Vector3(side * 0.785, 0.97, 0.38), Vector3(side * 0.69, 1.47, 0.38), 0.065)
		_beam("DarkTrim", Vector3(side * 0.79, 0.98, 1.24), Vector3(side * 0.70, 1.46, 1.05), 0.045)
		_box("DarkTrim", Vector3(0.028, 0.042, 2.54), Vector3(side * 0.793, 0.971, 0.55))
		_box("RallyBluePaint", Vector3(0.23, 0.12, 0.27), Vector3(side * 0.94, 1.055, -0.57))
		_box("OpaqueGlass", Vector3(0.02, 0.08, 0.19), Vector3(side * 1.061, 1.055, -0.55))

func _rear_details() -> void:
	# Roof wing, high brake strip and pale rear light housings are GR cues.
	_box("RallyBluePaint", Vector3(1.58, 0.075, 0.43), Vector3(0, 1.53, 1.43), Vector3(-0.04, 0, 0))
	for side in [-1.0, 1.0]:
		_box("RallyBluePaint", Vector3(0.11, 0.17, 0.30), Vector3(side * 0.69, 1.44, 1.45))
		_box("LampLens", Vector3(0.42, 0.25, 0.06), Vector3(side * 0.66, 0.89, 2.015))
		_box("LampLens", Vector3(0.06, 0.18, 0.23), Vector3(side * 0.86, 0.88, 1.92))
		for offset in [-0.08, 0.08]:
			_annulus_z("SteelDetail", 0.063, 0.043, Vector3(side * 0.62 + offset, 0.31, 2.115), 10)
			_disk_z("DarkTrim", 0.043, Vector3(side * 0.62 + offset, 0.31, 2.108), 10)
	_box("TailLens", Vector3(0.49, 0.028, 0.025), Vector3(0, 1.515, 1.655))
	_box("DarkTrim", Vector3(1.38, 0.15, 0.09), Vector3(0, 0.34, 2.065))
	_box("DarkTrim", Vector3(0.53, 0.22, 0.025), Vector3(0, 0.63, 2.07))
	_box("LampLens", Vector3(0.41, 0.13, 0.028), Vector3(0, 0.63, 2.087))
	_box("RallyBluePaint", Vector3(0.69, 0.04, 0.04), Vector3(0, 0.80, 2.075))
	_box("DarkTrim", Vector3(0.53, 0.025, 0.035), Vector3(0.10, 1.10, 1.74), Vector3(0, 0, 0.07))

func _side_details() -> void:
	for side in [-1.0, 1.0]:
		_box("RallyBluePaint", Vector3(0.14, 0.12, 1.68), Vector3(side * 0.89, 0.34, 0))
		_box("DarkTrim", Vector3(0.012, 0.32, 0.012), Vector3(side * 0.887, 0.68, 0.35))
		for z in [0.18, 1.0]:
			_box("RallyBluePaint", Vector3(0.045, 0.035, 0.17), Vector3(side * (_width(z) + 0.023), 0.85, z))
		_box("DarkTrim", Vector3(0.025, 0.12, 0.19), Vector3(side * 0.90, 0.78, -0.78), Vector3(0.12, 0, 0))
		_box("SteelDetail", Vector3(0.028, 0.023, 0.17), Vector3(side * 0.916, 0.80, -0.78))

func _beam(material: String, a: Vector3, b: Vector3, width: float) -> void:
	var delta := b - a
	var basis := Basis.looking_at(delta.normalized(), Vector3.RIGHT)
	_box(material, Vector3(width, width, delta.length()), (a + b) * 0.5, basis.get_euler())

func _wheel(_side: float) -> void:
	# Four independently animated 20-sided tires, with real open split spokes.
	var segments := 20
	var rings := [Vector2(-0.14, 0.335), Vector2(-0.10, 0.37), Vector2(0.10, 0.37), Vector2(0.14, 0.335)]
	for i in range(rings.size() - 1):
		for segment in range(segments):
			var a := TAU * segment / segments
			var b := TAU * (segment + 1) / segments
			_quad("DarkTrim", _wheel_point(rings[i].x, rings[i].y, a), _wheel_point(rings[i].x, rings[i].y, b), _wheel_point(rings[i + 1].x, rings[i + 1].y, b), _wheel_point(rings[i + 1].x, rings[i + 1].y, a), Vector3(0, cos((a + b) * 0.5), sin((a + b) * 0.5)))
	for face_side in [-1.0, 1.0]:
		_annulus_x("DarkTrim", 0.335, 0.264, face_side * 0.14, segments, face_side)
		_annulus_x("GoldAlloy", 0.274, 0.237, face_side * 0.145, segments, face_side)
		_annulus_x("SteelDetail", 0.215, 0.060, face_side * 0.112, segments, face_side)
		_annulus_x("GoldAlloy", 0.071, 0.0, face_side * 0.151, 12, face_side)
		for spoke in range(8):
			for branch in [-1.0, 1.0]:
				var a := TAU * spoke / 8.0
				var b: float = a + branch * 0.14
				var inner_a := _wheel_point(face_side * 0.151, 0.063, a - 0.10)
				var inner_b := _wheel_point(face_side * 0.151, 0.063, a + 0.10)
				var outer_a := _wheel_point(face_side * 0.151, 0.246, b - 0.035)
				var outer_b := _wheel_point(face_side * 0.151, 0.246, b + 0.035)
				_quad("GoldAlloy", inner_a, outer_a, outer_b, inner_b, Vector3(face_side, 0, 0))
	# Caliper is intentionally omitted: it would spin with this simple visual rig.
	# Physics wheel radius/contact points remain exactly those of the original car.

func _wheel_point(x: float, radius: float, angle: float) -> Vector3:
	return Vector3(x, cos(angle) * radius, sin(angle) * radius)

func _annulus_x(material: String, outer: float, inner: float, x: float, segments: int, side: float) -> void:
	for segment in range(segments):
		var a := TAU * segment / segments
		var b := TAU * (segment + 1) / segments
		if inner <= 0.0:
			_face(material, [Vector3(x, 0, 0), _wheel_point(x, outer, a), _wheel_point(x, outer, b)], Vector3(side, 0, 0))
		else:
			_quad(material, _wheel_point(x, outer, a), _wheel_point(x, outer, b), _wheel_point(x, inner, b), _wheel_point(x, inner, a), Vector3(side, 0, 0))

func _disk_z(material: String, radius: float, at: Vector3, segments: int) -> void:
	for segment in range(segments):
		var a := TAU * segment / segments
		var b := TAU * (segment + 1) / segments
		_face(material, [at, at + Vector3(cos(a), sin(a), 0) * radius, at + Vector3(cos(b), sin(b), 0) * radius], Vector3.FORWARD if at.z < 0.0 else Vector3.BACK)

func _annulus_z(material: String, outer: float, inner: float, at: Vector3, segments: int) -> void:
	for segment in range(segments):
		var a := TAU * segment / segments
		var b := TAU * (segment + 1) / segments
		var da := Vector3(cos(a), sin(a), 0)
		var db := Vector3(cos(b), sin(b), 0)
		_quad(material, at + da * outer, at + db * outer, at + db * inner, at + da * inner, Vector3.BACK)

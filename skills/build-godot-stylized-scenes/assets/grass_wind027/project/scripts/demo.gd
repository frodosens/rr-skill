extends Node3D
const GrassField=preload("res://scripts/grass_field.gd")
var field: Node3D
var camera: Camera3D
var ground_material: StandardMaterial3D
var label: Label
var winter := false
var view := 1
var capture_mode := false
func _ready() -> void:
    var environment := Environment.new()
    environment.background_mode=Environment.BG_COLOR
    environment.background_color=Color("b8ccce")
    environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color=Color("abbfc3")
    environment.ambient_light_energy=0.63
    environment.tonemap_mode=Environment.TONE_MAPPER_LINEAR
    environment.fog_enabled=true
    environment.fog_light_color=Color("b8ccce")
    environment.fog_mode=Environment.FOG_MODE_DEPTH
    environment.fog_depth_begin=70.0
    environment.fog_depth_end=240.0
    environment.fog_density=0.5
    var env := WorldEnvironment.new()
    env.environment=environment
    add_child(env)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees=Vector3(-36.0,-46.0,0.0)
    sun.light_color=Color("fff0d5")
    sun.light_energy=0.86
    add_child(sun)
    make_ground()
    make_path()
    make_scenery()
    camera=Camera3D.new()
    camera.fov=57.0
    camera.far=260.0
    add_child(camera)
    set_view(1)
    field=GrassField.new()
    field.camera=camera
    add_child(field)
    field.update_lod(true)
    var canvas := CanvasLayer.new()
    add_child(canvas)
    var panel := ColorRect.new()
    panel.color=Color(0.035,0.055,0.045,0.78)
    panel.position=Vector2(22,22)
    panel.size=Vector2(520,112)
    canvas.add_child(panel)
    label=Label.new()
    label.position=Vector2(38,34)
    label.add_theme_font_size_override("font_size",18)
    canvas.add_child(label)
    update_label()

func update_label() -> void:
    var state := "SNOW / THINNED" if winter else "WARM MEADOW"
    var wind := "ON" if field.wind_enabled else "OFF"
    label.text="FIVE-CARD GRASS  /  %s\nWind %s   •   Root fixed   •   Bend = wind × height²\n[1] Wide  [2] Close  [3] High   [W] Wind   [S] Snow   [G] Grass"%[state,wind]

func set_view(index: int) -> void:
    view=index
    if index==1:
        camera.position=Vector3(17.5,4.5,31.0)
        camera.look_at(Vector3(0.0,1.2,-14.0))
    elif index==2:
        camera.position=Vector3(5.3,1.25,11.0)
        camera.look_at(Vector3(3.7,0.50,4.0))
    else:
        camera.position=Vector3(40.0,31.0,50.0)
        camera.look_at(Vector3(-4.0,0.0,-6.0))
    if field!=null: field.update_lod(true)

func set_winter(enabled: bool) -> void:
    winter=enabled
    field.set_winter(enabled)
    ground_material.albedo_color=Color("d7dfd8") if enabled else Color("a2a67c")
    update_label()

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo: return
    match event.physical_keycode:
        KEY_1: set_view(1)
        KEY_2: set_view(2)
        KEY_3: set_view(3)
        KEY_W: field.wind_enabled=not field.wind_enabled
        KEY_S: set_winter(not winter)
        KEY_G: field.visible=not field.visible
        KEY_ESCAPE: get_tree().quit()
    update_label()

func make_ground() -> void:
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    for z in range(-60,60,2):
        for x in range(-60,60,2):
            var points: Array[Vector3]=[]
            for p in [Vector2(x,z),Vector2(x,z+2),Vector2(x+2,z+2),Vector2(x+2,z)]:
                points.append(Vector3(p.x,GrassField.ground_height(p.x,p.y)-0.025,p.y))
            for index in [0,2,1,0,3,2]:
                st.add_vertex(points[index])
    st.generate_normals()
    var node := MeshInstance3D.new()
    node.mesh=st.commit()
    ground_material=StandardMaterial3D.new()
    ground_material.albedo_color=Color("a2a67c")
    ground_material.roughness=1.0
    node.material_override=ground_material
    add_child(node)

func make_path() -> void:
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    for z in range(-60,60):
        var points: Array[Vector3]=[]
        for pair in [Vector2(-2.48,z),Vector2(-2.48,z+1),Vector2(2.48,z+1),Vector2(2.48,z)]:
            var x: float=GrassField.path_center(pair.y)+pair.x
            points.append(Vector3(x,GrassField.ground_height(x,pair.y)+0.002,pair.y))
        for i in [0,2,1,0,3,2]: st.add_vertex(points[i])
    st.generate_normals()
    var node := MeshInstance3D.new()
    node.mesh=st.commit()
    var mat := StandardMaterial3D.new()
    mat.albedo_color=Color("a39578")
    mat.roughness=1.0
    node.material_override=mat
    add_child(node)

func make_scenery() -> void:
    var rng := RandomNumberGenerator.new()
    rng.seed=127
    for i in 34:
        var x := -48.0+float(i)*3.1+rng.randf_range(-2.0,2.0)
        var z := -39.0-rng.randf()*20.0
        var y := GrassField.ground_height(x,z)
        var height := rng.randf_range(6.0,11.0)
        var trunk := CylinderMesh.new()
        trunk.top_radius=0.16
        trunk.bottom_radius=0.3
        trunk.height=height*0.6
        trunk.radial_segments=5
        add_mesh(trunk,Vector3(x,y+height*0.3,z),Color("655f43"))
        for tier in 3:
            var crown := CylinderMesh.new()
            crown.top_radius=0.0
            crown.bottom_radius=height*(0.25-float(tier)*0.05)
            crown.height=height*0.46
            crown.radial_segments=7
            add_mesh(crown,Vector3(x,y+height*(0.48+float(tier)*0.18),z),Color("42634f").lerp(Color("688364"),float(tier)*0.23))
    for i in 6:
        var ridge := CylinderMesh.new()
        ridge.top_radius=0.0
        ridge.bottom_radius=34.0+float(i)*2.0
        ridge.height=25.0+float(i%3)*9.0
        ridge.radial_segments=7
        add_mesh(ridge,Vector3(-105.0+float(i)*40.0,ridge.height*0.5-8.0,-104.0-float(i%2)*12.0),Color("738c84"))

func add_mesh(mesh: Mesh,position_: Vector3,color: Color) -> void:
    var node := MeshInstance3D.new()
    node.mesh=mesh
    node.position=position_
    var mat := StandardMaterial3D.new()
    mat.albedo_color=color
    mat.roughness=1.0
    node.material_override=mat
    add_child(node)

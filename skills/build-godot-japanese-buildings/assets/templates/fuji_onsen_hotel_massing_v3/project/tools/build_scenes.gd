extends SceneTree
const BASE = "res://assets/fuji_destinations/"
var palette: Dictionary = {}
func _initialize() -> void:
    var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(BASE+"asset_manifest.json"))
    for key in manifest.materials:
        var mat := ShaderMaterial.new()
        mat.shader = load(BASE+"materials/destination_palette.gdshader")
        mat.resource_name = key
        var c: Array = manifest.materials[key]
        mat.set_shader_parameter("base_color",Color(c[0],c[1],c[2],1))
        mat.set_shader_parameter("is_water",key=="water")
        var error := ResourceSaver.save(mat,BASE+"materials/"+key+".tres")
        assert(error==OK)
        palette[key] = load(BASE+"materials/"+key+".tres")
    for group in ["modules","assemblies"]:
        for key in manifest[group]:
            build(key,manifest[group][key],group=="modules")
    print("SCENE_BUILD_COMPLETE: 2 guarded hotel scenes, 8 shared materials")
    quit()
func owner_all(n:Node,r:Node) -> void:
    n.scene_file_path=""
    n.owner=r
    for child in n.get_children(): owner_all(child,r)
func palette_all(n:Node,lod:int) -> void:
    if n is MeshInstance3D:
        n.mesh=n.mesh.duplicate()
        n.visibility_range_begin=0.0 if lod==0 else 110.0
        n.visibility_range_end=110.0 if lod==0 else 420.0
        n.visibility_range_begin_margin=0.0
        n.visibility_range_end_margin=0.0
        for surface in n.mesh.get_surface_count():
            var src=n.mesh.surface_get_material(surface)
            assert(src!=null and palette.has(src.resource_name),"Unknown material palette name")
            n.mesh.surface_set_material(surface,palette[src.resource_name])
            n.set_surface_override_material(surface,palette[src.resource_name])
    for child in n.get_children(): palette_all(child,lod)
func build(key:String,data:Dictionary,has_proxies:bool) -> void:
    var root:=Node3D.new();root.name=key
    root.set_meta("integration_status","unplaced_asset_only")
    root.set_meta("asset_version","0.3.0-massing-only")
    root.set_meta("front_axis","+Z")
    for lod in [0,1]:
        var model:Node3D=load(BASE+data.lods[str(lod)].file).instantiate()
        model.name="LOD%d"%lod;root.add_child(model);palette_all(model,lod);owner_all(model,root)
    if has_proxies:
        root.set_meta("shelter_descriptors",data.shelters)
        var body:=StaticBody3D.new();body.name="DISABLED_CollisionTemplates"
        body.collision_layer=0;body.collision_mask=0
        body.set_meta("guard","Enable only after support/ownership/drive tests; bridges require separate continuous road owner")
        root.add_child(body);body.owner=root
        for proxy in data.collision_proxies:
            var shape:=CollisionShape3D.new();shape.name=proxy.name
            var s:=BoxShape3D.new();s.size=Vector3(proxy.size[0],proxy.size[1],proxy.size[2]);shape.shape=s
            shape.position=Vector3(proxy.position[0],proxy.position[1],proxy.position[2])
            shape.disabled=true
            shape.set_meta("vehicle_surface_template",proxy.vehicle_surface)
            body.add_child(shape);shape.owner=root
    var marker:=Marker3D.new();marker.name="FrontStep";marker.position=Vector3(0,0.28,14.25);root.add_child(marker);marker.owner=root
    var packed:=PackedScene.new();assert(packed.pack(root)==OK)
    assert(ResourceSaver.save(packed,BASE+"scenes/"+key+".tscn")==OK)
    root.free()

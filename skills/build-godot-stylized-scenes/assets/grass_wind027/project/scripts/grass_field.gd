extends Node3D
## Reusable visual-only field. Each 12 m chunk has ONE MultiMeshInstance3D.
## All transforms and colors are seeded at creation; no per-clump CPU animation.
const CHUNK_SIZE := 12.0
const SIDE_CHUNKS := 8
const DENSITY := 4.5
const BASE_HEIGHT := 0.58
const MAX_WIND := 0.6
const LOD_DISTANCES := [24.0,48.0,96.0]
var material: ShaderMaterial
var meshes: Array[ArrayMesh] = []
var chunks: Array[Dictionary] = []
var camera: Camera3D
var wind_enabled := true
var snow_enabled := false
var fixed_time := -1.0
var wind_clock := 0.0
var lod_clock := 1.0
var clump_count := 0
var generation_ms := 0
var min_accepted_path_distance := INF
var generation_aabb_failures := 0
var stats := {}

static func ground_height(x: float,z: float) -> float:
    return 0.75*sin(x*0.065)*sin(z*0.042)+0.4*sin(z*0.09)
static func path_center(z: float) -> float:
    return -8.0+3.8*sin(z*0.046)

static func make_mesh(cards: int, segments: int) -> ArrayMesh:
    var vertices := PackedVector3Array()
    var normals := PackedVector3Array()
    var uvs := PackedVector2Array()
    var indices := PackedInt32Array()
    for card in cards:
        var angle: float = float(card)*PI/float(cards)+0.17
        var right := Vector3(cos(angle),0.0,sin(angle))
        var offset := Vector3(sin(angle*3.2),0.0,cos(angle*2.4))*0.065
        var height := BASE_HEIGHT*(0.87+0.13*sin(float(card)*2.7+0.6))
        var base := vertices.size()
        for row in segments+1:
            var h := float(row)/float(segments)
            for side in 2:
                vertices.append(offset+right*((float(side)-0.5)*0.8+h*h*0.075)+Vector3.UP*height*h)
                normals.append(Vector3.UP)
                uvs.append(Vector2(float(side),h))
        for row in segments:
            var i := base+row*2
            indices.append_array(PackedInt32Array([i,i+2,i+1,i+1,i+2,i+3]))
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX]=vertices
    arrays[Mesh.ARRAY_NORMAL]=normals
    arrays[Mesh.ARRAY_TEX_UV]=uvs
    arrays[Mesh.ARRAY_INDEX]=indices
    var mesh := ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
    return mesh

static func make_blade_texture() -> ImageTexture:
    # Bake once on the CPU. Fragment shaders only sample a tiny mipmapped mask.
    var image := Image.create(128,128,false,Image.FORMAT_RGBA8)
    for y in 128:
        var h := (float(y)+0.5)/128.0
        for x in 128:
            var u := (float(x)+0.5)/128.0
            var blade := floorf(u*7.0)
            var random_height := fposmod(sin(blade*37.17+1.9)*43758.54,1.0)
            var blade_height := 0.63+0.35*random_height
            var local_y := h/blade_height
            var center := 0.5+0.17*sin(blade*2.4)*local_y*local_y
            var width := 0.45*pow(maxf(1.0-local_y,0.0),0.73)
            var alpha := 1.0 if local_y<=1.0 and absf(fposmod(u*7.0,1.0)-center)<=width else 0.0
            image.set_pixel(x,y,Color(1.0,1.0,1.0,alpha))
    image.generate_mipmaps()
    return ImageTexture.create_from_image(image)

func _ready() -> void:
    var started := Time.get_ticks_msec()
    material=ShaderMaterial.new()
    material.shader=preload("res://shaders/grass.gdshader")
    material.set_shader_parameter("blade_mask",make_blade_texture())
    meshes=[make_mesh(5,3),make_mesh(3,2),make_mesh(2,1)]
    var rng := RandomNumberGenerator.new()
    rng.seed=270601
    var half := CHUNK_SIZE*SIDE_CHUNKS*0.5
    for cz in SIDE_CHUNKS:
        for cx in SIDE_CHUNKS:
            var origin := Vector3(float(cx)*CHUNK_SIZE-half,0.0,float(cz)*CHUNK_SIZE-half)
            var transforms: Array[Transform3D]=[]
            var customs: Array[Color]=[]
            for candidate in int(CHUNK_SIZE*CHUNK_SIZE*DENSITY):
                var x := origin.x+rng.randf()*CHUNK_SIZE
                var z := origin.z+rng.randf()*CHUNK_SIZE
                var path_distance := absf(x-path_center(z))
                if path_distance < 2.6+rng.randf()*0.6: continue
                # Broad patchiness; deterministic and independent of LOD.
                var density := 0.79+0.21*sin(x*0.22+sin(z*0.11))
                if rng.randf()>density: continue
                min_accepted_path_distance=minf(min_accepted_path_distance,path_distance)
                var scale_y := rng.randf_range(0.75,1.3)
                var basis := Basis(Vector3.UP,rng.randf()*TAU).scaled(Vector3(rng.randf_range(0.8,1.2),scale_y,1.0))
                transforms.append(Transform3D(basis,Vector3(x-origin.x,ground_height(x,z)-0.018,z-origin.z)))
                customs.append(Color(rng.randf(),rng.randf(),scale_y,rng.randf()))
            var mm := MultiMesh.new()
            mm.transform_format=MultiMesh.TRANSFORM_3D
            mm.use_custom_data=true
            mm.mesh=meshes[0]
            mm.instance_count=transforms.size()
            for i in transforms.size():
                mm.set_instance_transform(i,transforms[i])
                mm.set_instance_custom_data(i,customs[i])
            # Includes height, terrain variation and maximum shader displacement.
            mm.custom_aabb=AABB(Vector3(-1.5,-2.0,-1.5),Vector3(CHUNK_SIZE+3.0,5.0,CHUNK_SIZE+3.0))
            for transform in transforms:
                if not mm.custom_aabb.has_point(transform.origin): generation_aabb_failures+=1
            var node := MultiMeshInstance3D.new()
            node.name="Grass_%d_%d"%[cx,cz]
            node.multimesh=mm
            node.material_override=material
            node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
            node.position=origin
            add_child(node)
            chunks.append({"node":node,"count":transforms.size(),"center":origin+Vector3(6.0,0.0,6.0),"lod":-1})
            clump_count+=transforms.size()
    generation_ms=Time.get_ticks_msec()-started

func set_winter(enabled: bool) -> void:
    snow_enabled=enabled
    material.set_shader_parameter("snow",1.0 if enabled else 0.0)

func update_lod(force := false) -> void:
    if camera==null: return
    var count_by_lod := [0,0,0]
    var instances_by_lod := [0,0,0]
    var triangles := [30,12,4]
    for chunk in chunks:
        var center_world: Vector3=to_global(chunk.center)
        var distance := Vector2(center_world.x,center_world.z).distance_to(Vector2(camera.global_position.x,camera.global_position.z))
        var desired := 0 if distance<24.0 else (1 if distance<48.0 else (2 if distance<96.0 else 3))
        var old: int=chunk.lod
        # 3 m hysteresis prevents repeated mesh switching at chunk boundaries.
        if not force and old>=0 and desired!=old:
            var boundary: float=LOD_DISTANCES[mini(old,desired)]
            if absf(distance-boundary)<3.0: desired=old
        var node: MultiMeshInstance3D=chunk.node
        node.visible=desired<3
        if desired<3:
            node.multimesh.mesh=meshes[desired]
            node.multimesh.visible_instance_count=int(float(chunk.count)*[1.0,0.65,0.30][desired])
            count_by_lod[desired]+=1
            instances_by_lod[desired]+=node.multimesh.visible_instance_count
        chunk.lod=desired
    var tri_count := 0
    for i in 3: tri_count+=instances_by_lod[i]*triangles[i]
    stats={"total_clumps":clump_count,"chunks":chunks.size(),"active_chunks_by_lod":count_by_lod,"submitted_instances_by_lod":instances_by_lod,"submitted_triangles_upper_bound_before_frustum":tri_count,"instance_buffer_bytes_estimate":clump_count*64,"generation_ms":generation_ms,"per_clump_nodes":0,"grass_collision_objects":0}

func _process(delta: float) -> void:
    wind_clock+=delta
    material.set_shader_parameter("wind_time",fixed_time if fixed_time>=0.0 else wind_clock)
    material.set_shader_parameter("wind_strength",0.28 if wind_enabled else 0.0)
    lod_clock+=delta
    if lod_clock>=0.25:
        lod_clock=0.0
        update_lod()

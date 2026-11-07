shader_type spatial;
render_mode cull_disabled, specular_disabled, diffuse_lambert_wrap, world_vertex_coords;
// Opaque alpha cutout. No blend sorting or overlapping transparent passes.
uniform sampler2D blade_mask : filter_linear_mipmap, repeat_disable;
uniform vec3 root_color : source_color = vec3(0.32,0.39,0.25);
uniform vec3 tip_color : source_color = vec3(0.70,0.67,0.42);
uniform vec2 wind_direction = vec2(0.93,0.37);
uniform float wind_strength : hint_range(0.0,0.6) = 0.25;
uniform float wind_time = 0.0;
uniform float snow : hint_range(0.0,1.0) = 0.0;
uniform float fade_start = 63.0;
uniform float fade_end = 83.0;
varying float color_variation;
varying float clump_random;
void vertex() {
    vec3 root = MODEL_MATRIX[3].xyz;
    float h = clamp(UV.y,0.0,1.0);
    float distance_to_camera = distance(root.xz,CAMERA_POSITION_WORLD.xz);
    float range_scale = 1.0-smoothstep(fade_start,fade_end,distance_to_camera);
    float winter_scale = mix(1.0,0.46,snow);
    VERTEX.y = root.y+(VERTEX.y-root.y)*range_scale*winter_scale;
    // Slow spatial gust + per-clump phase. Root is mathematically immobile.
    float phase = dot(root.xz,vec2(0.19,0.27))+INSTANCE_CUSTOM.r*6.2831853;
    float wave = 0.57+0.28*sin(wind_time*1.8+phase)+0.15*sin(wind_time*3.1+phase*1.63);
    float displacement = wind_strength*wave*h*h*INSTANCE_CUSTOM.b*range_scale*winter_scale;
    vec2 safe_wind_direction=wind_direction/max(length(wind_direction),0.001);
    VERTEX.xz += safe_wind_direction*displacement;
    // Stylized upward normals avoid dark X-shaped cards; no specular highlights.
    NORMAL = vec3(0.0,1.0,0.0);
    color_variation=INSTANCE_CUSTOM.g;
    clump_random=INSTANCE_CUSTOM.a;
}
void fragment() {
    // Seven blade silhouettes per card, baked once into a 128×128 mask.
    // Cutout keeps the material in the opaque path, avoiding blend sorting.
    if (texture(blade_mask,UV).a<0.42) discard;
    // Stable thinning exposes snow, rather than turning a thick green mat white.
    if (clump_random < snow*0.58) discard;
    vec3 summer=mix(root_color,tip_color,smoothstep(0.03,0.95,UV.y));
    summer*=mix(0.86,1.12,color_variation);
    vec3 winter=mix(vec3(0.39,0.40,0.29),vec3(0.83,0.84,0.76),smoothstep(0.35,0.94,UV.y));
    ALBEDO=mix(summer,winter,snow);
    ROUGHNESS=1.0;
    SPECULAR=0.0;
}

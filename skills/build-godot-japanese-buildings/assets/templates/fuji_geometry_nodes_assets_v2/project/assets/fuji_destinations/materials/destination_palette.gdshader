shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
uniform vec4 base_color : source_color = vec4(1.0);
uniform float snow_amount : hint_range(0.0, 1.0) = 0.0;
uniform bool is_water = false;
varying vec3 world_normal;
void vertex() {
    world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}
void fragment() {
    // COLOR.a is authored shelter exposure, not transparency.
    // Every material stays opaque: no reflection, screen read, or alpha sorting.
    float exposure = COLOR.a * smoothstep(0.18, 0.8, world_normal.y);
    float snow = clamp(snow_amount, 0.0, 1.0) * exposure;
    vec3 base = base_color.rgb * COLOR.rgb;
    vec3 winter = is_water ? vec3(0.67, 0.78, 0.77) : vec3(0.88, 0.92, 0.89);
    ALBEDO = mix(base, winter, snow);
    ROUGHNESS = 0.94;
    SPECULAR = is_water ? 0.22 : 0.12;
}

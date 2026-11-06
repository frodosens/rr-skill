# 验证与性能

## 最低测试矩阵

1. 几何：全部属性有限、法线单位长度、绕序和法线一致、无退化面，正确计算 indexed/unindexed triangles。
2. 包络：静态车身、后视镜、全部车轮完整滚动和左右极限转向；轮胎接地高度、轮心与原物理轮接触对齐。
3. 预算：统计实例展开后的总面数、独立网格/材质数、surface submissions，说明是否含阴影及额外 pass。不能用多实例共享一个网格的面数冒充全部可见面数。
4. 状态：转向/滚动方向正确，前轴不混入后轴，制动变亮且不串到别车；非有限输入不污染 transform。
5. 生命周期：重复选择幂等、非法 ID、反复切换无旧引用/节点残留、资源身份共享正确、恢复存档安全。
6. 玩家接入：原碰撞 shape、body、轮胎、悬挂、传动对象、相机/HUD/交通引用保持；暂停切换保留 pose、速度和瞬时 RPM/挡位/离合状态。
7. UI/驾驶：实际按钮路径、不同横屏比例、开始/暂停/返回/后台/重置，正常加速和制动。不要仅直接调用方法就宣布触控 UI 通过。
8. 视觉：前后侧、正常追车、行驶轮组与制动灯。明确截图是模型图库、静态场景还是持续驾驶。

## 项目已有入口

先确认文件仍存在，并读脚本的输出/存档行为。在隔离 HOME/XDG 或项目提供的测试专用存档中运行，不触碰用户存档。

```sh
PROJECT_ROOT=/path/to/current/project
TEST_HOME="$(mktemp -d)"
export HOME="$TEST_HOME" XDG_DATA_HOME="$TEST_HOME/data" XDG_CONFIG_HOME="$TEST_HOME/config" XDG_CACHE_HOME="$TEST_HOME/cache"
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
godot --headless --path "$PROJECT_ROOT" --script res://tests/test_car_visual_style.gd
godot --headless --fixed-fps 60 --path "$PROJECT_ROOT" --script res://tests/test_player_vehicles.gd
godot --headless --path "$PROJECT_ROOT" --script res://tests/test_traffic_visuals.gd
```

交通池/资源复用变更还查 `tests/test_traffic_pool.gd`、`test_traffic_colors.gd`、`test_traffic_render_interpolation.gd`。物理接口受影响时加对应车辆、转向、轮接触、传动与相机测试，不以外观测试替代。

真实渲染要求可用显示与图形驱动，不能加 `--headless`：

```sh
godot --path "$PROJECT_ROOT" --audio-driver Dummy --script res://tools/capture_car_style.gd -- /absolute/capture/car-style
godot --path "$PROJECT_ROOT" --audio-driver Dummy --script res://tools/capture_player_vehicles.gd -- /absolute/capture/player-vehicles
godot --path "$PROJECT_ROOT" --audio-driver Dummy --script res://tools/capture_traffic_models.gd -- /absolute/capture/traffic-gallery
```

## 结果表述

记录源码 hash/commit 与工作区状态、Godot 精确版本、渲染器、镜头/光照/画质、分辨率、测试与截图路径。历史文档通过数字只作历史证据，不能算本次执行结果。

headless 适合几何与状态检查，不证明实际 shader/GPU 或 MultiMesh 缓冲正确。桌面 llvmpipe 的时间不是 Android FPS。真机比较要固定车数、镜头、画质和路段，记录设备、冷/热机、帧时间分位、内存、GPU/CPU 和阴影负载；未测就明确未测。

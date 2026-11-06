# 场景验收与性能

## 分层证据

1. **源与结构**：记录工具版本、源码/输入/输出 hash、manifest、文件所有权、参数、seed。重复生成逐文件比较；保存后重新读回真实 Mesh、collision 和 MultiMesh。
2. **静态几何**：实际世界变换下 bounds、有限法线、绕序、退化面、坡度、碰撞唯一所有者、跨块边界、支撑 probes；不只读生成器声明。
3. **放置**：完整足迹与实际 mesh 底部射线、最大掩埋/悬空、树冠/路口/护栏净空，树石碰撞和安全牌正反面。缺失数据明确标未知。
4. **生命周期**：加载→显示前准备→退休→卸载→重载；重复循环计数节点、资源、材质和注册项，确保不增长。检查启动过早按开始、暂停、返回、重置。
5. **天气**：同位置晴/雪、精确晴天恢复、远近 LOD、原本隐藏批次、天气缓存、遮蔽和水面类别。原车相同输入轨迹比较物理不变。
6. **连续驾驶**：真实原车仅靠油门/制动/转向，起步前可以一次合法出生定位，行驶中不设 pose/速度、不瞬移补路线。记录四轮、车体、surface owner、法线、接触深度、速度突降、离路、恢复和等待流送。
7. **画面**：真实默认主世界、车辆和世界管理器；固定相机同机位前后、晴雪、近中远与 LOD 边界。保留原 HUD 的驾驶图与隐藏 HUD 的美术检查图分别标注。
8. **性能**：实际渲染计数、冷/热加载、完整天气注册、稳态驾驶、最坏 HUD/交通/阴影；真机另验。

严格驾驶存在一次异常就按测试规则保留 FAIL，即使到终点。可说明有无实际速度影响与来源；官方引擎和修复引擎的结果分别标版本，不挪用修复版通过证明官方版全绿。阶段允许继续制作不等于删除旧失败。

## 项目现有测试

在当前相应工程找到后读脚本再执行。不是所有候选都包含以下所有文件；不得凭本列表编造通过数。

```sh
# 原山路工程，使用隔离 HOME/XDG，避免污染用户存档。
PROJECT_ROOT=/path/to/current/project
TEST_HOME="$(mktemp -d)"
export HOME="$TEST_HOME" XDG_DATA_HOME="$TEST_HOME/data" XDG_CONFIG_HOME="$TEST_HOME/config" XDG_CACHE_HOME="$TEST_HOME/cache"
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
godot --headless --path "$PROJECT_ROOT" --script res://tests/test_forest_distribution.gd
godot --headless --path "$PROJECT_ROOT" --script res://tests/test_ground_cover.gd
godot --headless --path "$PROJECT_ROOT" --script res://tests/test_landscape_style.gd
godot --headless --path "$PROJECT_ROOT" --script res://tests/test_visual_weather.gd
godot --headless --path "$PROJECT_ROOT" --script res://tests/test_winter_trees.gd
```

当前世界候选另读 `project/tools/forestNNN/` 中 bake/verify/test/drive/capture 和阶段 `tools/seal_contractNNN.py`；它们不完全共用命令行。先核对输入目录、引擎与真实 GL 要求，不能机械替换 NNN 运行。

示例 017 证据包括 `native_ground017.json`、`native_forest017.json`、`native_safety017.json`、`ground_material017_native.json`、`integration017.json`、驾驶逐帧 JSONL、同机位图和性能汇总。seal 只有当前资源与 PASS 证据 hash 匹配才执行，不能修改报告状态让它通过。

## 渲染与截图

原山路已有 `tools/capture_scene_art.gd`、`capture_terrain_forest.gd`、`capture_landscape_style.gd`、`capture_winter_trees.gd`、`capture_weather.gd`。实际运行需图形显示/驱动；headless 的零 draw counts 不作证据。

截图分类必须写清：概念参考、离线资产预览、实际引擎静态视角、持续物理驾驶。镜头移动采样不是连续实驾。相机/FOV/画质/日照/天气变化时不称严格 A/B。保留截图对应源码与参数，不把旧候选截图改名当最终结果。

## 性能预算

分别报告总资产、常驻、当前加载、当前可见的三角形/节点/资源；分清材质数、surface submissions 和实际渲染 draw calls（阴影会追加 pass）。文件大小不等于运行内存，引擎 video/static 不等于 Android PSS，微基准加速不等于整机 FPS。

性能诊断至少包含：
- 固定视角、分辨率、画质与时间窗口；保留原HUD/交通与是否启用物理；
- attach 与完整注册/构建成本分别计 p50/p95/p99/max，不只挑暖样本；
- 冷启动、第一次 shader 编译、反复跨块、长时间内存与退出；
- 真机型号/刷新率/省电与温升、冷/热连续驾驶、CPU/GPU/帧时间。

旧项目 Graphics owns 3D scaling/MSAA/shadow ranges：Balanced 0.8/2×/64 m，Performance 0.7/off/40 m，Original 1.0/4×/160 m。这是现有配置示例，风格/天气代码不覆盖用户画质选择。80% 每边是64%像素，不能直接换算FPS增幅。

云端 llvmpipe 仅作真实引擎画面与工作量观察，不能证明 Android 30/60 FPS。2 ms 挂载目标告警必须保留；新场景画面好看不清除它。未做设备、全图、所有天气或 APK 检查的项目明确列未验，不扩大局部结论。

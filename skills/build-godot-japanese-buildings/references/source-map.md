# 来源索引与状态边界

本技能的建筑方法来自已保存的本地实现，核对日期为 2026-11-06。下列路径以工作区或相应资产归档的父目录为基准，不是随技能分发的文件。先找到文件并核实内容；缺失时使用当前仓库的等价实现，或明确缺少源。不要执行含旧绝对路径的脚本而不审查。

## 普通住宅 / 商店

`fuji_geometry_nodes_assets_v2/`：
- `source/build_node_assets.py`：`graph()` 创建真实节点网络，`evaluate()` 离线求值，`check_door_clearance()` 验证求值后的窗组。空输入网格；住宅/商店 × 两级 LOD 共四张节点图。
- `source/japanese_buildings_geometry_nodes_v2.blend`：保留节点和输入参数的源文件。
- `source/validate_glb.py`、`source/run_checks.sh`：实际 GLB 检查和 Godot 导入/场景/资源测试。
- `project/tools/build_scenes.gd`：共享 ShaderMaterial、显式 LOD、默认禁用碰撞和入口 Marker。
- `project/tools/test_assets.gd`：加载、资源身份、40 次装卸和雪参数测试。
- `project/assets/fuji_destinations/materials/destination_palette.gdshader`：Color.a 雪曝光，不写 ALPHA。
- `evidence/module_contracts.json`、`geometry_nodes_proof.json`、`glb_validation.json`、`godot_validation.json`：绑定具体导出资产的历史结果。

历史证明使用 Blender 4.3.2 和 Godot 4.6.3。独立资产测试通过；其材质接口并未因此自动接入主游戏气候，未证明 Android/GPU、场地或驾驶。

## 温泉旅馆

`fuji_onsen_hotel_massing_v3/`：
- `source/build_hotel.py`：`hotel(detail=True)` 用显式 `Mesh.box`、`roof`、`cylinder`、窗组和组合资产建模，非 Geometry Nodes。
- 它读取相邻 `fuji_destination_assets_v1/source/build_assets.py` 的 `BUILDERS=` 之前定义。该段也会初始化材质、清空 Blender 当前场景；不是无副作用的库导入。仅在独立后台 Blender 进程/工作副本执行，并保留依赖目录结构或显式重构路径。
- `source/parking_design.json`、`evidence/hotel_site_contract.json`：14 车位方案、前场/后勤/浴场接口。
- `source/check_export_bounds.py`、`source/check_geometry_channels.py`、`source/audit_prepared_contract.py`：保存的 GLB 几何和静态布局审核。
- `evidence/hotel_export_bounds_verified.json`、`hotel_geometry_channels_verified.json`、`prepared_source_parking_audit.json`、`SITE_HANDOFF_V3.md`：具体 v3 证据。
- `evidence/godot_validation.json`：另有 Godot 4.6.3 headless 加载/资源/生命周期 PASS 记录，40次装卸、8材质身份；使用前重核当前输入绑定。

v3 仍是未摆入地形的体量方案。不要把旧 16 车位合同或六车位扫掠证明应用到它；不要把图示 6m 道路当作修改已冻结道路宽度的授权。headless 资源记录不构成 Godot 世界集成、Android/GPU、天气、物理、地形或驾驶验收。

## 宅地与实际运行案例

- `fuji_v3_house_access_v4/FINAL_REPORT.md`：拒绝的住宅地面候选，状态 SITE_ACCESS_BLOCKED。两维路线/门前路径读回通过不等于整片地形通过。不要应用 `patch/rejected_field_candidate.json`；相关 guarded 脚本有意拒绝。
- `fuji_v3_house_cleanup005/README.md`、`patch/apply_cleanup.gd`、`patch/cleanup_plan.gd`、`patch/native_signature.gd`：按原生节点/共享组件清理旧宅地，before-state guard 与重复调用拒绝。仅清理证明，不是新布局/驾驶验收。
- `fuji_v3_lakeside_cluster_plan005/README.md`、`selected_houses.json`：A4/A5 两户完整足迹、实际锚点、旧 A3 保护和固定镜头视线规划。不是可建或可驾驶定案。
- `household_details004_leaf_review/REPORT.md`：保存后原生组件、材料、脚位不变和限定继承的独立复审示例；不等于整世界复审。
- `fuji_v3_lakeside_private_drive005/FINAL_A6_REPORT.md`：v5 隔离世界实际低速回路已跑；v6 是不同哈希的静态继承，不是 v6 动力学重跑。旧路线遗留失败保持原状态。
- `fuji_v3_lakeside_private_drive005/tools/extract_multimesh.py`：保存的 MultiMesh float32 缓冲读取示例；后半段还写测试适配器，不能当纯只读工具直接运行。
- `fuji_v3_game_integration005/README.md`、`evidence/integration_summary.json`：主工程独立住宅区预览入口及原车约61m连续驾驶；严格子接触检查有保留告警，不代表旧主地图无缝拼接、全部天气或全碰撞通过。

上述目录是不同阶段，不互相提升状态。检查完整输入依赖和场景哈希后才继承一个结论。

## 主工程定位

历史工作区使用 `apex-rush-godot/` 保存游戏工程：
- `scripts/lakeside005/`、`scenes/lakeside005_preview.tscn`、`assets/lakeside005/`：独立预览入口，不替换默认 `scenes/main.tscn`。
- `scripts/world/world_climate.gd`：检查当前 `MAX_SHELTERS`，历史实现为16。
- `scripts/visual_weather.gd`：chunk 注册/卸载、遮蔽集合和材质参数更新。
- `scripts/ground_cover.gd`：包含 dummy/headless 无法可靠读回 MultiMesh 实例的说明。

历史本地工程的 Git 远端可能与用户当前要求的仓库不同。操作前实际运行 `git remote -v` 并核实目标，不能把这个目录默认当成 `frodosens/fsnet-godot-demo`。

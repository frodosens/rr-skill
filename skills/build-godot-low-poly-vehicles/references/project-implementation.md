# 项目实现与接口

## 来源边界

2026-11-06 从 fsnet-godot-demo 工作区核对。主工程目录名为 `apex-rush-godot`；其 Git HEAD 为 `7870e454be4b7e15ea2b8f598f0088e72050f41a`，同时存在未提交变更。因此下面是源码/文档核对过的方法，不是“所有文件已在该提交或远端 main”的声明。使用时先重新定位当前工程。

这些是项目相对路径，不是本 skill 附带的生成器。没有项目时，可按方法重建同类模型，但不能运行不存在的命令或声称已使用原项目资产。

## 源码入口

| 文件 | 已实现用途 |
| --- | --- |
| `scripts/car.gd` | 玩家车、既有红车构建、视觉切换与轮组驱动；阅读 `select_vehicle`、`_update_visual` |
| `scripts/car_visual_style.gd` | 红车一次性风格整理；`apply`、`_material`、`_polygon`、`_body_mesh` |
| `scripts/player_vehicle_visual.gd` | 蓝车原生程序化几何；`create()` 返回 `visual/wheels/front_wheels/tail_lights` |
| `scripts/traffic_vehicle_visual.gd` | 五种 NPC 共用的车型/网格缓存、材质与 `set_motion` |
| `scenes/traffic/*.tscn` | taxi、truck、sedan_a、sedan_b、hatchback 可复用入口 |
| `docs/PLAYER_VEHICLES.md`、`CAR_VISUAL_STYLE.md`、`TRAFFIC_MODELS.md` | 制作意图、接口、预算与历史验收边界 |

## 玩家车

蓝车是 2007–2010 GR 风格宽体拉力掀背的原创低多边形解读。没有厂徽、第三方模型或“官方授权 STI”声明。

- 四轮中心按左右分组：`x=±0.91`、`y=0.38`、前 `z=-1.35`、后 `z=1.31`。这是该车型与原底盘的接口，不是所有车型通用尺寸。
- 每轮是转向 pivot 下的 `Spinner`；`front_wheels` 单独存前轴引用。
- 后轮拱视觉半宽 1.085 m，前 1.010 m；更宽后肩不扩大物理轮距。
- 文档实测蓝车 3,056 三角、20 MeshInstance、7 材质；测试上限为 3,500 三角、22 MeshInstance、7 材质，视觉宽 <2.2 m、长 <4.5 m、高 <1.6 m。实测数与上限不要混用。
- 红车文档基线为 2,560 三角、8 材质资源，尾灯包含独立状态。
- 蓝车几何仅是视觉；选择该车时现有系统另绑定已实现的合成动力曲线，保留原底盘、五档齿比及轮胎/悬挂对象。不是量测 STI 标定或 AWD 仿真。新造型不应自动继承修改动力的授权。

## NPC 车

`create(kind)` 或实例化相应 tscn；`configure(kind, color)` 在需要时重建此实例。未知 kind 回退 sedan_a。`set_motion(speed_mps, steering_angle, braking, delta)` 控制轮动和尾灯，无自主 `_process`/`_physics_process`。

- +Y 向上、-Z 向前、名义轮胎接地 y=0。
- 一个六 surface 车身 + 一个两 surface 四轮 MultiMesh，共两个视觉子节点。八 surface/color pass，不含额外阴影 pass，不能简写为固定八个全帧 draw calls。
- 每车含四轮不超过 1,400 三角。文档基线 taxi 1,240，truck 928，sedan_a 764，sedan_b/hatchback 776。
- `dimensions(kind)` 包含 ±0.55 rad 转向与滚动包络；与 `_geometry_dimensions` 的固定车体尺寸分开。不要用扩大的净空尺寸重算轮心。
- 车体按 kind 缓存，轮网格按半径缓存；共用普通材质和有限车漆色板，尾灯为每车独立副本。
- `wheel_transforms` 为 CPU 端真值，可在 dummy renderer 不保留 MultiMesh 读回缓冲时检查计算结果；GPU 实际缓冲仍需实渲染验证。

## 核对来源

车型外观参考可查看项目文档中保留的 Subaru 官方历史资料。参考仅帮助理解形状，不将网页图片、标志或第三方几何打包：
- https://www.subaru.co.jp/en/news/archives/press/2007/07_10_24e.html
- https://www.subaru.ca/Content/7907/media/en-ca/download/WRX%20STI2008_Brochure.pdf

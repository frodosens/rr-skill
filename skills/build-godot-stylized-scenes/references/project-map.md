# 项目来源与阶段

## 使用边界

2026-11-06 核对的工作区包含多个并行候选。以下目录是相对历史共同工作根目录 `WORK_ROOT` 的来源线索，不是安装依赖。已打包的生成器和草样板及运行入口见 [portable-tools.md](portable-tools.md)，完整世界/旧证据未打包。重用时搜索并核对当前目录与源 hash，不依赖某台机器的绝对路径。本轮 git 实查 `apex-rush-godot` 的 origin 为 `https://github.com/frodosens/RallyDelivery.git`，不要从本技能的目标项目名推断来源仓库。其 HEAD 为 `7870e454be4b7e15ea2b8f598f0088e72050f41a`，但工作区有未提交变化，不能把本表当远端 main 的状态。

## 入口与适用范围

| 相对位置 | 可复用方法 | 不应误称 |
| --- | --- | --- |
| `apex-rush-godot/docs/ART_DIRECTION.md`、`LANDSCAPE_STYLE.md` | 参考转构图/色板、明亮但克制的光照、薄雾、实际截图验收 | 老文档树木总量不一定是当前场景数量 |
| `apex-rush-godot/scripts/forest_distribution.gd`、`course.gd`、`ground_cover.gd` | 最终地形、坡度/海拔倾向、共享占用、稳定散布与分块 | 不是真实生态/水文/生长模拟 |
| `apex-rush-godot/tools/generate_branching_trees.py` | 离线、固定种子、Branches/Foliage、两级 GLB | 不在游戏运行时执行 |
| `apex-rush-godot/scripts/landscape_style.gd` | 色板、粗细层次、统一环境与远雾 | 不拥有画质设置的 MSAA/阴影距离 |
| `apex-rush-godot/docs/OPEN_WORLD_W2_GEOMETRY.md`、`OPEN_WORLD_W3.md` | 地表所有权、保存资源验证、远近景、天气/流送缓存 | 历史验收与限制不能跨候选冒用 |
| `fuji_geometry_nodes_assets_v2/source/build_node_assets.py` | 真正 Geometry Nodes 建筑、参数、近远版本、GLB 导出 | 不是已摆好且玩法完成的村落 |
| `fuji_geometry_nodes_assets_v2/evidence/module_contracts.json` | 建筑包络、基座、入口/台阶合同 | 仅资产合同，不是全场景碰撞通过 |
| `fuji_community_store_v3/evidence/SCENE_HANDOFF.md` | 保持锚点/包络的便利店局部外观替换 | 局部对照不等于全面上线 |
| `fuji_v3_unified_world005/project` | 单一世界、住宅、已有任务和接入基础 | 005 README 后续章节可能为历史阶段 |
| `mountain_style_sample008/project/scripts/mountain_style_sample.gd` | 已选低多边形杉林风格样片、可驾驶验证 | 独立样片不是整合后全世界 |
| `forest_pcg009/tools/place_forest009.py`、`safety009.py` | 权威保存三角、种子、完整足迹、净空与新森林 owner | 009 严格驾驶曾 FAIL，不能写成全绿 |
| `forest_ground011/tools/build_ground_field011.py` | 真实道路距离场与平滑光照法线，只改外观 | 没有推平真实地形 |
| `forest_corridor012` 至 `ridge_corridor017` | 继承冻结候选，局部扩展/合同/回归/回退 | 候选不自动视为已合入 main 或全图完成 |
| `grass_wind027/project/scripts/grass_field.gd`、`project/shaders/grass.gdshader`、`INTEGRATION_NOTES.md` | 五片交叉草丛、固定根部 GPU 风动、分块 MultiMesh、LOD/晴雪与远景衔接；详见 [密集植被](dense-vegetation.md) | 独立 96×96 m 样板；新增 32–52 draw calls 仅为云端软件 GL 计数，非手机或正式主世界验收 |

## 新森林与旧山路不要混为一套

旧山路有多树种枝叶 GLB、远景树卡与分片占用。008 样片及 009–017 候选使用更简洁的低多边形针叶树风格，常见近/中/远树为 160/96/48 三角，64 m 组织，约 115/220/440 m 切换或隐藏。它们不是把全部旧树资产直接换皮。

009 后树干和岩石有实际静态碰撞，草/灌木可穿过；008 样片装饰没有独立碰撞。任何复用都先读本阶段合同，不能从“看起来一样”推断碰撞一致。

017 最终 README 与 `evidence/INDEPENDENT_REVIEW017.md` 写明：长程修复引擎 headless 与较短官方 OpenGL 两次严格驾驶均 FAIL，旧沥青接触造成真实停车，不能称无害单帧告警。既有道路问题仍阻塞驾驶/发布验收，局部场景检查通过不解除阻塞。该版本仅可逆开发候选，未合入 main、未导出 APK、未获 Android 验收，另有 2 ms 挂载预算告警及护栏未完成延伸。以后先查最新证据再更新，不把历史状态永久硬编码到新工作。

## 道路工作分流

当工作涉及日本左行、道路断面、停止线、文字、箭头、住宅接入或路口语义，配合 `generate-japan-left-hand-roads`。本技能负责场景/资产与道路的空间接口，不自行捏造法定路标或宣称道路工程合规。

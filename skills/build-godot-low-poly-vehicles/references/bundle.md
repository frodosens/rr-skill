# 独立资源、依赖与使用

## 运行

依赖 Python 3.9+（仅标准库）及 Godot 4.6.x。无需 pip 包、Blender、贴图、字体或下载步骤。`res://` 均相对 `assets/vehicle-fixture/project.godot`，不是技能目录。示例从技能目录执行，也可从任意目录使用脚本绝对路径：

```sh
python3 scripts/run_fixture.py --godot /path/to/godot
# 有显示服务器和 OpenGL 驱动时才执行图库截图，不可用 headless 替代：
python3 scripts/run_fixture.py --godot /path/to/godot --capture /absolute/output/vehicle-gallery
```

脚本将 fixture 复制到独立临时目录，隔离 HOME/XDG，运行蓝车和交通模型测试，失败返回非零，结束删除副本。截图只允许写入技能目录外的新目录或空目录；非空目录、技能内路径（含解析后指向技能内的符号链接）会在任何引擎启动前拒绝。截图完成后逐个检查七个预期文件存在、大小超过 PNG 签名长度且具有正确 PNG 签名；这不是完整 PNG 解码或画面质量检测。原始图库 GDScript 保持不变，其 `save_png` 返回值未直接检查，因此使用 runner 的输出验证，不要把直接调用脚本的退出码当作截图交付成功。截图仅是五种 NPC 的静态图库，不含玩家驾驶或 UI。未提供屏幕时不要调用截图分支。

也可把 `assets/vehicle-fixture` 复制到自己的工作目录，以 Godot 打开其 `project.godot`，或运行 `godot --headless --path /copied/fixture --script res://tests/test_player_visual.gd`。该工程没有默认游戏主场景，必须使用 `--script` 入口。

可不启动 Godot 验证输出防护：`python3 scripts/test_runner_guards.py`（Python 标准库）。

## 附带内容及接入

- `scripts/player_vehicle_visual.gd`：`create()` 返回蓝车视觉与四轮、前轮、尾灯引用。`RED_COUPE` 是兼容原游戏的 ID 常量，不代表本包附带完整红车生成器。
- `scripts/car_visual_style.gd`：蓝车依赖的材质、网格辅助函数；同时保留原红车风格工具，但其 `apply()` 需要原项目已有红车层级，不能单独生成完整红车。
- `scripts/traffic_vehicle_visual.gd`：五种交通车生成器，共享网格与材质缓存、独立制动灯、`set_motion` 接口。
- `scenes/traffic/*.tscn`：taxi、truck、sedan_a、sedan_b、hatchback 可实例化场景。
- `tests/test_traffic_visuals.gd`：原项目独立交通视觉测试，覆盖几何、预算、包络、轮动、状态隔离等。
- `tests/test_player_visual.gd`：本包新增蓝车几何、预算、轮组引用、尾灯状态资源隔离测试。
- `tools/capture_traffic_models.gd`：原项目静态模型图库，生成前后整体图及五个单车图。

复制生成器到目标 Godot 工程时保留 `res://scripts/` 路径，或同时修改两个构建器内的 preload/load 路径。构建器仅生成视觉，不附带碰撞、驾驶、音频、交通控制器、摄像机或 UI。四轮和前轮顺序以构建器为准。运行时节点要由调用方加入场景树并释放；不能直接把动态树当作已经持久化的 `.tscn`。

## 来源与授权边界

源仓库：`frodosens/RallyDelivery`（经 `git remote get-url origin` 核实为 `https://github.com/frodosens/RallyDelivery.git`），源目录名 `apex-rush-godot`，打包时 HEAD 为 `7870e454be4b7e15ea2b8f598f0088e72050f41a`，源工作区另有未提交改动。本次任务的用户项目背景涉及 fsnet-godot-demo，但不能据此把这份 RallyDelivery checkout 认作同一仓库。逐文件 SHA-256 与源文件状态记录于 `provenance.json`，不能用 HEAD 推断整个工作区干净。打包保持所选原始模型、场景、原测试及图库代码字节不变；fixture 工程、Python runner、蓝车独立测试与本文档是本次新增适配。

源工作区顶层未见 LICENSE；这里不虚构开源许可证或品牌授权。提交到 rr-skill 的许可和版权声明由仓库所有者/提交者确认。本包不含第三方品牌标志、外部模型或参考网页图片。造型是原创低多边形解读，不代表真实动力学或厂家授权产品。

## 验证边界

独立测试不覆盖原项目车型选择、存档、暂停切换、HUD、碰撞或动力系统。无真实渲染的测试也不证明 GPU/MultiMesh 缓冲或画面正确，更不能证明 Android 帧率。实际本次执行结果见 `validation-results.md`。

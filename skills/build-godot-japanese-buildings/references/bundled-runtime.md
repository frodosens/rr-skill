# 随包可运行的离线建筑样例

本技能不再只提供历史路径。`scripts/samples/` 包含住宅/商店 Geometry Nodes 生成器、旅馆显式网格生成器、它调用的完整本地辅助源码、GLB 检查器和渲染脚本；`assets/templates/` 包含最小 Godot 工程、共享 shader 和导入/生命周期测试。`assets/fixtures/` 是约 224 KiB 的原车视觉参考及尺寸快照，用于静态比例/停车示例，不是当前游戏动力或尺寸的永久真相。

## 运行环境

- Python 3.10+（入口与 GLB 检查只有标准库）。
- Blender 4.3.2 是实际验证版本；需要其 glTF 导出器与 Geometry Nodes API。没有 Blender 时只能准备/检查包，不能声称已生成模型。不会自动安装软件。
- Godot 4.6.3 是实际验证版本；headless 导入/保存读回检查不需要游戏仓库，`godot-check` 另需 Bash。
- 可选离线图像使用 Blender Cycles CPU，不依赖付费服务或网络。它是资产工作室/旅馆体量预览，不是游戏截图。旅馆画面保留概念树占位、遮挡与近镜头暗轮廓，不代表最终场景美术通过。
- 完整地形、入口、晴雪系统、玩家车与 Android 测试仍需用户明确提供的目标工程。整个历史世界、APK 和 700 MB 支撑三角输入不包含在技能内。

## 独立入口

从技能目录执行以下命令。输出选一个新的空目录；脚本拒绝写入安装目录、覆盖已有非空目录。所有产物、日志和 Godot 缓存都写入该工作区。可以把整个技能复制到另一目录再运行，未引用原工作区绝对路径。

```bash
python3 scripts/run_sample.py prepare --output /tmp/building-demo
python3 scripts/run_sample.py build --workspace /tmp/building-demo --sample all
python3 scripts/run_sample.py validate --workspace /tmp/building-demo --sample all
python3 scripts/run_sample.py godot-check --workspace /tmp/building-demo --sample all
# 可选：五张住宅/商店图与旅馆方案图，会占用 CPU 时间。
python3 scripts/run_sample.py render --workspace /tmp/building-demo --sample all
```

`--sample buildings` 仅住宅/商店，`--sample hotel` 仅旅馆。可用 `--blender /path/to/blender`、`--godot /path/to/godot` 显式选择二进制。每步默认 1200 秒超时，Blender 默认两线程；失败保留 `evidence/*.log`，入口非零退出。`--python-exit-code 1` 防止 Blender 的 Python 异常被误记为成功。

`prepare` 复制既有目录布局，旅馆相邻的 `fuji_destination_assets_v1` 辅助源码也一起复制。旅馆辅助加载有清空 Blender 场景的副作用，所以仅在独立 `--background --factory-startup` 进程运行。不要直接从安装目录执行 samples 中的作者脚本，它们按脚本位置写输出。不要在打开的 Blender 工作文件中执行。

## 输出与检查边界

- `fuji_geometry_nodes_assets_v2/project/assets/fuji_destinations/`：四种建筑 × 两级 LOD 的 GLB、manifest，以及引擎检查生成的场景、共享材质。
- `fuji_geometry_nodes_assets_v2/source/japanese_buildings_geometry_nodes_v2.blend`：可编辑节点源；`evidence/geometry_nodes_proof.json`、`module_contracts.json`：当前生成证据。
- `fuji_onsen_hotel_massing_v3/`：旅馆和组合资产 × 两级 LOD、可编辑 `.blend`、14 车位设计和当前导出审计。静态车位包络不证明可转弯或实际驾驶。
- `building_sample_workspace.json`：随包源到工作副本的 SHA-256 清单，不是生成模型的验收替代物。
- 两样例的 `evidence/glb_validation.json` 与 `godot_validation.json` 是本次输出；旧工作区的 PASS 不复制进包冒充新测试。
- `python3 -m unittest discover -s scripts/tests -v`：三项标准库测试，覆盖依赖复制、拒绝覆盖/写安装目录、技能搬迁后独立准备；不启动引擎。

本次搬迁后实际执行结果见 [validation-results.json](validation-results.json)，其中大量引擎检查为逐顶点校验，不代表同数量独立场景。

版权与来源见 [bundle-provenance.json](bundle-provenance.json)。保存原有作者注释；没有凭空添加第三方开源授权。包内模型由已有原创生成流程导出，不带外部贴图。要向其他项目再分发时确认对应权利，不把来源注释当许可证。

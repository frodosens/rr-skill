# 自包含道路工具与样板

本技能内置016实际标线Python生成/审计器、006住宅路GDScript、左行约定检查和小型合成fixture。执行无需原历史目录或游戏大包。软件依赖不是技能自带二进制：Python3.12、Shapely2.1.2（见 `requirements.txt`）；006样板需Godot4.x，验证版本4.6.3。

所有命令从技能根目录运行，输出放新临时目录。工具不读取本机旧工作区，不自动联网、合入世界或发布。

```sh
python3 -m venv /tmp/road-tools-venv
/tmp/road-tools-venv/bin/python -m pip install -r requirements.txt
PY=/tmp/road-tools-venv/bin/python
SKILL="$PWD"
WORK="$(mktemp -d)"
"$PY" scripts/check_conventions.py --self-test
"$PY" scripts/smoke_test.py --output "$WORK/smoke"
```

## 016真正生成与独立审计

```sh
F="$SKILL/assets/fixture"
"$PY" scripts/generate_markings016.py --source-project "$F/project" \
  --triangles "$F/surface_triangles.jsonl" --rules "$F/marking_rules016.json" \
  --output "$WORK/markings"
"$PY" scripts/audit_geometry016.py --bundle "$WORK/markings"
```

结果包括 `output/meshes/mesh_*.json`、每个三角的 `support_witness016.json`、generation report，以及 `project/assets/world/road_markings016/` 的规则/报告。每个顶点来自同一真实输入三角平面并量化float32，图形逐三角裁切，不是仅检查约定的空壳命令。

包内fixture只有8个解析三角：跨三个128m owner的直路、一个独立接入面；第三owner受保护。例子生成84个标线三角、两个owner，验证真实接入轮廓中断、保护区移除、全路虚线相位、全部输出面积和支持误差。`make_fixture.py --output "$WORK/fixture"` 可逐字重建。这是合成测试，不能引用为正式道路验收。

生成器只写新的/空的输出目录，拒绝写入输入工程/规则/技能目录。它保留layout、triangle和native resource SHA检查。输出是JSON几何，还**不是已导入Godot的 `.res/.tscn` 标线包**；正式native烘焙、paint shader、天气和WorldManager adapter需调用者当前工程提供并重验。本包不打包旧016 seal/apply/发布脚本，因为它们需要特定世界的完整合同及审核证据。不要伪造合同通过或复制历史PASS。

`assets/historical/marking_rules016.json` 只保留历史R3/R8/R10范围与输入digest作为迁移对照，**不是快速示例输入**。正式执行需要另提供授权工程及约700MB完整triangle corpus，或经过验证、合同匹配的裁减输入；大文件和游戏源码不随技能发布。不得为了消除hash失败自动重签输入。新道路范围/交通语义仍需明确授权。

## 006住宅路原生样板

```sh
python3 scripts/prepare_residential_sample.py --output "$WORK/residential"
mkdir -p "$WORK/home"
export HOME="$WORK/home" XDG_DATA_HOME="$WORK/home/data" XDG_CONFIG_HOME="$WORK/home/config" XDG_CACHE_HOME="$WORK/home/cache"
godot --headless --path "$WORK/residential/project" --script res://scripts/test_residential.gd
```

`assets/residential006/project/scripts/residential_road_generator.gd` 是现有生成器源码，`demo_config.gd` 是小型弯路/两侧向接入口配置。测试实际生成 ArrayMesh + 同面碰撞，重复构建对比、开口/渐降路缘插点及中心车道物理射线。它不是9户住宅世界，也不包含自动路网求交、路路并集、NPC交通、流送接入或完整驾驶。此样板无默认主场景，按测试脚本运行；需画面时由调用者创建已授权的展示场景。

## 证据与许可

2026-11-07：将技能独立复制到 `/tmp`，在无原项目目录工作路径下生成两遍并审计，通过84三角、两owner、源hash失败/输入写入拒绝、相位和接入中断检查。同轮Godot4.6.3住宅样板通过5类可见/碰撞同面、确定性重建、178个断面插点、2666三角及195条实际物理射线。未重验正式地图、天气、可见画面、完整实驾或手机性能；Python PASS不是这些阶段PASS。

来源hash及打包适配见 [bundle-provenance.json](bundle-provenance.json)。未找到源项目脚本独立LICENSE/COPYING；不擅自创造开源授权。本包不包含新字形纹理或字体。要添加日文路面文字，需另提供有合法许可且覆盖目标字形的字体，按 [traffic-and-lettering.md](traffic-and-lettering.md) 保留许可并检查字形。

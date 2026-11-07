# 自包含工具、样板与边界

本技能随包提供可运行源码，不再需要历史工作目录才能制作树或运行小型验证。所有命令从技能根目录运行；`$PWD` 只用于定位已安装技能。不要把输出写回技能、输入工程或原始素材。下面依赖需由环境预先提供，`pip` 安装时遵循当前权限。

## 外部软件

- Python 3.12 为本轮测试版本。树 GLB、结构检查和 SVG 卡片只需标准库，Python 3.10+ 可用。
- 009/011 使用 `requirements.txt` 中固定的 NumPy、Shapely 2、SciPy、Pillow、fontTools。用独立 venv 安装；不把本机二进制 vendor 目录打进技能。
- 草样板需要 Godot 4.x；实测 4.6.3 Compatibility。真正 GPU/OpenGL 截图还需要正常显示与驱动；`--headless` 不证明渲染。
- Blender Geometry Nodes 建筑属于独立的 `build-godot-japanese-buildings` 技能，不是本包内置生成器。没有它也能独立运行以下全部命令；建筑任务需另提供该工具包或当前项目建筑源。

```sh
python3 -m venv /tmp/scene-tools-venv
/tmp/scene-tools-venv/bin/python -m pip install -r requirements.txt
PY=/tmp/scene-tools-venv/bin/python
SKILL="$PWD"
WORK="$(mktemp -d)"
# 这是合成输入隔离 smoke，不是当前世界验收。
"$PY" scripts/smoke_test.py --output "$WORK/smoke"
# 可选重复 smoke 加 Godot 纯 headless 草输入/LOD测试：
"$PY" scripts/smoke_test.py --output "$WORK/smoke-native" --godot /path/to/godot
```

## 树 GLB 与裸枝卡

```sh
python3 scripts/generate_branching_trees.py --output "$WORK/trees"
python3 scripts/generate_branching_trees.py --output "$WORK/trees" --check
python3 scripts/validate_tree_glbs.py --input "$WORK/trees"
python3 scripts/bake_bare_forest_card.py --output "$WORK/broadleaf_bare_card.svg"
python3 scripts/bake_bare_forest_card.py --output "$WORK/broadleaf_bare_card.svg" --check
```

生成九种树的近/远共18个 GLB及 manifest；无需下载模型。树写模式只接受技能外的新目录或已有空目录；SVG写模式只接受技能外尚不存在的目标文件，父目录可存在。已有输出与技能内路径会被拒绝，不覆盖。`--check` 保持只读，可检查已有输出。独立标准库回归：`python3 scripts/test_output_guards.py --output "$WORK/output-guards"`，无需Shapely或Godot。源码适配后 generator hash 会与原工程旧 manifest 不同，不能直接对旧 manifest 宣称复现通过；先在新目录生成，再独立验证。输出预算是资产预算，不是手机帧率保证。

## 009 放置、安全设施与 011 距离场

包内 `assets/fixture/` 是24个解析平面三角形的小场景，包含六个 owner、两条路及最小原生支撑资源。它不是富士地图、不是从正式世界提取的证据。`scripts/make_fixture.py --output "$WORK/fixture"` 可逐字重建这些输入。安全设施样例在平地只生成2个提示牌，不测试险坡护栏和桥梁覆盖。

```sh
FIXTURE="$SKILL/assets/fixture"
"$PY" scripts/place_forest009.py --project "$FIXTURE/project" \
  --frozen-project "$FIXTURE/project" --triangles "$FIXTURE/surface_triangles.jsonl" \
  --output "$WORK/forest"
"$PY" scripts/build_ground_field011.py --project "$FIXTURE/project" \
  --triangles "$FIXTURE/surface_triangles.jsonl" --output "$WORK/ground"
SHA=$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["triangle_sha256"])' "$FIXTURE/fixture_manifest.json")
"$PY" scripts/safety009.py --project "$FIXTURE/project" \
  --triangles "$FIXTURE/surface_triangles.jsonl" --expected-triangle-sha256 "$SHA" \
  --output "$WORK/safety"
```

`place_forest009.py` 与 `build_ground_field011.py` 输出新增资源到指定目录下的 `project/`，不改输入工程。安全设施输出 JSON 和带许可的日文字体子集，**没有完成 Godot 护栏碰撞/文字场景烘焙**。所有输出根需新建或为空；失败输出单独保留，重试换新目录。

重要限制：这些是009/011固定范围工具，不是任意地图 API。保留原六 owner `3:-11,4:-11,3:-10,4:-10,3:-9,4:-9`、384..640 / -1408..-1024范围、原密度/河道保留域与 `paddy_lane` / `forest_return` 约定。011仍为512×768、0.5m像素。更换地图必须显式适配并重验，不能仅替换文件路径。

正式复用需调用者提供授权的工程、独立冻结参考、完整 source catalog、layout、exclusions、匹配 native resources 和 triangle JSONL。未打包约700MB历史输入及游戏源码。catalog、triangle和源资源哈希不匹配时停止；不要删除校验或把当前损坏输入的hash填进去消警。安全脚本默认锁历史 G007 digest，fixture才使用明确的合成digest参数。正式替换digest要来自已核对的输入合同。`--frozen-project`在fixture可等于project，正式工作须有独立审核基线；相等只证明自洽，不证明审核。

## 草丛样板

`assets/grass_wind027/project/` 完整包含 shader、交叉草片生成、样板背景及测试/截图/计数脚本。没有依赖原 `grass_wind027` 目录；也不带旧 screenshots 或 PASS 报告冒充本轮结果。

```sh
python3 scripts/prepare_grass_sample.py --output "$WORK/grass"
mkdir -p "$WORK/home"
export HOME="$WORK/home" XDG_DATA_HOME="$WORK/home/data" XDG_CONFIG_HOME="$WORK/home/config" XDG_CACHE_HOME="$WORK/home/cache"
godot --headless --path "$WORK/grass/project" --script res://tools/test_grass.gd
# 仅在已有真实显示/驱动的环境运行，不添加 --headless：
godot --path "$WORK/grass/project" --rendering-method gl_compatibility --script res://tools/capture.gd
godot --path "$WORK/grass/project" --rendering-method gl_compatibility --script res://tools/profile_draw_calls.gd
```

每轮截图使用新样板副本，避免把旧 PNG 或历史计数当新结果。样板临时生成地形/散布只为演示；正式接入按 [dense-vegetation.md](dense-vegetation.md) 替换地表、遮罩、包围盒、天气与所有权，不整体复制背景。

## 本轮打包验证与许可

2026-11-07：移到 `/tmp` 新根且从无项目的工作目录运行；只用已安装 Python 依赖。树18个GLB重复生成/结构检查通过；fixture逐字重建、2910个确定性放置、011数据图、2个提示牌、损坏hash拒绝/源目录输出拒绝通过。Godot4.6.3 headless草测试91项通过。真实GL截图、原世界、原车、险坡护栏、天气集成及手机性能未在本轮重验。

来源与改动hash见 [bundle-provenance.json](bundle-provenance.json)。字体子集及完整SIL OFL保存在 `assets/fonts/`，保留重命名和版权声明。未找到原项目脚本的独立 LICENSE/COPYING；原作者说明不是新开源授权，不擅自加MIT或宣称可任意再分发。

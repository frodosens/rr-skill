# fsnet-godot-demo 实现地图

核查日期：2026-11-06。完整项目路径相对本次工作区根，后续缩写的 scripts/assets/docs 路径相对该段所列项目根；它们不是稳定安装路径。先定位对应工程；缺文件就报告缺失。skill不携带Godot、完整游戏或大型资产。少量生成器源码、原生样板和合成输入已自包含，见 [portable-tools.md](portable-tools.md)；以下未打包的路径仅作历史来源线索。

## 旧山路环路

来源身份：本轮 git 实查历史 `apex-rush-godot` 的 origin 为 `https://github.com/frodosens/RallyDelivery.git`，HEAD为 `7870e454be4b7e15ea2b8f598f0088e72050f41a`。后述候选目录只按历史工作区及逐文件hash识别，不推断属于哪个远端仓库。

来源：`apex-rush-godot/scripts/road_rules.gd`、`scripts/road_markings.gd`、`docs/ROAD_MARKINGS.md`、`assets/road_markings/road_paint.gdshader`。统一世界目录仍有旧文件，但存在不代表连接新路网。

- 已实现：`DRIVING_SIDE=-1`；四个hairpin双向“減速”、沿弯箭头、视觉减速条与外弯chevrons；真实底层三角面裁切、字形和天气材质。
- 耦合：旧course的 `hairpin_apices`、闭合progress、`SAMPLE_COUNT`、12米断面、`_right()`及固定车道距离。`RoadRules.LANE_CENTER=3.0`，文字/箭头2.85米，不适合直接套新6–7米路。
- 边界：静态装饰，不自动新增碰撞、抓地、限速执行或完整交叉口控制。
- 既有文档记录127个几何/材质、38个天气检查和真实截图；历史局部证据不等于本轮新项目已重跑。

## 住宅道路006

来源：`fuji_v3_residential_roads006/world_candidate/scripts/residential_road_generator.gd`、`scripts/neighborhood_semantics.json`、`README.md`、`evidence/native_validation.json`。最小例在 `prototype/`。

- 已实现：单条不自交住宅中心线、宽度/横坡、人行道、渐降路缘、简单侧向车道、视觉/碰撞同面。外部链处理入户步道、地形重整、植被排除与最终保存。
- 场地参数：约192米支路、4.4米车行道、双侧各1.2米步道，9户住宅/商店/公共路共11个接入端口。
- 独立候选历史证据：9组铺装视觉/碰撞一致、3337射线、367车体包络位置、1468轮位，不是动态驾驶。
- 该生成器未实现：任意路网求交、路路接驳并集、自动地块规划、完整交通控制、NPC停止/让行同步、通用桥梁。
- 候选README“尚未整合”属于其早期阶段；较新统一世界已含006owner。读当前adapter/manifest，勿以旧README覆盖后续证据。

## 016白线模块与统一世界

生成：`road_markings016/tools/generate_markings016.py`、`inputs/marking_rules016.json`、`output/INTEGRATION_FILES016.json`。

运行：`unified_markings016/project/scripts/world/road_markings_adapter016.gd`、`assets/world/road_markings016/contract.json`、`marking_rules016.json`。

- 已实现范围：R3 `fuji_lakeside` 平面桩号540至真实末端898.587米；R8 `onsen_climb` 40至553.408886米；R10 `ridge_ascent` 0至160米。双向左行是显式游戏假设。
- 内容：白边线/白中心虚线，12owner、16,284三角形，每owner一个paint mesh/material，不是完整交通标识全集。
- 未添加：停止/让行线、止まれ、日文路面文字、掉头/转向箭头、横断步道、限速、优先权或NPC行为。旧脚本有字不等于016新路有字。
- 保护owner：住宅 `0:-8, 0:-7, 1:-8, 1:-7`；POI `-1:-3, -1:-7`。扩展必须有新范围及真实支持，不能取消保护后全图铺旧线。
- 先验实际支持、owner、payload/shared哈希；staged apply原子且幂等，不改碰撞、抓地、导航或交通。
- 集成证据 `unified_markings016/evidence/integration016_review.md` 与 `integration016.json` 记录330/330检查和12owner天气生命周期。合同旧PENDING字段不能抹去后续证据，也不能自动证明最终验收。
- `drive_markings016_result.json` 记录原车191.309米低速R3路线通过，明确不是全图、交通、完整天气或APK验收。真实固定截图见 `capture_markings016.json`；有截图不代表全部问题已过复审。
- 主世界未设置 `snow_world_region`，12owner实际走非区域paint shader复制雪材质；独立fixture的区域路径只证明fixture。沥青与标线雪mask不保证逐像素一致。

## 世界规划与护栏

来源：`fuji_world_plan007/PLAN.md` 第4、6–9节。

- 保留道路、单世界和128米所有权，危险区间连续护栏，交通语义先于图形，小样回归后扩展。
- 1.5米落差或1:2外坡、路缘外1/2/4/8米采样、2米初采样与0.5米边界加密、护栏距路缘0.5–1.2米/柱距2–4米只是候选起点，不是法律或现实碰撞性能认证。
- 规划未单独证明全图悬崖100%覆盖、所有交叉口控制、完整停止/掉头、全图雪天驾驶或手机达标。014/015局部安全设施读各自合同，不向全图外推。
- 10条骨干设计长度约7.643公里，R3最大输入中心线坡度约11.12%，需单列雪天/停车风险。都是游戏场地数据，不是富士山测绘值。

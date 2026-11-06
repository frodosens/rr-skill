# 离线建模与合同

## 普通建筑 Geometry Nodes

从来源索引的普通建筑脚本复用结构，必要时在授权的工作副本修改。用 Python 创建节点不等于普通 Python mesh：检查空输入 mesh、NODES modifier、实际节点与连线，并对求值结果做验证。

节点做法：
1. 用 Mesh Cube 和 Transform 构成基础、墙体和门阶；将材质和曝光写在组件层。
2. 用 Mesh Line 生成水平开间点，Instance on Points 放窗。按首层门口位置排除完整窗组，不裁掉半扇窗；上层独立堆叠，保留门上方窗。
3. 后立面与左右立面旋转到外侧。检查窗框相对玻璃的法向方向，后面不能沿用前面偏移符号。
4. 住宅寄棟屋顶由控制立方体顶点位置场收拢成屋脊，再 Merge by Distance；离线清退化面并重算法线。屋顶与檐口闭合，避免墙上方细缝。
5. 商店用独立平顶、檐带、无品牌色条和普通文字节点；后勤门及后阶要单独排除窗组并计入包络。
6. LOD1 减窗棂和小细节，不缩小整栋。最终 Realize Instances 后求值，再导出。

住宅参数界面历史范围：宽6–12m、深6–10m、1–2层、层高2.8–3.3m、开间2–4、屋顶升高1.2–2.2m。商店另有范围。它们是编辑护栏，不是穷举验证；新的组合重跑门窗、闭合面、屋檐与合同测试。

历史精确样板，不当作普遍预算：

| 资产 | 完整包络 宽×深×高 m | LOD0/LOD1 三角形 | 材质表面数 |
|---|---|---|---|
| house_a_single | 9×7.55×5.26 | 920 / 260 | 6 / 5 |
| house_b_two_floor | 10×8.55×8.16 | 1784 / 404 | 6 / 5 |
| house_c_timber | 8×9.05×7.66 | 1784 / 404 | 5 / 4 |
| convenience_store | 16.8×10.1×3.75 | 1898 / 372 | 6 / 5 |

墙体 Width/Depth 小于完整包络；便利店后阶使后界到 z=-5.05m。不要沿用旧版总深度。

## 特殊温泉旅馆

用有明确房间翼和中央凹入入口的体块组织，不简单放大普通住宅。现有源为：石基、两侧客房翼、中央核心、连续寄棟屋顶、按朝向编写的窗框、门帘、外台阶。温泉池和屏风为可分离的视觉组合。

保持以下区别：
- 建筑本体近/远为6160/4516三角形、6材质面；带浴场和小物的 compound 为7000/4864、8材质面。远级仍较重，要按镜头与设备预算重新取舍。
- compound 是 visual-only 组合，不因包含建筑就继承完整碰撞/遮蔽所有权。池边、屏风和通路分别审查。
- 当前入口台阶只是表现，车辆走另行验证的前场。没有可用客房数量、室内、无障碍或消防合规结论。
- 14车位是前6后8；前排中央保留5.6m不停车区域，其中2.8m人行通道和两侧各1.4m缓冲。静态车在部分车位内放得下，不是转弯、倒车、开门或后排行人路线验收。

## 坐标、材质和雪曝光

导出合同统一米制、Godot/glTF +Y up、+Z front、底部 y=0、根变换单位。GN 源在 Blender 本地 Z-up 建造；显式 Mesh helper 使用 Godot 坐标并在导出前转成 Blender `(x,-z,y)`。不要再次重复转换。

历史色板为 cedar、charcoal、plaster、stone、vermilion、field、water、bamboo，GN 建筑实际使用7色。Blender 材质先做 sRGB→linear，Godot shader 使用 source_color。核查导出的真实材质和保存后的颜色，不混用线性/显示值。

Color.rgb 为色调乘数，Color.a 为雪曝光。GN 在 corner 域写入二值曝光，并清除朝下/竖直面的曝光；屋檐遮挡区与露出区台阶拆分。Godot shader 再乘 `smoothstep(0.18,0.8,world_normal.y)`。该逻辑不是物理积雪模拟，也不能从 headless 参数测试推断 GPU 显示正确。

## 合同最小字段

保存 asset ID/version、源文件与参数哈希、单位/轴向/根原点、实际 GLB AABB、LOD 文件/三角形/材质面、共享材质名、FrontDoor/FrontStep、可选 ServiceDoor/ServiceStep、基础标高、门宽、collision proxies、shelter descriptors、world placement 与验证状态。

未放置时 world placement 保持空或明确 unplaced。不要把展示地面、车辆或画面中的世界 transform 烘焙进模块。

## 可复现命令

仅在已经定位并审查完整依赖的资产工作副本内执行：

```sh
blender -b -t 2 --python source/build_node_assets.py
bash source/run_checks.sh
blender -b -t 2 --python source/render_assets.py
```

旅馆改用其 `source/build_hotel.py`，并单独检查上述 bounds、channels、parking 脚本的输入和输出路径。不要把旅馆的基础 `run_checks.sh` 误当已覆盖所有后补审计。生成脚本会覆盖副本的模型、合同和源 blend；保留旧版与失败证据。

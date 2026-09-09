# 场景审查与剪辑蓝图

## 抽帧覆盖

同时使用固定间隔帧和场景变化帧。固定帧用于避免漏掉长镜头内部的空间变化，场景变化帧用于找到门口、转身、进房和快速摇镜等边界。连续走拍默认每 1 秒取一帧；空间变化快或无法定位边界时改为每 0.5 秒，并回看边界前后原视频。

每个场景区间至少检查开始、中间、结束三处。最终入点/出点必须来自真实视频时间，不用缩略图序号冒充时间码。

## 房屋事实清单

先把用户资料整理为 `property-facts.json` 或等价表格，每条记录至少包含：

```text
fact_id,category,value,source,status,must_include,verbatim,notes
```

- `source` 使用 `user_provided`，不要把不可见事实写成视觉识别结果。
- `status` 使用 `confirmed` 或 `unknown`；不得自行把未知项补成确定事实。
- `must_include` 表示成片必须覆盖；`verbatim` 表示用户要求原句保留。
- 用户完整稿拆成事实和表达偏好后再重组，不把原稿顺序当作房间走访顺序。

## 房产空间分类

优先使用以下标准标签：

```text
entrance | corridor | kitchen | living_room | dining_area
balcony | sea_view | bathroom | bedroom_unknown | secondary_bedroom
master_bedroom | ensuite | storage | exterior | transport_view | transition
```

判断必须写可见证据：

- `kitchen`：灶台、水槽、橱柜、抽油烟机等成套烹饪设施。
- `living_room`：沙发/电视墙/主要起居空间，通常连接餐区或露台。
- `dining_area`：餐桌、餐椅、吊灯或与进餐功能明确相关的区域；即使与客厅相连也单独标记，避免在解说中漏掉餐厅。
- `balcony`：跨过门槛后的室外平台；只从室内看到玻璃门时写 `balcony_view_from_inside` 到 `subscene`。
- `sea_view`：水面或明确港景实际可见，不因旁白说“海景”就标记。
- `bathroom`：马桶、洗手盆、淋浴或浴缸等设施。
- `secondary_bedroom` 与 `master_bedroom`：只在空间顺序、面积、套卫、独立露台等证据足够时区分；否则用 `bedroom_unknown`。

同一源片段可以被切成多个空间区间。穿过门口、镜头被墙遮挡、快速甩镜、光线显著改变，都是候选边界。

场景地图另加 `visit_order` 或在 `notes` 中记录真实走访次序。旁白结构应由这条次序驱动：具名空间只有在镜头跨过门槛或已清楚展示其关键设施后才能开始对应口播。若前一个空间之后仍有更长、更完整的新空间镜头，口播顺序和时长必须随素材调整，不能套用预设房型顺序。

## 质量与用途

`shot_quality` 只标记用途，不把普通素材全部删除：

```text
hero       清楚展示核心卖点
support    能说明空间或设施
transition 有移动方向或进出关系
reject     严重模糊、遮挡、失焦，且没有叙事价值
```

先去除 `reject`，再从重复区间中保留信息最完整、运动最稳定的一段。移动段能说明空间关系时可保留短片，不允许它压过主体展示。

## 蓝图最低结构

```json
{
  "project": {"name":"...","fps":30,"width":1080,"height":1920},
  "beats": [
    {
      "id":"beat-01",
      "fact_ids":["fact-kitchen-01"],
      "narration":"进门先看到独立厨房",
      "required_scene":["entrance","kitchen"],
      "visual_start_seconds":3.2,
      "visual_end_seconds":6.1,
      "narration_start_seconds":3.4,
      "caption_start_seconds":3.4,
      "alignment_confidence":0.94,
      "clips":[
        {
          "source_path":"C:/absolute/source.mp4",
          "source_in_seconds":3.2,
          "source_out_seconds":6.1,
          "timeline_in_seconds":0.0,
          "timeline_out_seconds":2.9,
          "scene":"kitchen",
          "purpose":"从入口揭示厨房",
          "speed":1.0,
          "confidence":0.94
        }
      ]
    }
  ],
  "music":{"source":"jianying_library","instrumental":true},
  "captions":{"method":"jianying_smart_captions"}
}
```

所有源出点必须小于等于媒体时长；没有声明变速时，源时长与时间线时长一致。交通、户型数据等不能由现有画面证明的文字事实标为 `narration_only`，不得伪造镜头证据。

同时输出逐句对齐表 `narration-alignment.csv`：

```text
fact_id,fact_text,narration,scene,visual_in,visual_out,
narration_in,caption_in,confidence,notes
```

`narration_in` 和 `caption_in` 不得早于具名空间的有效视觉证据；允许为自然呼吸略晚开始。每个房间的口播字数按有效画面时长估算，不用统一字数强行填满所有空间。

## 蓝图通过条件

- 每句具象口播至少有一个语义匹配的画面区间。
- 最终口播在完整看片和场景地图锁定后生成，并能追溯到用户事实或可见证据。
- 楼盘、面积、楼层、交通、价格等不可见事实均来自用户资料；未知项没有被臆造。
- 没有把整条长素材原样放入时间线再统一变速。
- 每个主要场景至少有一个核心展示镜头；重复镜头有明确新信息才保留。
- 玄关、厨房、餐厅/餐区、客厅、露台、景观、卧室、卫生间等已被清楚拍到的主要空间均已进入场景地图；没有无故漏讲餐厅/餐区。
- 转场短于主体展示，且不会在错误房间上开始下一句口播。
- 每个具名空间 beat 的时间线入点不早于该空间的可见证据入点；尤其检查主卧和卫生间字幕是否抢跑。
- 时间线总时长来自片段之和、变速与配音实长，不靠音乐尾巴或黑屏补齐。
- 最后一条视频片段覆盖最后一句旁白；需要延长时使用有意义的交通镜头回放或房屋卖点回访，不冻结末帧。

# Kaka Vision Video Kit（卡卡视光短视频通用套件 · v5.0）

一套面向 **卡卡老师《视光小课堂》** 的 **1080×1920 @ 30fps 竖屏视光科普短视频生产套件**。现已升级至 **v5.0 路线 A+ 标准**：采用 **高密度皮克斯 / Apple Health 级 3D 精绘分镜 + 2.5D 电影运镜 + 毫米级校准 HTML5 Canvas 实时光学动效 + 30fps 口型同步卡卡老师**（半身精讲 / 192px 动嘴圆形头像 / 落地实景全身结尾），彻底告别暗黑背景、简陋几何建模与刻板 PPT 模板。

> 📘 **长期演进规划（A+ 主力标准 / B 谷歌 Veo 图生视频混剪 / C 后期 Blender 固定资产库）**：详见 [docs/PRODUCTION_ROADMAP.md](docs/PRODUCTION_ROADMAP.md)。

## 目录结构

```text
kaka-vision-video-kit/
├── assets/
│   ├── backgrounds/                 # 9:16 阳光明亮实景背景（含定制北欧极简阁楼、诊室、视光实验室等）
│   └── kaka_teacher/
│       ├── clean_base/              # 卡卡老师 16 套去嘴透明 PNG 标准立绘 (682x1024)
│       ├── mouths/                  # 6 帧标准口型字典 (mouth_01 ~ mouth_06)
│       └── kaka_mouth_sheet.png     # 口型总览表
├── voice/
│   ├── kaka_voice_clean_ref.wav     # 参考样音
│   └── ref_opening_sample.mp3       # 原片开场风格参考
├── src/
│   ├── synthesize_voice.py          # 多引擎配音脚本（默认 Edge zh-CN-XiaoyiNeural +8% -4Hz，支持分句纠音与变速）
│   ├── audio_mix_v2.py              # 杂志科普风 BGM + 电影级 UI/光学音效混音 + 30fps 口型状态机
│   ├── web_render_v2.py             # 30fps 多进程 Chromium 确定性渲染器（--keyframes 审片、0.0px 口型烘焙、零错校验与纯净 HTML 导出）
│   ├── render_core.py               # v1.0 PIL 通用 1080P 渲染核心（向后兼容）
│   └── render_episode_template.py   # 分集最小模板
├── episodes/
│   ├── ep05_* ~ ep12_*/             # 历代已验收分集工程（DOT 专题、角膜曲率与科学配镜专题）
│   └── ep13_binocular_vision_3d/    # EP13《视功能：被忽视的涨度数背后因素》v5.0 路线 A+ 标杆工程
│       ├── script.json              # 口播文案、节奏变速、镜头与音效编排
│       ├── scene.html               # 1080×1920 2.5D 运镜 + 实时 Canvas 光学动效 + 动嘴圆形/半身/落地全身编排
│       └── assets/                  # 6 张定制皮克斯 / Apple Health 级 3D 分镜原画
├── skills/
│   └── kaka-vision-producer/
│       └── SKILL.md                 # 标准化制作与验收 SOP（Agent Skill）
├── docs/
│   ├── PRODUCTION_ROADMAP.md        # 三阶段视觉演进路线图（A+ 主力 / B Google Veo / C Blender 固定资产库）
│   ├── PRODUCTION_SPEC.md           # 视觉坐标、立绘调用、音色与编码基础规范
│   └── mouth_rig_calibration.png    # 16 套立绘口型锚点标定参考图
└── requirements.txt                 # Python 依赖清单
```

## 环境准备

需要 **Python 3.10+**、**FFmpeg**（带 `libx264` 和 `aac`）、**Chromium**（通过 Playwright 安装）、中文字体（Linux 推荐 `fonts-noto-cjk`）以及 `rclone`（用于直传谷歌网盘）。

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 安装渲染器所需的无头 Chromium
playwright install chromium
```

## v5.0（路线 A+）标准分集制作流程（以 EP13 为例）

### 第 1 步：合成卡卡老师配音与精准时间轴
锁定 **方案 01「活力眼科小姐姐」**（`zh-CN-XiaoyiNeural`, `rate=+8%`, `pitch=-4Hz`，自动 `-16 LUFS` 响度统一，支持单句 `tts_text` 纠音与变速）：

```bash
.venv/bin/python -m src.synthesize_voice \
  --script episodes/ep13_binocular_vision_3d/script.json \
  --out-dir audio/ep13
```

### 第 2 步：快速导出全片关键帧审片（必检门禁）
在正式渲染 30fps 全片前，导出所有核心节拍的 1080×1920 关键帧与 `contact_sheet.png` 逐帧质检（核查零遮挡、安全区、光线锚点对齐、结尾落地站位）：

```bash
.venv/bin/python -m src.web_render_v2 \
  --scene episodes/ep13_binocular_vision_3d/scene.html \
  --audio-dir audio/ep13 \
  --prefix ep13 \
  --out-dir output/ep13_v5 \
  --keyframes
```

### 第 3 步：四线程并发渲染 1080P @ 30fps 成片 + 纯净单视频网页

```bash
.venv/bin/python -m src.web_render_v2 \
  --scene episodes/ep13_binocular_vision_3d/scene.html \
  --audio-dir audio/ep13 \
  --prefix ep13 \
  --out-dir output/ep13_v5 \
  --title "EP13 · 视功能：被忽视的涨度数背后因素（皮克斯级3D视光版）" \
  --fps 30 \
  --workers 4
```

### 第 4 步：直传谷歌网盘（严禁在 GitHub 留存大文件 Release）

```bash
rclone copyto output/ep13_v5/ep13_master.mp4 \
  "gdrive:kaka-vision-video-kit/episodes_1080p_mp4/EP13_视功能被忽视的涨度数背后因素_皮克斯3D视光版_1080P_v5.0.mp4"
rclone copyto output/ep13_v5/ep13_pure_video.html \
  "gdrive:kaka-vision-video-kit/episodes_1080p_mp4/EP13_视功能被忽视的涨度数背后因素_皮克斯3D视光版_纯净网页版_v5.0.html"
```

- GitHub 仓库仅保留轻量级源码、脚本与压缩分镜原画，不创建大文件 MP4/HTML Release。
- 详细视觉演进路线与 Google Veo / Blender 规划请查阅 [docs/PRODUCTION_ROADMAP.md](docs/PRODUCTION_ROADMAP.md) 与 [skills/kaka-vision-producer/SKILL.md](skills/kaka-vision-producer/SKILL.md)。

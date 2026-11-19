# Kaka Vision Video Kit（卡卡视光短视频通用套件 · v2.0）

一套开箱即用的 **2D 医学/视光科普竖屏短视频（1080×1920）高定生产套件**，包含卡卡老师标准角色立绘与 6 帧口型字典、5 张同画风 9:16 实景背景、Edge Neural TTS 活力眼科女声配音方案（保留 Qwen3-TTS 本地备选），以及 **v2.0 轻奢视光杂志风 HTML5/SVG/Canvas + Chromium 30fps 并发渲染引擎**（兼容 v1.0 PIL 渲染内核）。

## 目录结构

```text
kaka-vision-video-kit/
├── assets/
│   ├── backgrounds/                 # 5 张同画风 9:16 2D 实景背景（诊室/屈光室/教室/户外公园/儿童房）
│   └── kaka_teacher/
│       ├── clean_base/              # 卡卡老师 16 套去嘴透明 PNG 标准立绘 (682x1024)
│       ├── mouths/                  # 6 帧标准口型字典 (mouth_01 ~ mouth_06)
│       └── kaka_mouth_sheet.png     # 口型总览表
├── voice/
│   ├── kaka_voice_clean_ref.wav     # 参考样音
│   └── ref_opening_sample.mp3       # 原片开场风格参考
├── src/
│   ├── synthesize_voice.py          # v2.0 多引擎配音脚本（默认 Edge zh-CN-XiaoyiNeural +8% -4Hz，支持分句变速/同音修正与 Qwen3 备选）
│   ├── audio_mix_v2.py              # v2.0 杂志科普风 BGM + 电影级 UI/光学音效混音 + 30fps 口型状态机
│   ├── web_render_v2.py             # v2.0 30fps 多进程 Chromium 确定性渲染器（含 --keyframes 快速审片、0.0px 口型烘焙、零错校验与纯净 HTML 导出）
│   ├── render_core.py               # v1.0 PIL 通用 1080P 渲染核心（向后兼容）
│   └── render_episode_template.py   # v1.0 分集最小模板
├── episodes/
│   └── ep06_dot_principle/          # EP06《点扩散镜片 · 设计与防控原理》v2.0 高定分集工程
│       ├── script.json              # 口播文案、节奏变速、镜头与音效编排
│       └── scene.html               # 1080×1920 高定矢量光学动效与分镜模板
├── examples/
│   └── sample_script.json           # 脚本配置示例
├── docs/
│   ├── PRODUCTION_SPEC.md           # 视觉坐标、6套配色、立绘调用、音色与编码规范
│   └── mouth_rig_calibration.png    # 16 套立绘口型锚点标定参考图
└── requirements.txt                 # Python 依赖清单
```

## 环境准备

需要 **Python 3.10+**、**FFmpeg**（带 `libx264` 和 `aac`）、**Chromium**（通过 Playwright 自动安装）以及中文字体（Linux 推荐安装 `fonts-noto-cjk`）。

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 安装 v2.0 渲染器所需的无头 Chromium
playwright install chromium
```

## v2.0 高定分集制作流程（以 EP06 为例）

### 第 1 步：合成卡卡老师配音与精准时间轴（约 5 秒）
默认使用 **方案 01「活力眼科小姐姐」**（`zh-CN-XiaoyiNeural`, `rate=+8%`, `pitch=-4Hz`，自动 `-16 LUFS` 响度统一，支持单句 `tts_text` 纠音与变速）：

```bash
python -m src.synthesize_voice \
  --script episodes/ep06_dot_principle/script.json \
  --out-dir audio/ep06
```

### 第 2 步：快速渲染 12 张关键帧审片（约 10 秒）
在正式渲染 30fps 全片前，先导出所有核心分镜的 1080×1920 关键帧与 `contact_sheet.png` 逐帧质检：

```bash
python -m src.web_render_v2 \
  --scene episodes/ep06_dot_principle/scene.html \
  --audio-dir audio/ep06 \
  --prefix ep06 \
  --out-dir output \
  --keyframes
```

### 第 3 步：多核并发渲染 1080×1920 @ 30fps 超清成片 + 纯净单视频网页

```bash
python -m src.web_render_v2 \
  --scene episodes/ep06_dot_principle/scene.html \
  --audio-dir audio/ep06 \
  --prefix ep06 \
  --out-dir output \
  --title "卡卡老师《视光小课堂》EP06 · 点扩散镜片设计与防控原理 (1080P)" \
  --fps 30 \
  --workers 4
```

将自动输出并通过全片零错解码校验：
- `output/ep06_master.mp4`（1080×1920 · 30fps · H.264 High Profile + 自动闪避科普 BGM 与光学/UI 音效）
- `output/ep06_pure_video.html`（离线单页 `<video>` 播放器，体积自动控制在 20 MB 以内）

## 详细设计规范

请参阅 [docs/PRODUCTION_SPEC.md](docs/PRODUCTION_SPEC.md) 了解立绘库分工、口型标定与编码质检标准。

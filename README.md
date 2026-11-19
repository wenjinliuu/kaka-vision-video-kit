# Kaka Vision Video Kit（卡卡视光短视频通用套件）

一套开箱即用的 **2D 医学/视光科普竖屏短视频（1080×1920）通用底座**，包含卡卡老师标准角色立绘与 6 帧口型字典、5 张同画风 9:16 实景背景、Qwen3-TTS 纯净基线配音方案，以及基于 Python + FFmpeg 的逐帧超清渲染内核。

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
│   ├── kaka_voice_clean_ref.wav     # 干净人声参考样音
│   └── ref_opening_sample.mp3       # 原片开场风格参考
├── src/
│   ├── render_core.py               # 通用 1080P 渲染核心（背景柔光、2x矢量UI、口型同步、BGM混音、零错校验、纯净HTML导出）
│   ├── synthesize_voice.py          # 通用 Qwen3-TTS 纯净基线配音脚本（JSON 驱动 + 分段缓存）
│   └── render_episode_template.py   # 新分集最小可运行模板（含 --preview 快速预览模式）
├── examples/
│   └── sample_script.json           # 脚本配置示例
├── docs/
│   ├── PRODUCTION_SPEC.md           # 视觉坐标、6套配色、立绘调用、音色与编码规范
│   └── mouth_rig_calibration.png    # 16 套立绘口型锚点标定参考图
└── requirements.txt                 # Python 依赖清单
```

## 环境准备

需要 **Python 3.10+**、**FFmpeg**（带 `libx264` 和 `aac`）以及中文字体（Linux 推荐安装 `fonts-noto-cjk`，macOS/Windows 会自动识别 PingFang / 微软雅黑，也可通过环境变量 `KAKA_FONT_BOLD`、`KAKA_FONT_REG` 指定字体路径）。

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 确认 ffmpeg 可用
ffmpeg -version
```

## 快速上手（3 步产出新视频）

### 第 1 步：无音频快速预览排版（3 秒出图）
验证字体、实景背景、卡卡老师立绘与片尾落版是否正常：

```bash
python -m src.render_episode_template --preview output/template_preview.png
```

### 第 2 步：用 Qwen3-TTS 合成卡卡老师配音与时间轴
复制并修改 `examples/sample_script.json`，执行配音合成（首次运行会自动从 HuggingFace 拉取 `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`）：

```bash
python -m src.synthesize_voice \
  --script examples/sample_script.json \
  --out-dir audio/sample
```

将自动生成：
- `audio/sample/sample_vo_master.wav`（24kHz 纯净基线原声母带）
- `audio/sample/sample_timeline.json`（自动切分好的每幕与气泡时间戳）

### 第 3 步：逐帧渲染 1080×1920 超清 MP4 + 纯净单视频网页

```bash
python -m src.render_episode_template \
  --audio-dir audio/sample \
  --prefix sample \
  --out-dir output
```

将自动输出并通过全片零错解码校验：
- `output/sample_master.mp4`（1080×1920 · 25fps · H.264 High Profile + 自动混音 BGM/SFX）
- `output/sample_pure_video.html`（仅含全屏 `<video>` 播放器的离线纯净单页，体积自动控制在 20 MB 以内）

## 详细设计规范

请参阅 [docs/PRODUCTION_SPEC.md](docs/PRODUCTION_SPEC.md)，了解画布坐标体系、6 套同色系渐变、12 套白大褂常用立绘分工、M06 统一招手片尾规范以及 Qwen3-TTS 纯净基线音色调优要点。

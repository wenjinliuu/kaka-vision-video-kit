# 卡卡老师《视光小课堂》三阶段视觉制作路线图（A+ / B / C）

本文档沉淀 `kaka-vision-video-kit` 在 **EP13 v5.0** 验收定型后的长期视觉演进路线：以 **路线 A+（主力日更/周更最优解）** 为核心标准，**路线 B（Google Veo 图生视频混剪）** 为重点镜头画质跃迁方案，**路线 C（Blender 固定核心视光 3D 资产库）** 为长期资产沉淀规划。

---

## 一、路线总览与定位

| 路线 | 定位 | 核心技术栈 | 适用场景 | 当前状态 |
| :--- | :--- | :--- | :--- | :--- |
| **路线 A+（主力标准）** | **当前最优解 · 日常主力生产** | 高密度皮克斯/Apple Health 级 3D 精绘分镜 + 多层 2.5D 视差运镜 + 实时 Canvas 光学动效 + 动嘴圆形/半身/落地全身卡卡老师 | 全部常规科普更新（EP13+） | ✅ **已落地执行（v5.0 → v5.1 持续精进）** |
| **路线 B（混合动效）** | **重点爆款/关键镜头升级** | 路线 A+ 骨架 + 1～2 个重点镜头接入 **Google Veo 3.1 图生视频**（3～5 秒真动态 3D 镜头），上层仍叠加精准代码光学动效与字幕 | 置顶爆款、强冲击力开场、运动/产品展示镜头 | 🛠️ **接口方案已调研就绪，按需启用** |
| **路线 C（核心 3D 资产）** | **远期高频复用资产沉淀** | Blender 精建/采购 3～4 套永久高频医学模型（眼球、晶状体、离焦/点扩散镜片、眼轴对比），生活叙事场景仍用路线 A+ | 高频解剖旋转展示、专业原理深度篇 | 🗓️ **后期规划（待账号稳定放量后推进）** |

---

## 二、路线 A+（主力生产规范 · v5.1 精进要点）

在 EP13 v5.0 已验证的高质感基础上，后续所有新集数按以下精进标准执行，让画面更生动、细腻、有电影感：

1. **提高分镜图片密度，拒绝“一张图干撑太久”**
   - 遵循**「每 8～15 秒 / 每个独立论点或生活场景必换新画面」**原则；单条 90～120 秒视频建议配套 **6～9 张同画风定制 3D/皮克斯精绘分镜**，把抽象视光概念拆成一眼就能看懂的生动画面（如 EP13 中把“场景 03”拆成「阳光体育馆接篮球 POV」→「阳光木质阶梯防踩空 POV」双镜头叠化）。
   - 严禁重复使用旧诊室背景；每集按主题全新定制明亮、通透、有生命力的场景。
2. **升级多层 2.5D 纵深视差（Parallax）与微动效细节**
   - 在基础 Ken Burns 缓推之上，对适合的镜头增加**景深虚化切换（Rack Focus）**、**镜头光斑扫光（Specular Sweep）**、**3D 主体柔和悬浮呼吸**，并在必要时将前景/主体/背景拆层以不同速率微移，做出接近真 3D 机位移动的立体纵深感。
   - 所有光学光线、焦点漂移、测距标尺、神经信号光子流必须在渲染前**实测原画锚点像素坐标**（如瞳孔中心、球心、阶梯边缘、地板踢脚线），确保毫米级对齐、零遮挡。
3. **色彩、安全区与卡卡老师出场铁律**
   - **配色**：只用清新明亮活力色系（晴空淡蓝 `#edf8fe`、浅薄荷青 `#def3ee`、暖阳橡木/奶油白），绝不用暗黑底色或沉闷灰底。
   - **安全区**：全面屏左右安全留白 `>= 92px`，顶部刊头 `top: 154px`，底部字幕与头像严格控制在抖音标题区上方（`Y <= 1615px`）。
   - **卡卡老师编排**：
     - 开场 / 总结：半身精讲（柔和底部羽化）+ 左侧磨砂字幕卡；
     - 满屏科普 / 情景演示：右下角 **192px 动嘴圆形卡卡老师**（按 `POSE_MOUTH_RIG` 逐姿势像素居中 + 30fps 口型同步 + 声浪微动条）；
     - 结尾全身出镜：严格对齐背景实景地板高度，**脚踏实地 + 双层真实接触阴影与斜向窗光投影**，绝不悬空。
4. **交付与仓库红线**
   - **GitHub 零大文件、零 Release**：只提交轻量级 `scene.html`、脚本、文档及压缩分镜 JPG；
   - **谷歌网盘直传**：通过 `rclone` 将成片 MP4 与 `<20 MB` 纯净网页版直接上传至 `gdrive:kaka-vision-video-kit/episodes_1080p_mp4/`，旧版及时移入回收站。

---

## 三、路线 B（Google Veo 3.1 图生视频混合接入方案）

当某集视频中有 1～2 个极具表现力的镜头（例如：篮球真实朝镜头飞来、儿童离焦眼镜在阳光下缓慢 3D 旋转、书本翻页伴随焦距虚实呼吸），可用 **路线 A+ 生成的高定静帧作为首帧**，直接调用谷歌官方 **Gemini API · Veo 3.1** 生成 5 秒 9:16 真动态片段，再无缝接入现有渲染管线。

### 1. 官方 SDK 调用方式（`google-genai`）
前提：安装 `pip install -U google-genai` 并配置具备 Veo 权限的 `GEMINI_API_KEY`（或 Vertex AI 凭据）。

```python
import time
from google import genai
from google.genai import types

client = genai.Client()  # 读取环境变量 GEMINI_API_KEY
hero_img = types.Image.from_file(location="episodes/epXX/assets/s04_basketball.jpg")

operation = client.models.generate_videos(
    model="veo-3.1-generate-001",
    source=types.GenerateVideosSource(
        prompt=(
            "Sunlit Pixar 3D animated first-person POV in a bright sky-blue school gym, "
            "the orange basketball smoothly arcs forward toward camera with subtle spin "
            "and warm morning light rays, clean bright lighting, no text."
        ),
        image=hero_img,
    ),
    config=types.GenerateVideosConfig(
        aspect_ratio="9:16",
        resolution="1080p",
        duration_seconds=5,
        number_of_videos=1,
    ),
)

while not operation.done:
    time.sleep(15)
    operation = client.operations.get(operation)

video = operation.response.generated_videos[0].video
client.files.download(file=video)
video.save("output/veo_clips/s04_basketball_veo.mp4")
```

### 2. 无缝接入 `src/web_render_v2.py` 的确定性合成技巧
为保持四进程 Playwright 并发渲染 **100% 帧精确、零掉帧、零音画漂移**（避免浏览器 `<video>` 异步解码抖动）：
1. 用 FFmpeg 将 5 秒 Veo 视频拆帧为本地 30fps JPEG 序列（仅 ~150 帧，放 `.cache/` 不入 Git）：
   ```bash
   ffmpeg -i s04_basketball_veo.mp4 -vf "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -q:v 3 .cache/veo_s04/f_%04d.jpg
   ```
2. 在 `scene.html` 的 `window.renderFrame(state)` 中按 `frameIdx = Math.min(totalClipFrames - 1, Math.floor(state.beatElapsed * 30))` 同步切帧作为底层画面；
3. 上层依然叠加我们可控的 **1080×1920 矢量光学标尺、精准中文排版、磨砂字幕与 30fps 动嘴圆形卡卡老师**——兼顾「真电影动态」与「100% 医学严谨度」。

---

## 四、路线 C（远期 · Blender 固定核心视光 3D 资产库）

不针对每一集零散建模，而是待频道进入规模化阶段后，一次性沉淀 **4 个最高频复用的专业视光 3D 精模**（`.blend` + `.glb`，配套统一阳光明亮 HDRI 棚拍灯光）：

1. **儿童解剖级眼球模型**：含透明角膜、蓝/棕虹膜、可形变晶状体、睫状肌环、视网膜与眼轴拉长变形键（Shape Keys）；
2. **儿童光学镜片与镜架模型**：真实透明板材/钛架 + 可切换「多点离焦微透镜 / 点扩散光柔化 / 普通单光」镜片材质节点；
3. **眼轴与角膜曲率对比模型**：支持直观展示曲率陡/平、焦点落在视网膜前/后、眼轴增长趋势；
4. **眼脑视觉通路模型**：双眼 → 视交叉 → 视觉皮层的半透明玻璃/次表面材质雕塑。

> **分工原则**：高频医学解剖用 **路线 C**（建一次、用几十集），丰富多变的生活情景与故事画面始终坚持 **路线 A+ / B**，做到画质、医学严谨度与更新效率的最佳平衡。

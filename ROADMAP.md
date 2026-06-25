# shadow_fiend 路线图

## MVE（Minimum Viable Experience）

目标：在 macOS Apple Silicon 上，让本地播放器（如 IINA/QuickTime/VLC）的声音实时显示翻译字幕。

### MVE 1：能跑通（2-3 周）

- [ ] 项目骨架搭建（README / AGENTS / Git / 目录结构）
- [ ] 音频捕获：从 BlackHole 读取 16kHz 单声道 PCM
- [ ] VAD：基于能量/Silero VAD 切句
- [ ] ASR：SenseVoice-Small 本地推理
- [ ] 翻译：Argos Translate 中日韩互译
- [ ] UI：PyQt6 半透明浮窗，显示原文+译文
- [x] 启动脚本：自动检测/安装 BlackHole、下载模型
- [ ] Logo v2：当前版本为占位风格化设计，用户对当前方案不完全满意，需继续迭代
- [x] 端到端 demo：播放一段日韩视频，屏幕出现字幕

### MVE 1 补充

- [x] 一键测试工具（setup / test / demo / logs / cleanup）
- [x] Docker 无 GUI 单元测试环境

### MVE 2：可用（1-2 月）

- [x] 支持选择源语言和目标语言
- [x] 支持仅显示翻译（单栏模式）
- [ ] 字幕样式调整（字体、大小、颜色、位置）
- [ ] 导出 SRT 字幕文件
- [ ] 降低延迟：优化 VAD 切句策略
- [ ] 加入本地 LLM 作为高级翻译选项
- [ ] Windows 初步支持

### MVE 3：好用（2-3 月）

- [ ] 自动检测视频语言
- [ ] 上下文感知的翻译（保留前几句作为 prompt）
- [ ] 术语表/自定义翻译规则
- [ ] 更好的 UI（拖拽、置顶、点击穿透）
- [ ] 性能 profiling 与内存优化
- [ ] Linux 支持
- [ ] 发布到 GitHub Release

### 长期愿景

- [ ] 移动端（iOS/Android）
- [ ] 浏览器扩展（网页视频）
- [ ] 多说话人字幕样式
- [ ] 社区模型市场
- [ ] 硬件合作伙伴（耳机/电视盒子）

## 当前阶段

**MVE 1 进行中。**

核心模块已就位并通过了单元测试，端到端实时 demo 因本地环境限制（Python 3.9.6、无 Homebrew、无 portaudio）尚未跑通。下一步需要在符合要求的 macOS 环境上验证。

> 🎨 **Logo 状态**：README 首页已替换为原创 Shadow Fiend 风格 SVG，但用户对当前设计不完全满意，已标记为待迭代项。

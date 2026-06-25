# shadow_fiend 路线图

## MVE（Minimum Viable Experience）

目标：在 macOS Apple Silicon 上，让本地播放器（如 IINA/QuickTime/VLC）的声音实时显示翻译字幕。

### MVE 1：能跑通（2-3 周）

- [x] 项目骨架搭建（README / AGENTS / Git / 目录结构）
- [x] 音频捕获：从 BlackHole 读取 16kHz 单声道 PCM
- [x] VAD：基于能量/Silero VAD 切句
- [x] ASR：SenseVoice-Small 本地推理
- [x] 翻译：Argos Translate 中日韩互译
- [x] UI：PyQt6 半透明浮窗，显示原文+译文
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

**MVE 1 基本完成，已发布 v0.0.1。**

核心模块已就位，单元测试 15/15 通过，端到端实时 demo 已在 macOS Apple Silicon + BlackHole 2ch 环境验证通过（日语、韩语均可识别并翻译为中文字幕）。

剩余待解决问题：
- Logo v2 仍需迭代。
- 端到端延迟约 2–5 秒，需优化 VAD 切分策略、翻译路径与 ASR 推理效率。
- UI/UX 需要进一步打磨（样式调整、位置记忆、点击穿透等）。

下一步进入 **MVE 2：可用**，重点降低延迟、优化字幕样式与导出能力。

> 🎨 **Logo 状态**：README 首页已替换为原创 Shadow Fiend 风格 SVG，但用户对当前设计不完全满意，已标记为待迭代项。

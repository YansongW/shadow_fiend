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
- [x] Logo v2：影魔头像多尺寸 PNG 已生成
- [x] 端到端 demo：播放一段日韩视频，屏幕出现字幕

### MVE 1 补充

- [x] 一键测试工具（setup / test / demo / logs / cleanup）
- [x] Docker 无 GUI 单元测试环境

### MVE 2：可用（1-2 月）

- [x] 支持选择源语言和目标语言
- [x] 支持仅显示翻译（单栏模式）
- [x] 字幕样式调整（字体、大小、颜色、位置）
- [x] 导出 SRT 字幕文件
- [x] 降低延迟：Silero VAD + SenseVoice 短窗口流式 ASR
- [x] 系统托盘 / 菜单栏控制
- [x] 本地 opus-mt 翻译引擎（优先）+ Argos 回退
- [ ] 加入本地 LLM 作为高级翻译选项
- [ ] Windows 初步支持

### MVE 3：好用（2-3 月）

- [ ] 自动检测视频语言
- [ ] 上下文感知的翻译（保留前几句作为 prompt）
- [ ] 术语表/自定义翻译规则
- [x] 更好的 UI（拖拽、置顶、点击穿透、样式设置、位置记忆）
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

**v0.0.2 已发布。**

流式低延迟 pipeline 已落地：Silero VAD + SenseVoice 短窗口流式 ASR + opus-mt/Argos 本地翻译 + 系统托盘 UI。日/韩合成集端到端延迟：first_final 平均日 269 ms / 韩 230 ms（MPS 设备）。

v0.0.2 构建产物：
- `shadow_fiend-0.0.2-py3-none-any.whl`
- `shadow_fiend-0.0.2.tar.gz`

剩余待解决问题：
- 真实影视/带噪场景下的准确率与延迟（v0.0.3）。
- 降噪分离清晰人声（下一阶段）。
- 多人音色区分（长期）。

下一步进入 **MVE 3：好用**，重点提升嘈杂/真实场景鲁棒性、上下文翻译与 GitHub Release 分发。

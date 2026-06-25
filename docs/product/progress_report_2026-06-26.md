# shadow_fiend 产品进度汇报

**汇报日期**：2026-06-26  
**当前版本**：v0.0.3  
**汇报人**：DEV  

---

## 1. 项目概述

shadow_fiend（影魔）是一款**本地实时字幕翻译工具**，核心定位：

- **本地隐私优先**：所有音频识别、翻译均在本地完成，不调用任何商业云 API
- **实时低延迟**：看电影/剧集时，自动识别语音并叠加双语字幕
- **美观易用**：浮窗字幕 + 系统托盘/菜单栏控制

目标用户：观看无中文字幕的日韩影视内容的用户。

---

## 2. 版本完成情况

### v0.0.1（MVE 1：能跑通）— 已完成

- 项目骨架、README、AGENTS
- 音频捕获（BlackHole 2ch + PyAudio）
- 能量阈值 VAD 切句
- SenseVoice-Small 本地 ASR
- Argos Translate 本地翻译
- PyQt6 半透明浮窗字幕
- 端到端 demo 验证

### v0.0.2（MVE 2：降低延迟 + UI 升级）— 已发布

**发布时间**：2026-06-26  
**Release**：https://github.com/YansongW/shadow_fiend/releases/tag/v0.0.2

核心改进：
- Silero VAD 替代能量阈值 VAD，切句更鲁棒
- SenseVoice 短窗口流式 ASR（500 ms 窗口 / 200 ms hop）
- ASR 启动预热，避免首次推理卡顿
- 新增 opus-mt 本地翻译引擎（优先），Argos 回退
- 系统托盘 / 菜单栏控制器
- 影魔头像 Logo
- wheel + sdist 打包发布

**性能指标**（日/韩合成集，MPS 设备）：

| 指标 | 日语 | 韩语 |
|---|---|---|
| first_final 平均延迟 | 269 ms | 230 ms |
| 完整音频 ASR 准确率（CER） | 约 1.7% | 约 3.3% |

### v0.0.3（MVE 2：降噪分离清晰人声）— 已发布

**发布时间**：2026-06-26  
**Release**：https://github.com/YansongW/shadow_fiend/releases/tag/v0.0.3

核心改进：
- 集成 RNNoise 实时降噪模块
- Pipeline 数据流：音频捕获 → RNNoise → VAD → ASR → 翻译 → UI
- 托盘菜单和 CLI 均支持降噪开关
- 新增白噪声带噪测试集与降噪基准测试

**测试结果**：
- 在合成 TTS 测试集上，RNNoise 对 ASR CER **改善有限/部分场景下降**
- 原因分析：测试音频为 macOS `say` 合成短句，非真实人声；RNNoise 可能过度抑制 TTS 音色
- **结论**：降噪基础设施已就绪，真实人声/影视场景效果需进一步验证

---

## 3. 当前技术架构

```
┌─────────────────┐
│  BlackHole 2ch  │  系统音频环回
└────────┬────────┘
         ▼
┌─────────────────┐
│  Audio Capture  │  PyAudio, 16 kHz
└────────┬────────┘
         ▼
┌─────────────────┐
│  RNNoise        │  实时降噪（可开关）
└────────┬────────┘
         ▼
┌─────────────────┐
│  Silero VAD     │  语音活动检测
└────────┬────────┘
         ▼
┌─────────────────┐
│  SenseVoice     │  流式 ASR
└────────┬────────┘
         ▼
┌─────────────────┐
│  opus-mt/Argos  │  本地翻译
└────────┬────────┘
         ▼
┌─────────────────┐
│  PyQt6 UI       │  浮窗字幕 + 托盘
└─────────────────┘
```

---

## 4. 测试资产

- **合成集**：日/韩各 30 句，macOS `say` 生成
- **带噪集**：基于合成集叠加白噪声，SNR -10/-5/0/5/10/15 dB
- **测试分支**：所有测试代码、音频、报告在 `test` 分支
- **报告位置**：
  - `tests/asr_benchmark/results/sensevoice_report.json`
  - `tests/asr_benchmark/results/e2e_latency_report.json`
  - `tests/asr_benchmark/results/denoiser_report.json`

---

## 5. 已知问题与风险

| 问题 | 影响 | 状态 |
|---|---|---|
| RNNoise 在合成 TTS 集上效果不佳 | 可能让用户对降噪功能失望 | 真实场景待验证，已提供开关 |
| pyrnnoise 安装后 `import pyrnnoise` 失败（audiolab/av 17 不兼容） | 用户可能误以为安装失败 | 已绕过，动态加载内部 rnnoise.py |
| 真实影视/嘈杂人声素材缺乏 | 无法充分验证降噪和分离效果 | 需按用户要求使用公开数据集/CC 素材 |
| MPS 首次推理仍有预热延迟 | 首次 ASR 较慢 | 已添加 warmup，可接受 |
| 多人同时说话时 ASR 会串扰 | 下一阶段的音色分离需求 | 长期规划 |

---

## 6. 下一阶段计划

### v0.0.4 / MVE 3：真实场景验证 + 上下文翻译

- 收集/使用公开数据集或 CC 授权素材验证 Docker 镜像与降噪效果
- 评估 RNNoise 对 VAD 触发率的改善（不仅是 ASR CER）
- 尝试其他降噪方案（DeepFilterNet3 / Silero 语音增强）作为对比或替代
- 加入本地 LLM 作为高级翻译选项（可选）

### v0.0.5 / 长期：多人音色区分

- 说话人分离（Speaker Diarization）
- 按说话人区分字幕颜色/标签

---

## 7. 发布产物

当前 GitHub Releases 已发布：

| 版本 | 产物 |
|---|---|
| v0.0.2 | wheel + sdist |
| v0.0.3 | wheel + sdist |

**GitHub Packages**：

- 镜像地址：`ghcr.io/yansongw/shadow_fiend:latest`
- 标签：`0.0.3`、`latest`
- 平台：`linux/amd64`、`linux/arm64`
- 用途：开发环境一致性、无界面 CI 测试；GUI 模式需 X11 转发
- 构建方式：通过 `.github/workflows/docker-publish.yml` 在每次 Release 时自动构建推送

---

## 8. 资源需求

- 需要真实人声/影视测试素材（公开数据集或 CC 授权）
- 评估是否需要替换 RNNoise 为更适配音质的模型
- 后续可能需要更多磁盘空间用于多模型并存对比

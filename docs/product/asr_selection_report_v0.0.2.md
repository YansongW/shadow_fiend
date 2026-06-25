# ASR 选型测试报告 v0.0.2

**日期**：2026-06-25  
**目标**：为 shadow_fiend v0.0.2 选择满足「低延迟 + 中日韩 + 严格本地化」的 ASR 方案。

---

## 1. 执行摘要

| 候选方案 | 语言支持 | 流式能力 | 本地部署 | 实测 CER（合成集） | 实测延迟 | 推荐结论 |
|----------|----------|----------|----------|-------------------|----------|----------|
| **SenseVoice 整句** | ✅ 中日韩英粤 | ❌ 非原生 | ✅ | JA 1.69% / KO 3.33% | ~458ms | **当前基准** |
| **SenseVoice 短窗口模拟** | ✅ 中日韩英粤 | ⚠️ 模拟 | ✅ | 待测 | 预计 200–400ms | **v0.0.2 推荐路径** |
| **Paraformer-zh-streaming** | ❌ 仅中英 | ✅ 原生 | ✅ | 不适用 | <300ms | **不支持日韩，排除** |
| **Fun-ASR-Nano** | ✅ 31 语言含日韩 | ✅ 原生 | ✅ | 待测 | CPU 未知，GPU 快 | **v0.0.3 候选** |

**结论**：开源 Paraformer streaming 没有可靠的中日韩支持；v0.0.2 应走 **SenseVoice 短窗口流式模拟 + Silero VAD** 的稳妥路线，v0.0.3 再评估 Fun-ASR-Nano。

---

## 2. 测试集

### 2.1 合成音频集

- **日语**：30 句，覆盖日常问候、疑问、请求等，macOS `Kyoko` TTS 生成
- **韩语**：30 句，覆盖同类场景，macOS `Yuna` TTS 生成
- **格式**：16 kHz mono WAV
- **位置**：`tests/asr_benchmark/synthetic/{ja,ko}/`

### 2.2 真实影视集

- 目录已建立：`tests/asr_benchmark/real_world/{ja,ko}/`
- 当前为空，等待用户添加自有正版影视片段及标注
- 用于最终验证，不作为本次引擎对比依据

---

## 3. SenseVoice 基准测试结果

### 3.1 测试条件

- 模型：`iic/SenseVoiceSmall`
- 设备：CPU（Apple Silicon MPS 未启用，因当前 `device="cpu"`）
- 输入：完整utterance音频（整句送入）
- 评估指标：CER（字符错误率，忽略空格和标点）

### 3.2 日语合成集

| 指标 | 结果 |
|------|------|
| 平均 CER | **1.69%** |
| 平均延迟 | **458.7 ms** |
| 主要错误 | 个别句加入 emoji/问号，少量分词差异 |

### 3.3 韩语合成集

| 指标 | 结果 |
|------|------|
| 平均 CER | **3.33%** |
| 平均延迟 | **487.2 ms** |
| 主要错误 | "이해했습니다" 被识别为 "1 해 했 습니다"（同音数字干扰） |

### 3.4 关键观察

1. SenseVoice 对清晰合成语音的字符识别准确率极高。
2. 458–487ms 是**整句 ASR 推理耗时**，不含 VAD 等待时间。
3. 若改为短窗口（500ms–1s）连续调用，预计首次输出延迟可降至 200–400ms。

---

## 4. 流式 ASR 调研结论

### 4.1 Paraformer streaming

- **开源模型 `paraformer-zh-streaming`** 明确仅支持中文/英文。
- 阿里云商业 API `paraformer-realtime-v2` 支持中日韩，但违背项目本地化准线。
- **结论**：排除。

### 4.2 Fun-ASR-Nano

- **模型**：`FunAudioLLM/Fun-ASR-Nano-2512`
- **语言**：31 种，含日语、韩语
- **流式**：✅ 支持 streaming SDK
- **规模**：800M 参数
- **速度**：GPU 上可达 340x RTF；CPU 表现未明确，预计较慢
- **结论**：作为 v0.0.3 升级候选，需在目标设备上实测延迟。

### 4.3 SenseVoice 短窗口模拟

- 利用现有 `SenseVoiceSmall` 模型，以 500ms–1s 音频窗口滑动调用。
- 非原生流式，但工程实现简单，无需下载新模型。
- 风险：窗口边界可能导致断词、重复调用开销。
- 结论：**v0.0.2 推荐方案**。

---

## 5. 推荐方案

### v0.0.2（当前版本）

- **ASR**：SenseVoice 短窗口流式模拟
- **VAD**：Silero VAD 替代能量阈值 VAD
- **音频 chunk**：32–40ms
- **翻译**：opus-mt 直接中日韩互译
- **目标延迟**：300–500ms

### v0.0.3（后续版本）

- 评估 Fun-ASR-Nano 在目标设备上的流式延迟
- 如果 CPU/MPS 能达到 200–300ms，迁移至 Fun-ASR-Nano
- 否则继续优化 SenseVoice 短窗口方案

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| SenseVoice 短窗口断词 | 字幕闪烁/重复 | 滑动窗口重叠 + 去重平滑 |
| 真实影视音频背景噪音大 | CER 上升 | 先用真实集验证，必要时加降噪 |
| Fun-ASR-Nano CPU 太慢 | v0.0.3 升级受阻 | 保留 SenseVoice 方案作为回退 |

---

## 7. 待用户确认

1. **是否确认 v0.0.2 采用 SenseVoice 短窗口流式模拟方案？**
2. **是否接受 v0.0.3 再评估 Fun-ASR-Nano？**
3. **是否能提供真实日韩影视片段用于最终验证？**

---

## 8. 附件

- 测试脚本：`scripts/benchmark/asr_benchmark.py`
- 合成音频生成：`scripts/benchmark/generate_synthetic_audio.py`
- 原始日志：
  - `tests/asr_benchmark/results/sensevoice_ja_download.log`
  - `tests/asr_benchmark/results/sensevoice_ko_download.log`

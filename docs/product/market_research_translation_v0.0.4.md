# v0.0.4 市场与开源方案调研报告

**日期**：2026-06-26  
**版本**：v0.0.4 规划  
**汇报人**：DEV  

---

## 1. 调研目标

1. 了解市场上已有的实时翻译字幕产品（开源 + 闭源）及其技术路线
2. 评估自训练翻译模型的可行性、算力依赖、数据需求和产出效果
3. 为 shadow_fiend 的长期翻译方案选择提供决策依据

---

## 2. 市场产品分类

### 2.1 闭源/商业产品

| 产品 | 模式 | 技术路线 | 价格 | 隐私 |
|---|---|---|---|---|
| **Sokuji** | 本地离线 + 云端 | WebAssembly/WebGPU, sherpa-onnx ASR, Opus-MT/TranslateGemma/Qwen | 免费/付费 | 本地模式隐私好 |
| **my-translator** | 桌面应用 | OpenAI Realtime, Qwen LiveTranslate, 本地 MLX+Whisper+Gemma | API 按量 / 免费预览 | 本地模式可离线 |
| **AI 字幕助手（ various ）** | 云服务 | Whisper ASR + GPT/DeepL 翻译 | 订阅制 | 音频上传云端 |
| **PotPlayer + 翻译插件** | 播放器插件 | OCR/内置 ASR + 在线翻译 API | 免费+API费用 | 依赖在线 API |

**共同特点**：

- 云端方案普遍使用 Whisper + LLM/GPT/DeepL，效果好但依赖网络
- 本地方案普遍使用 Whisper/Faster-Whisper + Opus-MT/NLLB/m2m-100/小型 LLM
- 商业产品都在向"本地离线"方向发展，以满足隐私需求

### 2.2 开源项目

| 项目 | 定位 | 技术栈 | 备注 |
|---|---|---|---|
| **LavX/ai-subtitle-translator** | SRT 字幕翻译 API | OpenRouter + LLM（Gemini/Claude/Llama） | 非实时，批量处理 |
| **phuc-nt/my-translator** | 实时语音翻译桌面应用 | Tauri, Whisper/SenseVoice, OpenAI/Qwen/MLX | 支持本地 Apple Silicon |
| **rockbenben/subtitle-translator** | 浏览器字幕翻译工具 | Next.js, 在线 API | 批量 SRT 翻译 |
| **luizomf/nlingua2** | 离线字幕翻译 CLI | Whisper + Meta NLLB | 离线，CPU 可跑 |
| **TTomas65/Subtitle-Translator-for-LM-Studio** | SRT 翻译 web 工具 | LM Studio 本地 LLM / ChatGPT API | 字幕文件翻译 |
| **real-time-translation topic 项目** | 实时翻译集合 | 各种 ASR + LLM/翻译模型 | 38+ 个项目 |

**观察**：

- 实时翻译的开源项目多依赖 LLM API 或本地小 LLM
- 纯离线实时翻译仍是难点，尤其是低延迟 + 高质量
- 大多数项目聚焦"字幕文件翻译"而非"实时字幕"

---

## 3. 技术路线对比

### 3.1 ASR 方案

| 方案 | 特点 | 本地延迟 | 适用场景 |
|---|---|---|---|
| **Whisper (OpenAI)** | 准确率高，多语言 | 中等 | 通用 |
| **Faster-Whisper** | Whisper 的 CTranslate2 加速版 | 较快 | 本地实时 |
| **WhisperX** | 加 VAD + diarization | 中等 | 需要说话人区分 |
| **SenseVoice (阿里)** | 对中日韩优化，支持情感/事件 | 快 | 中日韩实时 |
| **sherpa-onnx** | 轻量，支持流式 | 很快 | 边缘设备 |
| **April-ASR** | 本地离线 | 快 | 低资源 |

**shadow_fiend 当前选择**：SenseVoice + Silero VAD，对中日韩友好，延迟低。

### 3.2 翻译方案

| 方案 | 特点 | 本地延迟 | 训练成本 |
|---|---|---|---|
| **Opus-MT** | 多语言对，模型小（~80M） | 快 | 预训练，无需训练 |
| **NLLB-200** | 200 语言，单模型多向 | 中等（600M–1.3B） | 可微调 |
| **m2m-100** | 100 语言，单模型多向 | 中等（418M） | 可微调 |
| **Google Translate API** | 云端，效果极好 | 依赖网络 | 无 |
| **DeepL API** | 云端，欧洲语言强 | 依赖网络 | 无 |
| **LLM（Qwen/Gemma/Llama）** | 上下文理解强 | 慢（本地）/ 按量（API） | 可微调但成本高 |
| **CTranslate2 加速** | 推理引擎优化 | 比 transformers 快 15–38% | 无 |

**shadow_fiend 当前选择**：opus-mt 直接对 + 英语 pivot，已做动态 max_length、重复截断、warmup、缓存优化。

### 3.3 部署加速方案

| 方案 | 效果 | 复杂度 | Apple Silicon |
|---|---|---|---|
| **CTranslate2** | 15–38% 加速 | 中 | CPU + Accelerate |
| **ONNX Runtime + CoreML** | 可能更高 | 高 | CoreML |
| **MLX（Apple）** | Apple Silicon 优化 | 中 | 极佳 |
| **量化 INT8** | 速度提升，但可能损失质量 | 低 | 支持 |
| **蒸馏小模型** | 大幅加速 | 高 | 好 |

---

## 4. 自训练翻译模型的可行性分析

### 4.1 为什么不建议 RNN / CNN

| 架构 | 问题 |
|---|---|
| **RNN（LSTM/GRU）** | 训练慢、并行差、长距离依赖弱，2017 年后基本被 Transformer 淘汰 |
| **CNN** | 适合局部模式，翻译任务需要长距离依赖，效果差 |
| **结论** | 投入产出比极低，不建议 |

### 4.2 可行的自训练方向

#### 方向 A：微调多语言基础模型（推荐）

**候选模型**：

- `facebook/m2m-100_418M`
- `facebook/nllb-200-distilled-600M`
- `facebook/mbart-50-large-many-to-many-mmt`

**优势**：

- 一个模型支持多语言，无需 pivot
- 可以直接学习 ja→zh / ko→zh / en→zh
- 支持无标点短句 fine-tuning

**劣势**：

- 模型比 opus-mt 大（418M–600M vs 80M）
- 推理延迟更高
- 需要准备平行语料

**算力需求**：

- 据文献：NLLB-600M 微调 3 epochs，GH200 120GB GPU 可完成
- m2m-100 418M 微调：单 GPU（A100/V100）数小时到数十小时
- 低资源场景（1–5 万句对）：单 A100 约 10–50 GPU 小时

#### 方向 B：蒸馏 opus-mt 到小型 Transformer

**思路**：

- 教师模型：`opus-mt-ja-en` + `opus-mt-en-zh` 串联
- 学生模型：30M–60M 参数的 ja→zh 直接 Transformer

**优势**：

- 模型小、推理快
- 专门针对 ja→zh / ko→zh
- 可控制输出风格

**劣势**：

- 需要蒸馏技术经验
- 需要平行语料
- 工程复杂度高

**算力需求**：

- 中等：A100 上数十 GPU 小时
- 需要反复调优温度、loss、层数

#### 方向 C：在影视字幕数据上微调 opus-mt

**思路**：

- 保持 MarianMT 架构
- 在 OpenSubtitles 等影视字幕平行语料上继续训练

**优势**：

- 工程改动小
- 可以让模型适应口语化、无标点短句

**劣势**：

- 仍受限于 MarianMT 架构
- pivot 问题未解决
- 需要中日/中韩直接语料

### 4.3 数据需求

| 数据规模 | 预期效果 | 适用方向 |
|---|---|---|
| <1 万句对 | 基本不可用 | 无 |
| 1–5 万句对 | 可用但质量一般 | 微调 m2m-100/NLLB |
| 5–20 万句对 | 较好 | 微调 + 数据增强 |
| >50 万句对 | 接近商业水平 | 全量训练/蒸馏 |

**关键**：需要 **ja→zh 直接平行语料**，而不是通过 en 的 pivot 语料。

### 4.4 可用数据集

| 数据集 | 语言对 | 领域 | 规模 | 获取难度 |
|---|---|---|---|---|
| **OpenSubtitles 2018** | ja/zh/ko/en | 影视字幕 | large | 中 |
| **JParaCrawl** | ja↔en | 网页 | large | 易 |
| **Korean Parallel Corpora** | ko↔en | 通用 | medium | 易 |
| **CCMatrix** | ja/zh/ko/en | 网页 | huge | 中（需清洗） |
| **Tatoeba** | ja/zh/ko/en | 简单句 | small | 易 |
| **Anime/J-drama fan subs** | ja→zh | 影视 | medium | 难（版权/整理） |

**数据准备成本**：

- 下载和清洗：数天到数周
- 对齐和质量过滤：需要规则和人工抽检
- 影视字幕数据尤其需要处理时间轴、多说话人、语气词

### 4.5 算力成本估算

| 方案 | 硬件 | 时间 | 估算成本（按云 GPU） |
|---|---|---|---|
| 微调 m2m-100 418M | 单 A100 40GB | 10–30 小时 | $100–$300 |
| 微调 NLLB 600M | 单 A100 40GB | 20–60 小时 | $200–$600 |
| 蒸馏 60M 学生模型 | 单 A100 40GB | 50–200 小时 | $500–$2,000 |
| 从头训练 Transformer | 单 A100 40GB | 100–500 小时 | $1,000–$5,000 |
| Apple Silicon 本地训练 | M3 Max 36GB | 数倍于 A100 | 时间成本极高 |

**注意**：

- Apple Silicon 可以训练小模型，但 400M+ 模型训练非常慢
- 建议使用云 GPU（AWS/Google Cloud/AutoDL）进行实验
- 生产化后推理可在 Apple Silicon CPU 上运行

### 4.6 预期效果

| 方案 | 预期 BLEU（ja→zh） | 推理延迟（Apple Silicon CPU） | 质量 |
|---|---|---|---|
| 当前 opus-mt pivot | 中等 | 100–150 ms | 有幻觉、重复问题 |
| 微调 m2m-100 418M | 20–35 | 150–300 ms | 明显改善 |
| 微调 NLLB 600M | 25–40 | 200–400 ms | 较好 |
| 蒸馏小模型 | 15–30 | 30–80 ms | 快但质量需调优 |
| 商业 API | 40+ | 依赖网络 | 最好 |

---

## 5. 对 shadow_fiend 的建议

### 5.1 短期（v0.0.4）

**已完成**：

- 动态 max_length
- 重复 token 截断
- 翻译 warmup
- 高频短句缓存

**建议继续**：

- 端到端延迟基准测试，量化优化效果
- 评估 m2m-100 418M 在本地的推理延迟（不训练，仅测试预训练模型）
- 整理 OpenSubtitles 中日/中韩平行数据的可行性

### 5.2 中期（v0.0.5-v0.0.6）

**方案 A（推荐）**：微调 m2m-100 418M 或 NLLB-600M

- 用 OpenSubtitles + JParaCrawl + Korean Parallel 数据
- 目标是获得一个支持 ja→zh / ko→zh / en→zh 的单模型
- 消除 pivot 延迟

**方案 B**：蒸馏专用小模型

- 若 m2m-100 延迟过高，可蒸馏一个 60M–100M 的专用模型
- 需要更多工程投入

### 5.3 长期

- 构建影视字幕专用数据集
- 训练领域-specific 翻译模型
- 结合 LLM 做后编辑（高质量模式）

---

## 6. 风险提示

1. **自训练模型是中长期投入**：至少需要 1–2 个月的数据准备和实验
2. **算力成本不低**：即使是微调，也需要 A100 级别的 GPU
3. **数据质量决定上限**：垃圾数据会训练出垃圾模型
4. **Apple Silicon 训练不现实**：可以做推理，但训练大模型太慢

---

## 7. 待 PM 确认事项

1. **是否同意短期 v0.0.4 继续以现有优化为主，不启动模型训练？**
2. **是否授权我先测试 m2m-100 418M 在本地的推理延迟和质量？**（不训练，仅评估）
3. **是否愿意投入资源整理 OpenSubtitles 中日/中韩平行数据？**
4. **如果决定训练模型，预算上限是多少？**（决定用 m2m-100 微调还是蒸馏小模型）

# v0.0.4 本地翻译延迟优化调研报告

**日期**：2026-06-26  
**版本**：v0.0.4 规划  
**汇报人**：DEV  

---

## 1. 背景与目标

v0.0.2/v0.0.3 已实现流式 ASR 与 opus-mt 本地翻译，但在实际观影体验中，**翻译输出仍存在可感知的延迟和偶发错误**。v0.0.4 的核心目标不是新增功能，而是**把本地翻译延迟降到用户无感知的水平**，并提升翻译稳定性。

本报告调研本地部署场景下可行的翻译加速方案，并给出最适合 shadow_fiend 的推荐路径。

---

## 2. 当前实现与延迟来源

### 2.1 当前实现

当前翻译引擎位于 `src/translation/opus_engine.py`：

- 框架：`transformers.AutoModelForSeq2SeqLM` + `AutoTokenizer`
- 模型：Helsinki-NLP/opus-mt 系列（Marian NMT）
- 推理参数：`num_beams=1`（greedy）、`max_length=128`
- 中日/中韩等无直接模型时，走 **英语 pivot**（ja→en→zh，两次翻译）
- 默认设备：CPU（实测 MarianMT 小模型在 Apple Silicon MPS 上反而慢于 CPU）

### 2.2 延迟来源

| 来源 | 影响 | 备注 |
|---|---|---|
| **transformers 框架开销** | 高 | 通用框架，未针对翻译推理优化 |
| **模型推理本身** | 高 | 6+6 层 Transformer，每句需编码+自回归解码 |
| **pivot 路径** | 极高 | ja→zh 需连续跑 ja→en 和 en→zh 两个模型 |
| **模型加载/首次推理** | 中 | 首次翻译需加载模型；启动时无翻译 warmup |
| **tokenizer 编解码** | 低 | 通常 <10 ms |
| **max_length 设置** | 中 | 128 对短句偏保守，但仍影响内存与缓存 |

当前端到端延迟（粗略估计，Apple Silicon CPU）：

- 直接对（en→zh）：约 100–300 ms
- pivot 对（ja→zh / ko→zh）：约 200–600 ms，甚至更高
- 句子越长、生词越多，延迟越不可控

---

## 3. 可行方案调研

### 3.1 方案 A：CTranslate2 替换 transformers 推理（推荐）

**原理**：CTranslate2 是专为 Transformer Seq2Seq 推理优化的 C++ 运行时，支持模型转换、量化、层融合、缓存机制等。

**对 opus-mt 的支持**：

- 官方支持 `MarianMT` / `OPUS-MT` 模型转换：`ct2-transformers-converter`
- 转换示例：
  ```bash
  ct2-transformers-converter \
    --model Helsinki-NLP/opus-mt-ja-en \
    --output_dir ct2-opus-mt-ja-en \
    --quantization int8
  ```

**性能数据**（官方 benchmark，OPUS-MT En→De）：

| 运行时 | CPU tokens/s | 内存 |
|---|---|---|
| Transformers 4.26 | 147.3 | 2332 MB |
| Marian 1.11 | 344.5 | 7605 MB |
| CTranslate2 | 525.0 | 721 MB |
| CTranslate2 INT8 | 696.1 | 516 MB |

在 CPU 上预计 **3–5 倍加速**，INT8 量化后模型体积和内存均减半。

**Apple Silicon 适配**：

- CTranslate2 在 Apple Silicon 上**不使用 Metal/MPS**，而是调用 Apple Accelerate Framework 优化 CPU 矩阵运算
- 官方和社区实测：Apple Silicon CPU 上性能可接近部分 GPU 场景
- 与当前项目默认 CPU 策略一致，无需额外处理 MPS 兼容问题

**优缺点**：

- ✅ 与 opus-mt 模型生态完全兼容
- ✅ 推理速度提升显著（3–5x）
- ✅ INT8 量化简单，内存占用大幅降低
- ✅ 支持 batch translation，可进一步提吞吐
- ❌ 首次使用需转换模型（可在 setup 时自动完成）
- ❌ 增加一个原生依赖（但 pip 安装 `ctranslate2` 即可）

### 3.2 方案 B：ONNX Runtime + CoreML

**原理**：将 MarianMT 导出为 ONNX，使用 ONNX Runtime 推理，在 Apple Silicon 上通过 CoreMLExecutionProvider 调用 ANE/GPU。

**实现路径**：

- 使用 `optimum[onnxruntime]` 的 `ORTModelForSeq2SeqLM.from_pretrained(..., from_transformers=True)`
- 或在导出时指定 `CoreMLExecutionProvider`

**性能预期**：

- CoreML 可利用 Apple Neural Engine，理论上延迟最低
- 但 MarianMT 导出 ONNX 存在已知问题：需手工处理 generate 循环、softmax、decoder 输入等

**优缺点**：

- ✅ 有机会利用 ANE，延迟最低
- ✅ 跨平台（Windows/Linux 也能跑 CPU/CUDA）
- ❌ 导出和部署复杂度高
- ❌ MarianMT Seq2Seq 的 ONNX 支持不如 encoder-only 成熟
- ❌ 量化与动态 shape 处理较麻烦

### 3.3 方案 C：模型量化（INT8/FP16）

**原理**：降低权重精度，减少内存带宽和计算量。

**实现方式**：

- CTranslate2 自带 INT8/INT16/FP16 量化（推荐与方案 A 结合）
- PyTorch 动态量化：对 MarianMT 支持有限，效果不如 CTranslate2
- ONNX Runtime 量化：可行但复杂

**推荐**：与 CTranslate2 一起使用 INT8，几乎无损加速。

### 3.4 方案 D：批处理与预翻译缓存

**批处理**：

- 当前每句单独翻译。若 VAD 切出多句短句，可合并为 batch 一起推理
- CTranslate2 的 `translate_batch` 对 batch 效率更高
- 但实时字幕不能等太久，适合在 VAD 触发后 micro-batch（如 50–100 ms 窗口）

**预翻译缓存**：

- 缓存高频短句/常见表达（如 "谢谢"、"等一下"）
- 对影视中重复出现的台词、语气词有效
- 实现简单，可作为辅助优化

### 3.5 方案 E：使用更小/蒸馏模型

**思路**：用更小的翻译模型替代 opus-mt。

候选：

- `Helsinki-NLP/opus-mt-tiny-*` 系列（体积更小，速度更快）
- 自行蒸馏一个针对日/韩→中的轻量模型

**优缺点**：

- ✅ 速度最快
- ❌ 准确率可能下降
- ❌ 需要训练或筛选模型，工作量大

### 3.6 方案 F：本地 LLM 翻译

**思路**：使用 Qwen2.5、Llama 等本地小模型进行翻译。

**优缺点**：

- ✅ 上下文理解强，术语/省略句处理更好
- ❌ 延迟高（即使是 7B 模型也很难实时）
- ❌ 内存占用大
- ❌ 不符合 v0.0.4 降低延迟的目标

**结论**：v0.0.4 不建议采用本地 LLM，可在未来作为"高质量模式"选项。

---

## 4. 方案对比

| 方案 | 延迟改善 | 实现复杂度 | Apple Silicon 适配 | 准确率影响 | 推荐度 |
|---|---|---|---|---|---|
| A. CTranslate2 | 高（3–5x） | 中 | 好（Accelerate CPU） | 几乎无损 | ⭐⭐⭐⭐⭐ |
| B. ONNX + CoreML | 可能最高 | 高 | 好 | 需验证 | ⭐⭐⭐ |
| C. 量化 | 中高 | 低（配合 A） | 好 | 几乎无损 | ⭐⭐⭐⭐⭐ |
| D. 批处理/缓存 | 中 | 低 | 好 | 无 | ⭐⭐⭐⭐ |
| E. 小模型 | 高 | 高 | 好 | 可能下降 | ⭐⭐ |
| F. 本地 LLM | 慢 | 中 | 中 | 好 | ⭐ |

---

## 5. 推荐方案

### 5.1 主路径：CTranslate2 + INT8 量化

**原因**：

1. 与现有 opus-mt 模型生态完全兼容，无需重新训练或寻找新模型
2. 在 Apple Silicon CPU 上可获得 3–5 倍加速，直接解决感知延迟
3. INT8 量化后模型体积和内存大幅下降，对本地部署友好
4. 实现复杂度适中，风险可控
5. 为后续批处理、缓存等优化打下基础

### 5.2 辅助优化

- **翻译 warmup**：启动时预热一次翻译模型，避免首次 utterance 卡顿
- **预翻译缓存**：对高频短句建立 LRU 缓存
- **micro-batch**：在 VAD 触发后短窗口内合并 2–3 句一起翻译（需评估延迟收益）
- **合理 max_length**：根据输入长度动态设置，避免固定 128 的浪费

### 5.3 备选路径

- 若 CTranslate2 效果不及预期，再投入 ONNX + CoreML
- 若 pivot 路径延迟仍高，考虑寻找 ja→zh / ko→zh 的直接 opus-mt 替代模型或训练蒸馏模型

---

## 6. 实施计划

| 步骤 | 任务 | 产出 |
|---|---|---|
| 1 | 在本地环境验证 CTranslate2 转换 opus-mt 模型（ja→en、en→zh、en→zh 直接对） | 转换脚本 + 初步延迟数据 |
| 2 | 实现 `CTranslate2Engine`，保持与 `OpusEngine` 相同接口 | 可运行的翻译引擎 |
| 3 | 对比 Transformers / CTranslate2 / CTranslate2 INT8 在测试集上的延迟与 BLEU/CER | 对比报告 |
| 4 | 集成到 `pipeline_streaming.py`，替换默认翻译引擎 | 更新后的 pipeline |
| 5 | 添加翻译 warmup 与高频短句缓存 | 延迟进一步降低 |
| 6 | 端到端延迟基准测试（日/韩合成集） | v0.0.4 延迟报告 |
| 7 | 更新 README / CHANGELOG / ROADMAP | 文档同步 |

---

## 7. 待 PM 确认事项

1. **是否同意 v0.0.4 以 CTranslate2 + INT8 作为翻译延迟优化的主路径？**
2. **是否接受首次 setup 时自动转换模型（增加首次安装时间，但后续推理更快）？**
3. **micro-batch 是否要做？** 还是先做 CTranslate2 替换，再评估是否需要？
4. **翻译 warmup 是否加入启动流程？** 会增加启动时间约 1–3 秒，但避免首次字幕延迟。

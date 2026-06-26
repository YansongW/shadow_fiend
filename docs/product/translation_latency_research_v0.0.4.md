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

## 5. 实测结果

已在隔离虚拟环境 `.venv-ctranslate2-benchmark` 中完成实测，原始数据见 `translation_latency_benchmark_v0.0.4.json`。

### 5.1 测试环境

- Python 3.9（系统默认）
- torch 2.8.0
- transformers 4.57.6
- ctranslate2 4.8.0
- 设备：macOS Apple Silicon（M-series）
- 测试句：10 句日→英、10 句英→中短句，每句跑 20 轮

### 5.2 延迟对比

| 语言对 | transformers (ms) | CTranslate2 fp32 (ms) | CTranslate2 int8 (ms) |
|---|---|---|---|
| ja→en | 31.06 | 26.32（-15%） | 19.17（-38%） |
| en→zh | 72.43 | 61.05（-16%） | 46.47（-36%） |

**结论**：

- CTranslate2 确实有加速，但 **远没有官方 benchmark 的 3–5 倍**，在 shadow_fiend 的短句场景下只有 **15–38%**。
- 原因是当前 `OpusEngine` 已经使用 `num_beams=1`（greedy）和 CPU，transformers 的框架开销被限制在较小范围。
- 内存占用 CTranslate2 明显更低（ja→en fp32 仅 0.34 MB vs transformers 1.7 MB），但这不是当前主要瓶颈。

### 5.3 质量对比（以 transformers 输出为参考）

| 语言对 | CTranslate2 fp32 BLEU | CTranslate2 int8 BLEU |
|---|---|---|
| ja→en | 100.00 | 71.99 |
| en→zh | 98.48 | 97.23 |

**结论**：

- fp32 几乎无损。
- **int8 在 ja→en 上质量下降明显**，不适合直接采用。
- int8 在 en→zh 上尚可，但与 fp32 相比收益不大。

### 5.4 意外发现：无标点短句会重复输出

在测试中发现一个比延迟更严重的问题：

- `Hello`（无标点）→ `你好 你好 你好 你好 你好...`（重复到 max_length）
- `Hello.`（有句号）→ `你好,我叫艾莉森`（正常）
- `Thank you very much` → `非常感谢`（正常）

**影响**：

- ASR 输出通常没有标点，频繁出现单字/短词时可能触发重复生成
- 这比延迟更直接影响用户体验
- 可能是 opus-mt-en-zh 模型对无上下文短输入的退化现象

---

## 6. 重新评估推荐方案

基于实测，之前"CTranslate2 + INT8 可加速 3–5 倍"的判断过于乐观。修正后的判断：

### 6.1 CTranslate2 是否值得引入？

- **收益**：延迟降低 15–38%，内存降低明显
- **代价**：
  - 增加依赖和模型转换步骤
  - INT8 在 ja→en 上质量不可接受，fp32 收益有限
  - 需要维护两套 tokenizer/推理路径
- **结论**：可以作为后续优化，但**不是 v0.0.4 的银弹**，不应作为唯一主路径

### 6.2 真正影响体验的瓶颈

按优先级排序：

1. **pivot 路径的双倍延迟**：ja→zh / ko→zh 需 ja→en→zh 两次推理，en→zh 本身已 72 ms，pivot 路径约 100–150 ms
2. **无标点短句重复生成**：直接影响字幕可读性
3. **max_length=128 固定值**：短句也按 128 解码，浪费算力
4. **缺少翻译 warmup**：首次 utterance 可能额外卡顿
5. **transformers 框架开销**：当前影响已较小

### 6.3 修正后的 v0.4 优化路径

**第一阶段（低风险、高感知收益）**：

1. **动态 max_length**：根据输入 token 长度设置合理的 max_length（如输入长度 + 20），避免短句过度解码
2. **无标点短句保护**：
   - 检测重复 token 并截断
   - 对 ASR 输出尝试自动补标点（如基于规则的句尾补全）
3. **翻译 warmup**：启动时预跑一句，消除首次延迟
4. **预翻译缓存**：高频短句/语气词缓存

**第二阶段（需要评估）**：

5. **CTranslate2 fp32 替换**：在确认收益大于维护成本后引入，优先用于 en→zh 直接对
6. **寻找 ja→zh / ko→zh 直接模型**：若能找到直接对模型，可消除 pivot 双倍延迟
7. **micro-batch**：在 VAD 触发后短窗口内合并 2–3 句

**不建议 v0.0.4 做**：

- INT8 量化（ja→en 质量损失大）
- 本地 LLM（延迟高）
- ONNX + CoreML（复杂度高，收益不确定）

---

## 7. 实施计划（修正版）

| 步骤 | 任务 | 预期收益 | 风险 |
|---|---|---|---|
| 1 | 实现动态 max_length | 减少短句过度解码，可能缓解重复 | 低 |
| 2 | 实现重复 token 检测与截断 | 消除无标点短句重复问题 | 低 |
| 3 | 添加翻译 warmup | 消除首次 utterance 卡顿 | 低 |
| 4 | 添加高频短句缓存 | 对常见词秒回 | 低 |
| 5 | 在真实日/韩测试集上跑端到端延迟基准 | 量化实际改善 | 中 |
| 6 | 评估 ja→zh / ko→zh 直接 opus-mt 模型是否存在 | 若存在可消除 pivot 延迟 | 中 |
| 7 | 评估 CTranslate2 fp32 集成价值 | 额外 15–38% 加速 | 中 |
| 8 | 更新 README / CHANGELOG / ROADMAP | 文档同步 | 低 |

---

## 8. 待 PM 确认事项

1. **是否同意优先做"动态 max_length + 重复截断 + warmup + 缓存"这类低风险优化，而不是直接引入 CTranslate2？**
2. **是否接受我进一步调研 ja→zh / ko→zh 直接 opus-mt 模型的存在性？**（当前只有 en→zh 直接对）
3. **无标点短句重复问题是否纳入 v0.0.4 必修复项？** 这比延迟更影响体验。
4. **是否同意 CTranslate2 作为第二阶段优化，而非 v0.0.4 主路径？**

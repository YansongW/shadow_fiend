# m2m-100 Fine-tuning 实验方案 v0.0.5

## 目标

验证通过 fine-tune facebook/m2m-100-418M 获得低延迟、高质量 ja→zh / ko→zh / en→zh 直接翻译模型的可行性。

## 背景

- 当前 v0.0.4 使用 Helsinki-NLP/opus-mt 通过英文桥接翻译，延迟高、错误累积。
- m2m-100-418M 实测本地延迟：ja/zh ~146ms、ko/zh ~147ms、en/zh ~287ms，质量尚可但未专门优化中文方向。
- CCMatrix 提供大规模平行数据（ja-zh / ko-zh / en-zh），经清洗后可用于 fine-tuning。

## 实验假设

1. 在 CCMatrix 清洗数据上 fine-tune m2m-100-418M，可提升 ja→zh / ko→zh 的翻译质量。
2. 直接 fine-tune 后的 m2m-100-418M 延迟与基线相当（~140–300ms），不会显著增加。
3. fine-tune 后的模型可作为教师模型，蒸馏出 100M–200M 学生模型以进一步降低延迟。

## 实验设计

### 数据集

| 语言对 | 训练集 | 验证集 | 测试集 | 来源 |
|--------|--------|--------|--------|------|
| ja-zh  | 80k    | 10k    | 10k    | CCMatrix 清洗后 |
| ko-zh  | 80k    | 10k    | 10k    | CCMatrix 清洗后 |
| en-zh  | 80k    | 10k    | 10k    | CCMatrix 清洗后 |

- 使用 `scripts/data/download_and_clean_ccmatrix.py` 生成数据。
- 验证集/测试集从清洗后的数据中随机抽取，不参与训练。
- 训练时混合三个语言对，目标语言强制为简体中文（`zh_CN`）。

### 基线模型

- facebook/m2m-100-418M
- 使用 transformers 默认 generate 参数：num_beams=1, max_length=128

### Fine-tune 配置

```python
model = M2M100ForConditionalGeneration.from_pretrained("facebook/m2m-100-418M")
tokenizer = M2M100Tokenizer.from_pretrained("facebook/m2m-100-418M")

# 训练参数
batch_size = 8          # 单卡 A100 可尝试 16
learning_rate = 5e-5
num_epochs = 3
max_source_length = 128
max_target_length = 128
label_smoothing_factor = 0.1
fp16 = True
gradient_accumulation_steps = 4
```

- 每个样本设置 `forced_bos_token_id = tokenizer.lang_code_to_id["zh_CN"]`。
- 源语言通过 `tokenizer.src_lang` 指定。

### 评估指标

1. **质量**：
   - BLEU（sacrebleu）
   - chrF++
   - 人工抽查 50 句
2. **延迟**：
   - 本地 Apple Silicon 实测 mean / p50 / p95 / p99
   - 与基线 m2m-100-418M、opus-mt 桥接方案对比

### 实验步骤

1. 准备数据（`scripts/data/download_and_clean_ccmatrix.py`）
2. 拆分 train/valid/test
3. 编写 fine-tune 脚本（Hugging Face Trainer）
4. 在云 GPU（A100 40GB）上训练
5. 导出模型到本地
6. 本地延迟与质量评测
7. 对比基线，形成报告

## 预期产出

- fine-tuned 模型权重
- 训练日志与评估报告
- 延迟对比报告
- 蒸馏实验方案（如 fine-tune 成功）

## 风险与预案

| 风险 | 影响 | 预案 |
|------|------|------|
| CCMatrix 质量差 | BLEU 低 | 增加 LaBSE 语义过滤、补充 OpenSubtitles |
| 训练资源不足 | 无法完成 | 使用 Google Colab / Lambda / AutoDL A100 |
| 延迟未改善 | 目标未达成 | 直接进入蒸馏阶段，压缩模型 |
| 过拟合到网页文本 | 口语翻译差 | 增加字幕数据、术语表 fine-tuning |

## 后续路线

- 若 fine-tune 成功且质量提升明显 → 进入蒸馏小模型阶段
- 若 fine-tune 质量提升有限 → 分析数据问题，增强清洗与领域数据
- 若延迟仍不满足 → 蒸馏 + ONNX/CTranslate2 量化

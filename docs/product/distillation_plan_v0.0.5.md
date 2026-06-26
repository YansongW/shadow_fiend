# 蒸馏小模型实验方案 v0.5

## 目标

在 fine-tuned m2m-100-418M（教师）基础上，蒸馏出 100M–200M 参数的学生模型，用于 shadow_fiend 本地低延迟翻译。

## 背景

- m2m-100-418M 实测延迟 ja/zh ~146ms、ko/zh ~147ms、en/zh ~287ms。
- 目标延迟：ja/zh / ko/zh < 120ms，en/zh < 200ms（p95）。
- 直接用小模型（m2m-100-124M 不存在）不可行，需通过蒸馏构造。

## 蒸馏策略

### 方案 A：缩小 Transformer 维度（推荐）

- 教师：m2m-100-418M（d_model=1024, 12 layers, FFN 4096）
- 学生：6 层 encoder + 6 层 decoder，d_model=512，FFN 2048
- 参数量估算：~120M
- 训练目标：
  - 软标签交叉熵（教师 logits）
  - 真实标签交叉熵
  - 隐藏层 MSE（教师与学生同层对齐）
  - 注意力矩阵 KL 散度

### 方案 B：减少层数 + 共享参数

- 学生：6 层 encoder + 6 层 decoder，d_model=768，FFN 3072
- 参数量估算：~180M
- 共享 encoder/decoder embeddings 与部分 attention 参数
- 训练目标同方案 A

### 方案 C：序列级蒸馏（最小改动）

- 保持 m2m-100-418M 架构，但用教师生成的翻译作为 silver 数据继续训练
- 不减少参数量，只提升数据质量
- 延迟不变，只提升质量

## 推荐路线

优先执行方案 A（缩小维度），若质量损失过大则回退到方案 B，方案 C 作为数据增强辅助。

## 学生模型构造

```python
from transformers import M2M100Config

student_config = M2M100Config(
    vocab_size=128112,
    d_model=512,
    encoder_layers=6,
    decoder_layers=6,
    encoder_attention_heads=8,
    decoder_attention_heads=8,
    encoder_ffn_dim=2048,
    decoder_ffn_dim=2048,
    dropout=0.1,
    activation_function="relu",
    max_position_embeddings=1024,
)
```

- 嵌入层从教师初始化（截断或投影到 512 维）。
- 每 2 层教师对应 1 层学生（teacher layer 0,2,4,6,8,10 → student layer 0-5）。

## 训练目标

```
L = α * L_ce(soft, T=2) + β * L_ce(hard) + γ * L_mse(hidden) + δ * L_kl(attention)
```

建议初始权重：α=0.7, β=0.3, γ=0.1, δ=0.1

## 训练数据

- 使用与教师 fine-tune 相同的 CCMatrix 清洗数据
- 教师模型生成 soft targets（top-k logits 或 full logits）
- 数据量：每个语言对 100k–500k

## 评估

| 指标 | 教师 | 学生 A | 学生 B |
|------|------|--------|--------|
| BLEU (ja-zh) | ? | ? | ? |
| BLEU (ko-zh) | ? | ? | ? |
| BLEU (en-zh) | ? | ? | ? |
| 延迟 mean | 146ms | <120ms | <120ms |
| 参数量 | 418M | ~120M | ~180M |

## 实施步骤

1. 完成教师模型 fine-tune
2. 构造学生模型配置与初始化
3. 实现蒸馏训练循环
4. 在云 GPU 上训练
5. 导出与本地评测
6. 与教师模型对比，决定是否替换产品模型

## 风险

- 学生模型质量下降明显 → 增大模型、增加数据、调整蒸馏权重
- 训练不稳定 → 使用教师参数初始化、更小的学习率
- 延迟改善不达预期 → 结合 CTranslate2 / ONNX 量化

# shadow_fiend — AI 协作指南

本文件是 Kimi Code 等 AI 助手参与 shadow_fiend 项目时的核心上下文。
每次会话开始前必须先阅读本文件。

## 项目定位

- **名称**：shadow_fiend
- **定位**：开源、免费、本地优先的实时字幕翻译器，专注中日韩影视剧。
- **首要平台**：macOS Apple Silicon（MVE 阶段）。
- **核心原则**：简单、可维护、隐私优先、对非技术用户友好。

## 技术栈与决策

| 层级 | 选择 | 原因 |
|---|---|---|
| 语言 | Python 3.10+ | 生态成熟，AI/音频库丰富 |
| UI | PyQt6 + PyObjC | 跨平台潜力 + macOS 原生浮窗能力 |
| ASR | SenseVoice-Small | 中日韩强、比 Whisper 快 5-15 倍、本地可跑 |
| 翻译 | Argos Translate | 离线、轻量、中日韩可用 |
| 高级翻译 | 本地 LLM（可选） | Gemma / Qwen 小模型，复杂句使用 |
| 音频捕获 | BlackHole 2ch | macOS 系统音频 loopback 最稳定方案 |
| 包管理 | pip + requirements.txt | 保持简单，后续可迁移到 uv/poetry |

## 代码规范

1. **简单优先**：不要过度设计，MVE 阶段避免抽象工厂、插件系统。
2. **模块化**：每个模块有单一职责：
   - `audio/`：只负责获取原始音频
   - `asr/`：只负责语音转文字
   - `translation/`：只负责文本翻译
   - `ui/`：只负责显示
   - `pipeline.py`：负责串流程和错误恢复
3. **类型注解**：新代码尽量加类型提示。
4. **日志**：统一用 `logging`，模块名作为 logger name。
5. **错误处理**：I/O 和模型推理必须 try/except，不能因单帧错误导致整个 pipeline 崩溃。
6. **测试**：核心文本处理函数必须有单元测试。

## 协作流程

1. 每次会话前读取 `README.md`、`AGENTS.md`、`ROADMAP.md`、`CHANGELOG.md`。
2. 每次会话只聚焦 1-2 个 TODO 任务。
3. 所有代码改动必须可运行、有明确提交信息。
4. 每次会话结束时更新 `CHANGELOG.md` 和 TODO 列表。
5. 重大决策（换技术栈、改架构）先写入 `ROADMAP.md` 或 `AGENTS.md` 再执行。

## 禁止事项

- 不要引入不必要的依赖。
- 不要把 API key、凭据写入代码。
- 不要一次性重写多个模块。
- 不要假设用户已经会配 BlackHole/模型，安装脚本要自动化。

## 当前任务

见项目根目录 TODO 列表或 `ROADMAP.md`。

## 当前任务：v0.0.5 Fine-tuning

> 当前活跃分支：`v0.0.5-finetune`

本阶段目标：在清洗后的 v0.0.5 平行语料上微调 `facebook/m2m100_418M`，支持 ja↔zh、ko↔zh、en↔zh，并将模型发布到 Hugging Face。

### 已完成
- `main` 分支：CCMatrix small + large + OPUS 数据清洗，最终语料 `data/translation_corpus_final/`（586,187 对）。
- `v0.0.5-finetune` 分支：训练脚本、HF 上传脚本、一键训练发布脚本已就绪。
- Smoke test 通过：MPS 上可正常训练。

### 关键文件
- `docs/TASK_v0.0.5_FINETUNE.md` — 详细任务说明
- `scripts/training/finetune_m2m100_v0.0.5.py` — 训练脚本
- `scripts/training/upload_to_hf.py` — 模型上传脚本
- `scripts/training/train_and_publish.sh` — 训练 + 自动 push 代码 + 上传模型

### 在 Mac mini 上运行
```bash
git checkout v0.0.5-finetune
export HF_TOKEN=your_write_token
bash scripts/training/train_and_publish.sh
```

### 注意事项
- `data/` 目录被 gitignore，需要在 Mac mini 上本地准备或重新跑数据 pipeline。
- 训练前确认 `.venv` 已安装依赖：`pip install -r requirements.txt`
- 若 Kimi Code 重启后看到本文件，优先完成 `docs/TASK_v0.0.5_FINETUNE.md` 中的训练与发布任务。

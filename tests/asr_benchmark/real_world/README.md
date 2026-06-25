# 真实影视片段 ASR 测试集

## 用途

用于最终验证 ASR 在真实观影场景下的准确率。区别于合成音频，真实片段包含：

- 背景音乐
- 多人对话
- 情绪变化
- 真实语速和口音

## 目录结构

```
real_world/
├── ja/
│   ├── audio/          # 5–10 秒 WAV/AIFF 音频片段
│   └── metadata.json   # 片段元数据与人工标注
└── ko/
    ├── audio/
    └── metadata.json
```

## 采集要求

1. **来源**：您自己拥有的正版影视剧，仅用于本地测试，不外传。
2. **格式**：mono，16-bit PCM，16 kHz（或脚本自动重采样）。
3. **长度**：每段 5–10 秒，包含一句完整台词。
4. **标注**：每段需要人工写出实际台词原文。
5. **数量**：每个语言 ≥10 段，建议覆盖：
   - 单人独白
   - 双人对话
   - 带背景音乐的片段
   - 较快语速的片段

## metadata.json 格式

```json
{
  "language": "ja",
  "description": "Japanese drama clips",
  "clips": [
    {
      "file": "audio/clip_001.wav",
      "transcript": "ここは私が引き受けます",
      "source": "Sample Drama S01E03",
      "scene": " heroine 决心承担任务",
      "duration_sec": 7.2
    }
  ]
}
```

## 如何添加片段

1. 将音频文件放入 `audio/` 目录
2. 在 `metadata.json` 中添加对应条目
3. 运行 ASR benchmark 脚本时会自动加载

# Shadow Fiend MVE 技术设计文档

## 1. 目标

在 macOS Apple Silicon 上实现：
1. 捕获播放器系统音频（通过 BlackHole 虚拟声卡）。
2. 实时语音识别（SenseVoice-Small）。
3. 本地翻译（Argos Translate）。
4. 半透明浮窗显示双语字幕（PyQt6）。

## 2. 数据流

```
┌─────────────────────────────────────────────────────────────┐
│ 播放器声音                                                   │
└──────────────┬──────────────────────────────────────────────┘
               │ macOS Multi-Output Device
               ▼
┌─────────────────────────────────────────────────────────────┐
│ BlackHole 2ch（虚拟输入设备）                                 │
└──────────────┬──────────────────────────────────────────────┘
               │ 16kHz, 16-bit, mono PCM
               ▼
┌─────────────────────────────────────────────────────────────┐
│ AudioCaptureModule                                           │
│ - 用 PyAudio 读取 BlackHole 输入流                            │
│ - 输出固定长度 audio chunk（如 0.5s / 1024 samples）           │
└──────────────┬──────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────┐
│ VADModule                                                    │
│ - 基于 Silero VAD 检测语音活动                                │
│ - 在说话停顿处切出完整 utterance                              │
│ - 过滤静音和背景音乐                                          │
└──────────────┬──────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────┐
│ ASRModule (SenseVoice-Small)                                 │
│ - 把 utterance 音频转成文字                                   │
│ - 返回：原文文本 + 检测到的语言                                │
└──────────────┬──────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────┐
│ TranslationModule (Argos Translate)                          │
│ - 把原文翻译成目标语言                                        │
│ - 返回：译文文本                                              │
└──────────────┬──────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────┐
│ UIModule (PyQt6 浮窗)                                        │
│ - 显示原文 + 译文                                             │
│ - 支持置顶、透明、拖拽                                        │
└──────────────────────────────────────────────────────────────┘
```

## 3. 模块接口

### 3.1 AudioCaptureModule

```python
class AudioCaptureModule:
    def __init__(self, device_name: str = "BlackHole 2ch", sample_rate: int = 16000):
        ...

    def start(self) -> None:
        """启动音频流。"""

    def read_chunk(self, duration_ms: int = 500) -> np.ndarray:
        """读取指定时长的音频数据，返回 float32 数组。"""

    def stop(self) -> None:
        """停止音频流。"""
```

### 3.2 VADModule

```python
class VADModule:
    def __init__(self, sample_rate: int = 16000):
        ...

    def add_audio(self, chunk: np.ndarray) -> list[np.ndarray]:
        """
        持续输入音频，当检测到完整 utterance 时返回一个或多个音频段。
        没有完整段时返回空列表。
        """

    def reset(self) -> None:
        """清空缓存。"""
```

### 3.3 ASRModule

```python
class ASRModule:
    def __init__(self, model_name: str = "iic/SenseVoiceSmall", device: str = "auto"):
        ...

    def transcribe(self, audio: np.ndarray) -> dict:
        """
        返回：
        {
            "text": "识别出的文字",
            "language": "ja|ko|zh|en|...",
        }
        """
```

### 3.4 TranslationModule

```python
class TranslationModule:
    def __init__(self, source_lang: str, target_lang: str):
        ...

    def translate(self, text: str) -> str:
        """翻译文本。"""
```

### 3.5 UIModule

```python
class SubtitleWindow:
    def __init__(self):
        ...

    def show_text(self, source: str, translated: str) -> None:
        """更新字幕内容。"""

    def run(self) -> None:
        """启动 Qt 事件循环。"""
```

## 4. 线程模型

MVE 阶段采用**单生产者-单消费者队列**模型：

- **音频线程**：持续从 BlackHole 读取 chunk，推入 `audio_queue`。
- **处理线程**：从 `audio_queue` 取数据，经过 VAD → ASR → 翻译，把结果推入 `subtitle_queue`。
- **UI 线程**：主线程运行 Qt 事件循环，从 `subtitle_queue` 取结果更新浮窗。

```python
audio_queue: Queue[np.ndarray]
subtitle_queue: Queue[Tuple[str, str]]
```

## 5. 关键设计决策

### 5.1 为什么用 BlackHole 而不是 ScreenCaptureKit？

- BlackHole 是 macOS 上最稳定的系统音频 loopback 方案。
- ScreenCaptureKit 需要用户授权"屏幕录制"，且音频 API 较新、兼容性差。
- 后续可以加入 ScreenCaptureKit 作为可选方案。

### 5.2 为什么用 SenseVoice 而不是 Whisper？

- SenseVoice-Small 对中文、日语、韩语识别更强。
- 非自回归架构，推理速度比 Whisper 快 5-15 倍。
- 模型更小，更适合 Apple Silicon 的 unified memory。

### 5.3 为什么用 Argos 而不是本地 LLM 作为主要翻译？

- Argos 翻译延迟低（200-500ms），适合实时字幕。
- LLM 质量好但慢（2-4s），作为 MVE 2 的可选高级模式。

### 5.4 VAD 切句策略

- 使用 Silero VAD 检测语音帧。
- 当连续静音超过 300ms 时，认为一个 utterance 结束。
- 最大 utterance 长度 10 秒，超过则强制切分。

## 6. 错误处理

- 音频设备未找到：提示用户检查 BlackHole 安装和 Multi-Output Device 配置。
- ASR 失败：记录日志，跳过该段，不阻塞 pipeline。
- 翻译失败：显示原文，标记翻译失败。
- UI 异常：用 try/except 包裹，避免浮窗崩溃导致整个程序退出。

## 7. 配置

MVE 阶段配置通过命令行参数：

```bash
./scripts/run.sh --source ja --target zh
```

后续再引入 config 文件。

## 8. 验证标准

1. 播放一段日语/韩语/英语视频。
2. 屏幕出现半透明浮窗。
3. 浮窗内显示原文和中文译文。
4. 延迟在 1-3 秒内可接受。

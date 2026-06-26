# v0.0.5 平行数据策略报告

**日期**：2026-06-26  
**汇报人**：DEV  

---

## 1. 目标

为 fine-tune / 蒸馏 shadow_fiend 专用翻译模型，整理高质量的 ja↔zh / ko↔zh / en↔zh 平行语料。

重点需求：
- **影视字幕/口语对话领域**：贴近观影场景
- **短句为主**：匹配 ASR 输出的 utterance 长度
- **简中优先**：目标语言为简体中文
- **可清洗过滤**：原始数据允许有噪音，但需有效过滤

---

## 2. 候选数据源

### 2.1 CCMatrix（推荐，网页 mined）

- **来源**：CommonCrawl 网页挖掘的平行句对
- **语言对**：ja-zh、ko-zh、en-zh 等（ja-zho / ko-zho 不可用）
- **实际清洗结果**（每语言对目标 10 万条）：
  - ja-zh：100,000 对（seen 124,557，duplicates 3,521）
  - ko-zh：100,000 对（seen 128,903，duplicates 2,987）
  - en-zh：94,006 对（网络流读取提前停止）
  - 平均句长：ja 33.3 / ko 37.1 / en 63.1 字符；zh 约 26–28 字符
- **优点**：
  - 数据量巨大
  - 覆盖多种领域
  - Hugging Face 上可直接通过 streaming 加载
- **缺点**：
  - 噪音大，很多低质量对齐
  - 网页文本与影视字幕领域有差距
  - 包含大量繁体中文
  - 采样中可见宗教文本、网页模板、特殊符号等噪音

### 2.2 OpenSubtitles（影视字幕，理想但难获取）

- **来源**：OpenSubtitles.org 的电影/电视剧字幕
- **语言对**：en-zh 较常见，ja-zh / ko-zh 可能较少
- **优点**：
  - 最接近观影场景
  - 口语化、短句多
- **缺点**：
  - 中日/中韩对齐数据稀缺
  - 需要处理时间轴、多说话人
  - 版权问题需注意

### 2.3 JParaCrawl / Korean Parallel Corpora

- **来源**：日英、韩英平行语料
- **优点**：数据量大、质量较高
- **缺点**：
  - **不能直接用于 ja→zh / ko→zh**
  - 只能作为辅助数据或用于 pivot 增强

### 2.4 WikiMatrix / TED2020 / MultiUN

- **来源**：维基百科、TED 演讲、联合国文件
- **优点**：质量相对较高
- **缺点**：
  - 领域偏正式，与影视字幕差距大
  - 可作为混合训练数据的一部分

### 2.5 自建影视字幕数据

- **来源**：
  - 公开授权的影视作品字幕
  - 动漫/日剧/韩剧 fan subtitles
  - 自行翻译的小规模语料
- **优点**：
  - 最贴合目标场景
  - 可控制质量
- **缺点**：
  - 获取和版权成本高
  - 数据量小

---

## 3. 获取方式

### 3.1 CCMatrix via Hugging Face

```python
from datasets import load_dataset

# 通过 hf-mirror 加速
# HF_ENDPOINT=https://hf-mirror.com python script.py

ds = load_dataset(
    "yhavinga/ccmatrix",
    "ja-zh",
    streaming=True,
    split="train",
    trust_remote_code=True,
)
```

### 3.2 OPUS 直接下载

```bash
# 示例：OpenSubtitles en-zh（如存在）
curl -L -o en-zh.txt.zip \
  "https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2018/moses/en-zh.txt.zip"
```

### 3.3 本地字幕文件处理

```bash
# 未来可扩展：处理 .srt 字幕文件
python scripts/data/parse_srt.py --input subtitles/ --output corpus.tsv
```

---

## 4. 数据清洗流程

1. **基础过滤**
   - 去除空句
   - 去除过长句子（>200 字符）
   - 去除过短句子（<3 字符）
   - 去除明显不平衡的句对（长度比 >3 或 <0.3）

2. **繁体转简体**
   - 使用 `zhconv` 或 `opencc`
   - 目标语言统一为简体中文

3. **去重**
   - 基于 source + target 文本去重
   - 可使用 minhash/LSH 处理大规模数据

4. **质量过滤**
   - 语言识别：确保源/目标语言正确
   - 语义相似度：使用 LaBSE 等模型过滤低质量对齐
   - 规则过滤：去除包含过多标点/数字/特殊符号的句对

5. **领域过滤**
   - 优先保留短句、口语化表达
   - 可训练一个简单分类器筛选影视字幕风格句对

---

## 5. 训练数据配比建议

| 数据源 | 目标占比 | 用途 |
|---|---|---|
| CCMatrix ja-zh | 40% | 主训练数据 |
| CCMatrix ko-zh | 25% | 主训练数据 |
| CCMatrix en-zh | 15% | 保持 en→zh 能力 |
| OpenSubtitles（如可获取） | 15% | 影视领域适配 |
| 自建/清洗后的字幕数据 | 5% | 高质量 fine-tuning |

---

## 6. 数据规模目标

| 阶段 | 句对数 | 用途 |
|---|---|---|
| 小规模实验 | 10–50 万 | 验证 fine-tuning 是否有效 |
| 中规模训练 | 50–200 万 | 达到可用质量 |
| 大规模训练 | 200 万+ | 接近商业水平 |

---

## 7. 下一步行动

1. **完成 CCMatrix 数据探索**：统计 ja-zh / ko-zh / en-zh 的实际规模和质量
2. **实现数据下载脚本**：支持 streaming 下载和本地缓存
3. **实现数据清洗脚本**：繁体转简体、过滤、去重
4. **小规模 fine-tuning 实验**：用 10–50 万句对验证效果
5. **根据实验结果决定是否扩大数据规模和蒸馏**

---

## 8. 待 PM 确认

1. **是否同意以 CCMatrix 为主要数据源，OpenSubtitles 为辅？**
2. **是否接受数据清洗后仍有一定噪音？**（完全干净的平行语料很难获取）
3. **是否先投入 2–4 周做数据整理和小规模 fine-tuning 实验？**

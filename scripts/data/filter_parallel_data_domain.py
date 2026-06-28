#!/usr/bin/env python3
"""
领域/宗教/低质文本过滤。

输入为 LaBSE 过滤后的 TSV（source\ttarget），输出进一步去除宗教、网页导航、
HTML/URL、广告、成人、垃圾重复等低质平行句对。

用法：
    python scripts/data/filter_parallel_data_domain.py \
        --input data/translation_corpus_v0.0.5/ja-zh.labse.tsv \
        --output data/translation_corpus_v0.0.5/ja-zh.domain.tsv \
        --pair ja-zh
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tqdm import tqdm


PAIR_SRC_LANG = {
    "ja-zh": "ja",
    "ko-zh": "ko",
    "en-zh": "en",
}


# --------------------------------------------------------------------------- #
# 多语言宗教/教义敏感词黑名单（精确匹配子串）
# --------------------------------------------------------------------------- #
RELIGION_KEYWORDS = [
    # 中文 - 宗教名称与核心术语
    "基督教", "天主教", "新教", "东正教", "耶稣", "基督", "耶和华", "上帝",
    "圣经", "福音", "洗礼", "圣餐", "教会", "教堂", "牧师", "神父", "修女",
    "佛教", "佛陀", "释迦牟尼", "阿弥陀佛", "菩萨", "观音菩萨", "地藏王",
    "金刚经", "心经", "法华经", "楞严经", "华严经", "净土宗", "禅宗", "密宗",
    "伊斯兰教", "穆斯林", "真主", "安拉", "古兰经", "可兰经", "清真寺", "阿訇",
    "犹太教", "犹太", "摩西", "塔木德", "旧约",
    "印度教", "婆罗门", "毗湿奴", "湿婆", "梵天",
    "神道教", "神社", "天照大神",
    "道教", "老子", "庄子", "道德经", "玉皇大帝",
    "喇嘛", "藏传佛教", "达赖", "班禅",
    "圣经章节", "旧约圣经", "新约圣经", "诗篇", "箴言",
    "祷告", "祈祷", "阿门", "弥撒", "布道", "讲道", "受难", "复活节", "圣诞节",
    "菩萨保佑", "阿弥陀佛", "佛祖", "观世音",
    # 中文 - 宗教人物与伊斯兰经典语境
    "穆萨", "穆罕默德", "马赫迪", "法老", "以色列人", "迦南",
    "至仁的", "至慈的", "至宥的", "全能的", "天经", "信道者", "不信道者",
    "不信者", "隐微的事物", "痛苦的刑罚", "痛罪的刑罚", "严厉的刑罚",
    "以物配主", "族中的使者", "他们族中", "一个使者", "确已来临",
    "赏赐你", "使他们从云中", "从云中降下", "天地万物", "天和地",
    "天地的创造者", "创造天地", "神创造", "虔诚", "敬虔", "圣神", "圣灵",
    "创世记", "以色列的安慰", "崇正地", "专向", "隐讳", "私欲",
    "信士们啊", "不要追随恶魔", "恶魔的步伐", "幽玄", "赏赐经典",
    "亏折者", "后世", "今世", "不然你们却", "其实后世", "全体归顺",
    "乐园", "火狱", "善功", "多神教徒", "以物配主者", "你说", "他们否认",
    "确是全聪的", "确是全知的", "痛罪的刑罚", "严厉的刑罚", "刑罚",
    "畏惧主", "信道而且行善", "完全的报酬", "重大的报酬", "赦宥",
    "创造人类", "崇拜我", "毁灭了其余", "信道", "行善", "伟大的牺牲",
    "赎了他", "礼拜", "骑乘着", "光明之子", "刀剑临到你们",
    "亚伯拉罕", "在那日", "山岳消逝", "猶予", "缓刑",
    "先知", "崇拜", "创造我", "引导我的", "天怎样高过地",
    "撒旦", "satan", "satan's", "撒但", "神的", "神绝望", "deny it",
    "i said in my haste", "all men are liars", "from the east and the west",
    "i say to you", "i give you", "many will come", "the town that was by the sea",
    "psalm", "proverbs", "ecclesiastes", "isaiah", "jeremiah", "matthew", "mark", "luke", "john",
    "咒诅", "祝福", "恩典", "加添他的力量", "天使从天上",
    # English
    "christianity", "christian", "jesus", "christ", "god", "lord", "bible",
    "gospel", "baptism", "church", "pastor", "priest", "nun", "catholic",
    "protestant", "orthodox", "amen", "mass", "sermon", "easter", "christmas",
    "buddhism", "buddhist", "buddha", "amitabha", "avalokitesvara", "sutra",
    "islam", "muslim", "allah", "quran", "koran", "mosque", "imam",
    "judaism", "jewish", "moses", "talmud",
    "hinduism", "hindu", "brahman", "vishnu", "shiva",
    "shinto", "shrine",
    "taoism", "taoist", "laozi",
    "lama", "tibetan buddhism",
    "muhammad", "moses", "pharaoh", "israelites", "canaan",
    "apostle", "messenger", "denied", "revelation", "heavens and earth",
    "creation of the heavens", "pious", "holy spirit", "genesis", "israel",
    "lord of the worlds", "disbelievers", "believers", "hereafter",
    # 日文
    "キリスト教", "キリスト", "イエス", "聖書", "福音", "洗礼", "教会", "牧師",
    "神父", "修女", "カトリック", "プロテスタント", "正教", "アーメン", "ミサ",
    "説教", "復活祭", "クリスマス",
    "仏教", "仏陀", "釈迦", "阿弥陀", "観音", "菩薩", "経典", "お経",
    "イスラム教", "ムスリム", "アッラー", "コーラン", "モスク", "イマーム",
    "神道", "神社",
    "ムーサー", "ムハンマド", "マホメット", "フィラオ", "イスラエル人", "カナン",
    "イスラエル", "創世記",
    "至仁", "至慈", "天経", "信者", "不信者", "懲罰", "刑罰",
    "使徒", "遣わされた", "拒否", "隠していた", "明らか", "創造", "万物",
    "敬虔", "聖神", "神が", "主よ", "しもべ", "御名", "御心", "天と地",
    "信仰する者たちよ", "悪魔の歩み", "来世", "現世", "啓典", "失敗者",
    "嘘付き", "耳を選す", "幽玄界",
    "主を畏れる", "信仰して", "善い行い", "報奨", "恩恵", "贖い", "礼拝",
    "創った", "仕えさせる", "滅ぼした", "光の子", "剣を恐れる",
    "アブラハム", "その日", "山々を移させる", "猶予",
    "預言者", "崇拝", "創られた方", "導かれ", "天が地より高い",
    "サタン", "神の", "神に背く",
    "詩篇", "箴言", "伝道書", "イザヤ書", "エレミヤ書", "マタイ福音書", "マルコ福音書", "ルカ福音書", "ヨハネ福音書",
    "呪い", "祝福", "恵み", "力を与えた", "天からの使い",
    # 韩文
    "기독교", "그리스도", "예수", "성경", "복음", "세례", "교회", "목사",
    "신부", "수녀", "가톨릭", "프로테스탄트", "정교회", "아멘", "미사", "설교",
    "부활절", "크리스마스",
    "불교", "부처", "석가", "아미타불", "관음", "보살", "경전", "염불",
    "이슬람교", "무슬림", "알라", "코란", "모스크", "이맘",
    "신토", "신사",
    "모세", "무함마드", "모하메드", "파라오", "이스라엘", "칸나안",
    "지은자", "자비로우신", "천경", "불신자", "형벌",
    "사도", "선지자", "부인", "계시", "창조", "만물", "경건", "성신",
    "창세기", "하늘과 땅",
    "믿는 사람들이여", "악마의 발", "내세", "현세", "경전", "실패자",
    "거짓말쟁이", "선을", "귀를 기울이다",
    "주를 두려워", "믿음과", "선행", "보상", "은혜", "속량", "예배",
    "창조하셨으니", "섬기게", "멸망시켰다", "빛의 자녀", "칼을 두려워",
    "아브라함", "그날", "산들을 옮기리라", "유예",
    "선지자", "숭배", "창조하신 분", "인도하시는", "하늘이 땅보다 높음같이",
    "사탄", "하나님의", "하나님을 부인",
    "시편", "잠언", "전도서", "이사야", "예레미야", "마태복음", "마가복음", "누가복음", "요한복음",
    "저주", "축복", "은혜", "힘을 더하다", "하늘에서 천사",
]

# 需要整词匹配的高危词（避免误伤普通词汇）
RELIGION_REGEX_PATTERNS = [
    re.compile(r"\b(church|churches|christian|christians|bible|bibles|jesus|christ)\b", re.I),
    re.compile(r"\b(gospel|gospels|mosque|mosques|quran|koran|muslim|muslims)\b", re.I),
    re.compile(r"\b(buddha|buddhas|buddhist|buddhists|buddhism)\b", re.I),
]

# --------------------------------------------------------------------------- #
# 成人/低俗/攻击性内容
# --------------------------------------------------------------------------- #
ADULT_KEYWORDS = [
    # 英文
    "fuck", "fucking", "fuckable", "shit", "bitch", "damn", "asshole",
    "porn", "porno", "sex", "sexual", "nude", "naked", "dick", "cock",
    # 中文
    "他妈的", "草泥马", "傻逼", "婊子", "色情", "裸体", "性交", "做爱",
    # 日文
    "ファック", "セックス", "ポルノ", "裸", "死ね", "バカ", "アホ",
    # 韩文
    "씨발", "섹스", "포른", "누드", "졸라", "미친",
]

ADULT_REGEX_PATTERNS = [
    re.compile(r"\b(fuck|fucks|fucking|fucked|sex|porn|nude|naked)\b", re.I),
]

# --------------------------------------------------------------------------- #
# 网页/导航/低质文本特征
# --------------------------------------------------------------------------- #
WEB_NAV_KEYWORDS = [
    # 中文/英文网页导航
    "首页", "上一页", "下一页", "末页", "返回", "点击进入", "查看更多", "阅读全文",
    "关于我们", "联系我们", "免责声明", "隐私政策", "用户协议", "网站地图",
    "copyright", "all rights reserved", "privacy policy", "terms of service",
    "terms of use", "site map", "home page", "about us", "contact us", "login",
    "sign in", "sign up", "register", "logout", "cart", "shopping cart",
    # 日文
    "ホーム", "トップページ", "前のページ", "次のページ", "お問い合わせ",
    "利用規約", "プライバシーポリシー", "サイトマップ",
    # 韩文
    "홈", "첫 페이지", "이전 페이지", "다음 페이지", "문의하기", "이용약관",
    "개인정보처리방침", "사이트맵",
]

# HTML / URL / 标记
HTML_URL_PATTERNS = [
    re.compile(r"<[^>]+>"),                  # HTML 标签
    re.compile(r"https?://\S+"),             # URL
    re.compile(r"www\.\S+"),                 # www 链接
    re.compile(r"\{\{.*?\}\}"),              # 模板变量
    re.compile(r"\[.*?\]\(.*?\)"),           # markdown 链接
]

# --------------------------------------------------------------------------- #
# 重复/垃圾模式
# --------------------------------------------------------------------------- #
REPEAT_PATTERN = re.compile(r"(.)\1{6,}")   # 同一字符重复 7 次以上
EXCLAM_REPEAT = re.compile(r"[!！?？]{4,}")  # 连续 4 个以上 !/?
DIGIT_ONLY = re.compile(r"^\d+$")
# 论坛/社交媒体时间戳模式（韩/日/英常见）
FORUM_TIMESTAMP = re.compile(
    r"(\d{4}년\s+\d{1,2}월\s+\d{1,2}일\s+(오전|오후)\s+\d{1,2}시\s+\d{2}분)|"
    r"(\d{4}年\s*\d{1,2}月\s*\d{1,2}日\s*(午前|午後)\s*\d{1,2}時\s*\d{2}分)|"
    r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pair", required=True, choices=list(PAIR_SRC_LANG.keys()))
    parser.add_argument("--min-chars", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=500)
    parser.add_argument("--max-ratio", type=float, default=3.0,
                        help="源/目标长度比上限（字符数）")
    parser.add_argument("--min-ratio", type=float, default=0.2,
                        help="源/目标长度比下限（字符数）")
    return parser.parse_args()


def load_pairs(path: Path):
    pairs = []
    with open(path, "r", encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            pairs.append((parts[0], parts[1]))
    return pairs


def has_religion_keyword(src: str, tgt: str) -> bool:
    combined = (src + " " + tgt).lower()
    for kw in RELIGION_KEYWORDS:
        if kw in combined:
            return True
    for pat in RELIGION_REGEX_PATTERNS:
        if pat.search(combined):
            return True
    return False


def has_web_nav(src: str, tgt: str) -> bool:
    combined = (src + " " + tgt).lower()
    for kw in WEB_NAV_KEYWORDS:
        if kw in combined:
            return True
    for pat in HTML_URL_PATTERNS:
        if pat.search(src) or pat.search(tgt):
            return True
    return False


def has_adult_content(src: str, tgt: str) -> bool:
    combined = (src + " " + tgt).lower()
    for kw in ADULT_KEYWORDS:
        if kw in combined:
            return True
    for pat in ADULT_REGEX_PATTERNS:
        if pat.search(combined):
            return True
    return False


def latin_ratio(text: str) -> float:
    """拉丁字母（a-zA-Z）占非空白字符的比例。"""
    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return 0.0
    latin = sum(1 for c in non_space if "A" <= c <= "Z" or "a" <= c <= "z")
    return latin / len(non_space)


def is_low_quality(src: str, tgt: str, args) -> bool:
    # 长度过滤
    for text in (src, tgt):
        if len(text) < args.min_chars or len(text) > args.max_chars:
            return True
        if REPEAT_PATTERN.search(text):
            return True
        if EXCLAM_REPEAT.search(text):
            return True
        if DIGIT_ONLY.match(text):
            return True
        if FORUM_TIMESTAMP.search(text):
            return True

    # 长度比例过滤
    ratio = len(src) / (len(tgt) + 1e-6)
    if ratio > args.max_ratio or ratio < args.min_ratio:
        return True

    return False


def is_language_mixed(src: str, tgt: str, src_lang: str) -> bool:
    """
    检测源/目标语言是否被非目标语言严重污染。
    主要针对韩/日语料中混有大量英文的垃圾句对。
    """
    if src_lang in ("ja", "ko"):
        # 源句拉丁字母占比过高，说明不是纯正日/韩文
        if latin_ratio(src) > 0.5:
            return True
    elif src_lang == "en":
        # 英文源句中非拉丁字母占比过高
        if latin_ratio(src) < 0.3 and len(src) >= 10:
            return True

    # 目标句应当是中文，若拉丁字母占比过高则可能是未翻译或混用语言
    if latin_ratio(tgt) > 0.6:
        return True

    return False


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    src_lang = PAIR_SRC_LANG[args.pair]

    pairs = load_pairs(input_path)
    print(f"Loaded {len(pairs)} pairs from {input_path}")

    kept = 0
    duplicates = 0
    removed_reasons = {"religion": 0, "web_nav": 0, "adult": 0, "low_quality": 0, "lang_mix": 0}
    seen: set[tuple[str, str]] = set()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\n")
        for src, tgt in tqdm(pairs, desc="Domain filtering"):
            key = (src.strip(), tgt.strip())
            if key in seen:
                duplicates += 1
                continue

            if has_religion_keyword(src, tgt):
                removed_reasons["religion"] += 1
                continue
            if has_web_nav(src, tgt):
                removed_reasons["web_nav"] += 1
                continue
            if has_adult_content(src, tgt):
                removed_reasons["adult"] += 1
                continue
            if is_language_mixed(src, tgt, src_lang):
                removed_reasons["lang_mix"] += 1
                continue
            if is_low_quality(src, tgt, args):
                removed_reasons["low_quality"] += 1
                continue

            seen.add(key)
            f.write(f"{src}\t{tgt}\n")
            kept += 1

    stats = {
        "input": str(input_path),
        "output": str(output_path),
        "pair": args.pair,
        "total": len(pairs),
        "kept": kept,
        "duplicates": duplicates,
        "removed": len(pairs) - kept - duplicates,
        "retention_rate": round(kept / len(pairs), 4),
        "removed_reasons": removed_reasons,
    }
    stats_path = output_path.with_suffix(output_path.suffix + ".stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\nKept {kept}/{len(pairs)} pairs ({stats['retention_rate']*100:.1f}%)")
    print(f"Removed reasons: {removed_reasons}")
    print(f"Stats saved to {stats_path}")


if __name__ == "__main__":
    main()

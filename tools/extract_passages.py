# -*- coding: utf-8 -*-
"""
从 pdf_txt 提取押题库 51 篇 + 补充版 24 篇，生成 data/passages.json

用法：
    python tools/extract_passages.py

输出：data/passages.json  结构见 README.md
"""
import re, json, os, sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(BASE), 'pdf_txt')

NOISE = [
    r'^===== PAGE \d+ =====$',
    r'^\s*$',
]

def clean_line(s):
    s = s.strip()
    if not s:
        return ''
    if re.match(r'^===== PAGE \d+ =====$', s):
        return ''
    # 页眉页脚
    if re.match(r'^撷墨教育', s) or re.match(r'^墨盒自考', s):
        return ''
    if re.match(r'^\d+\s*/\s*\d+\s*$', s):
        return ''
    if '2604 考期必背短文' in s:
        return ''
    if re.match(r'^微信公众号', s):
        return ''
    if re.match(r'^高等教育自学考试\s*英语二', s):
        return ''
    # 补充版页眉：Unit 4B / Unit 12A
    if re.match(r'^Unit\s*\d{1,2}\s*[AB]\s*$', s):
        return ''
    if re.match(r'^[\d\s]{1,10}$', s):          # 孤立题号/页码
        return ''
    s = re.sub(r'微信公众号【[^】]*】', '', s)
    return s.strip()


def is_zh(line):
    """中文字符占比 > 28% 视为中文行"""
    zh = len(re.findall(r'[\u4e00-\u9fff]', line))
    if zh == 0:
        return False
    total = len(re.findall(r'[\u4e00-\u9fffA-Za-z]', line))
    return total and zh / total > 0.28


def split_en_zh(lines):
    """把行列表分成英文段落与中文段落。

    规则：真正的空行 = 段落分隔；被过滤的噪音行（页眉页脚/PAGE 标记）直接跳过，
    不打断段落。同语言的连续行合并为一个段落。
    """
    en, zh = [], []
    cur_en, cur_zh = [], []

    def flush():
        if cur_en:
            en.append(re.sub(r'\s+', ' ', ' '.join(cur_en)).strip())
            cur_en.clear()
        if cur_zh:
            zh.append(''.join(cur_zh).strip())
            cur_zh.clear()

    for raw in lines:
        stripped = raw.strip()
        if not stripped:          # 真空行 → 段落分隔
            flush()
            continue
        s = clean_line(raw)
        if not s:                 # 噪音行 → 跳过，不分隔
            continue
        if is_zh(s):
            if cur_en:
                flush()
            cur_zh.append(s)
        else:
            if cur_zh:
                flush()
            cur_en.append(s)
    flush()
    return [p for p in en if len(p) > 1], [p for p in zh if len(p) > 3]


def join_en(parts):
    """英文段落清洗：去掉练习题，并把 PDF 断行造成的碎片段落合并回去"""
    out = []
    for p in parts:
        p = re.sub(r'\s+', ' ', p).strip()
        if len(p) < 2:
            continue
        # 段首混入的题号（1-2 位数字 + 空格，如 "21 like sunrise"）
        p = re.sub(r'^\d{1,2}\s+(?=[A-Za-z])', '', p)
        # 正文里插入的题号标记，如 "... a little time off. (3)I needed to ..."
        p = re.sub(r'[（(]\s*\d{1,2}\s*[)）]\s*(?=[A-Z])', '', p)
        p = re.sub(r'\s{2,}', ' ', p).strip()
        if len(p) < 2:
            continue
        # 过滤练习题残留
        if re.match(r'^（\s*[）]?\s*\d+', p):          # （ ）3. / （3.
            continue
        if re.match(r'^\d+\s*[.、]', p):               # 1.Reading...
            continue
        if re.match(r'^\s*[A-D]\s*[.、]\s', p):        # A. xxx
            continue
        if re.match(r'^Unit\s*\d{1,2}\s*[AB]\s*$', p):  # 页眉残留
            continue
        if re.match(r'^[\d\s]{1,10}$', p):
            continue
        # 答案解析从这里开始 → 截断；截断后过短则丢弃
        cut = re.split(r'【>?答案解析】', p)[0].strip()
        if len(cut) >= 30:
            p = cut
        elif '答案解析' in p:
            continue
        if '【正确答案】' in p:
            continue
        if re.match(r'^Directions:', p) or re.match(r'^说明[:：]', p):
            continue
        # PDF 断行/空行误切：前段不以句末标点收尾，或本段小写开头（英文段落不会
        # 以小写起头，如 Y22 "...(outings, video games, etc.)" + "and the third..."）
        # → 与上一段合并；前段以冒号结尾（对话/列举引导）除外
        if out and (not re.search(r'[.!?]["\']?$', out[-1])
                    or (p[:1].islower() and not out[-1].endswith(':'))):
            out[-1] = out[-1] + ' ' + p
            continue
        out.append(p)
    return out


def join_zh(parts):
    """中文段落清洗。

    注意：译文里常嵌有英文（如 "I get a kick out of"、"Ask Jeeves"、"他 kick 球"），
    不能用 re.sub(r'\\s+','') 无差别删空格——否则英文短语变成 "Igetakickoutof"。
    只删除「中文↔中文标点」之间的空白（PDF 断行残留），英文单词间的空格全部保留。
    """
    out = []
    for p in parts:
        p = re.sub(r'\s+', ' ', p).strip()
        # 中文（含中文标点）之间的空白 → 删除；其余空格保留
        prev = None
        zhch = r'[\u4e00-\u9fff，。！？；：、（）\u201c\u201d\u2018\u2019《》…—]'
        while prev != p:
            prev = p
            p = re.sub('(?<=%s)\\s+(?=%s)' % (zhch, zhch), '', p)
        if len(p) < 4:
            continue
        # 段首混入的真题来源标注，如 "源、2021年10月填词补文来源)"
        p = re.sub(r'^\D{0,8}?\d{4}年\d{1,2}月[\u4e00-\u9fff]{2,12}来源\)?[、，,）)]?\s*', '', p)
        # 段首混入的题号
        p = re.sub(r'^\d{1,2}[、，]\s*', '', p)
        if len(p) < 4:
            continue
        if re.match(r'^\d+\s*[.、]', p):
            continue
        if re.match(r'^Unit\s*\d{1,2}\s*[AB]\s*$', p):
            continue
        if '【正确答案】' in p or '【答案解析】' in p:
            continue
        # 中文断行拼接：中↔中直接连，中英/英中/英英交界补一个空格（保留英文单词间隔）
        if out and not re.search(r'[。！？）”"]$', out[-1]):
            a, b = out[-1], p
            zhch = r'[\u4e00-\u9fff，。！？；：、（）\u201c\u201d\u2018\u2019《》…—]'
            sep = '' if (re.search(zhch + '$', a) and re.match(zhch, b)) else ' '
            out[-1] = a + sep + p
            continue
        out.append(p)
    return out


def _chunks(seq, k):
    """把列表均分成 k 个连续块（块大小差 ≤1）"""
    k = max(1, min(k, len(seq)))
    base, extra = divmod(len(seq), k)
    out, i = [], 0
    for j in range(k):
        size = base + (1 if j < extra else 0)
        out.append(seq[i:i + size])
        i += size
    return out


# ---------------- 句子级切分 ----------------
SENT_EN = re.compile(r'[^.!?]+[.!?]+["\'”’)\]]*')
SENT_ZH = re.compile(r'[^。！？；]+[。！？；]+["”’』）\]）]*')


def sent_en(text):
    out = [m.group(0).strip() for m in SENT_EN.finditer(text)]
    out = [x for x in out if x]
    tail = SENT_EN.sub('', text).strip()
    if tail:
        out.append(tail)
    # 修复缩写/切分误判：
    #  'etc.), and ...' → 以逗号开头的伪句子；'etc.) and ...' → 小写开头的伪句子
    #  （英文句子不会以小写起头）；孤立标点句（如 '..'）并入前句
    merged = []
    for s in out:
        if merged and (re.match(r'[,;:]', s) or re.fullmatch(r'[.!?,"\')\]]+', s)
                       or s[:1].islower()):
            sep = '' if re.match(r'[,.;:!?]', s) else ' '
            merged[-1] = merged[-1] + sep + s
        else:
            merged.append(s)
    return merged


def sent_zh(text):
    out = [m.group(0).strip() for m in SENT_ZH.finditer(text)]
    out = [x for x in out if x]
    tail = SENT_ZH.sub('', text).strip()
    if tail:
        out.append(tail)
    return out


def split_long(en, target=600, minimum=2):
    """仅把超长英文段按句子切成若干阅读块（保留原有段落结构）。

    教材里的课文段落已是完整语义单元，切碎反而会破坏与译文的对应关系，
    因此只对整篇连排成一段的长文做分块，便于「一段一译」对照阅读。
    """
    out = []
    for p in en:
        if len(p) <= target:
            out.append(p)
            continue
        ss = sent_en(p)
        if len(ss) < minimum:
            out.append(p)
            continue
        n = max(minimum, int(round(len(p) / float(target))))
        n = min(n, len(ss))
        out.extend([' '.join(c) for c in _chunks(ss, n)])
    return out


def merge_to(seq, k, sep=' '):
    """把 seq 合并到 k 段（合并字符数总和最小的相邻段）"""
    seq = list(seq)
    while len(seq) > k and len(seq) > 1:
        i = min(range(len(seq) - 1), key=lambda i: len(seq[i]) + len(seq[i + 1]))
        seq[i] = seq[i] + sep + seq.pop(i + 1)
    return seq


def _w_en(x):
    """英文句的等效汉字长度（英文约 5.5 字符 ≈ 1 个汉字）"""
    return max(1.0, len(x) / 5.5)


def _w_zh(x):
    c = len(re.findall(r'[\u4e00-\u9fff]', x))
    return max(1.0, float(c) if c else len(x) / 2.0)


def sent_align(E, Z):
    """英文句序列与中文句序列的单调对齐（动态规划）。

    允许 1:1 / 1:2 / 1:3 / 2:1 / 3:1 的对应关系，代价取等效长度差。
    返回：每个英文句对应的中文句区间 [j0, j1)。
    """
    n, m = len(E), len(Z)
    ew = [_w_en(x) for x in E]
    zw = [_w_zh(x) for x in Z]
    INF = float('inf')
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[(1, 1)] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        row, bkr = dp[i], bk[i]
        for j in range(1, m + 1):
            best, arg = dp[i - 1][j - 1] + abs(ew[i - 1] - zw[j - 1]), (1, 1)
            for k in (2, 3, 4, 5, 6, 8):        # 一个英文句对应多个中文短句
                if j - k >= 0 and dp[i - 1][j - k] < INF:
                    c = dp[i - 1][j - k] + abs(ew[i - 1] - sum(zw[j - k:j])) + 0.6 * (k - 1)
                    if c < best:
                        best, arg = c, (1, k)
            for k in (2, 3, 4):                 # 多个英文短句对应一个中文句
                if i - k >= 0 and dp[i - k][j - 1] < INF:
                    c = dp[i - k][j - 1] + abs(sum(ew[i - k:i]) - zw[j - 1]) + 0.6 * (k - 1)
                    if c < best:
                        best, arg = c, (k, 1)
            row[j], bkr[j] = best, arg
    if dp[n][m] == INF:                          # 无可行对齐 → 交由比例法兜底
        return None
    res = [(0, 0)] * n
    i, j = n, m
    while i > 0 and j > 0:
        di, dj = bk[i][j]
        if di == 0 or dj == 0:
            break
        for t in range(di):
            res[i - 1 - t] = (j - dj, j)
        i -= di
        j -= dj
    while i > 0:                     # 中文句已用完的残余英文句 → 挂到末尾
        res[i - 1] = (max(0, m - 1), m)
        i -= 1
    if j > 0:                        # 开头未覆盖的中文句 → 并入第一个英文句
        a, b = res[0]
        res[0] = (0, max(b, j))
    return res


def align(en, zh, split=True):
    """英/中严格一一对应：

    1) 英文保留原段落结构，仅超长段按句子切成阅读块（split=False 表示分段已权威，不动）；
    2) 中文不再依赖原分段，而是切成句子流后与英文句做动态规划对齐，
       再按英文段落的句子范围合并 —— 保证语义顺序一致、无错位、无缺段。
    """
    if not en or not zh:
        return en, zh
    if split:
        en = split_long(en)
    K = len(en)

    # 英文句子流 + 每段覆盖的句子索引范围
    E, spans = [], []
    for p in en:
        ss = sent_en(p) or [p]
        spans.append((len(E), len(E) + len(ss)))
        E.extend(ss)

    Z = sent_zh(''.join(zh))
    if not Z:
        return en, [''] * K
    if len(Z) < K:                      # 中文句子不够分 → 收缩英文段数
        en = merge_to(en, len(Z))
        return align(en, zh, split=False) if len(en) != K else (en, [''] * len(en))

    pairs = sent_align(E, Z)
    if pairs is None:
        return _align_ratio(en, Z, K)
    out, prev_end = [], 0
    for s0, s1 in spans:
        j0 = pairs[s0][0]
        j1 = pairs[s1 - 1][1]
        if j0 < prev_end:            # 与上一段重叠（多个英文句共用一个中文句）→ 去掉重复
            j0 = prev_end
        if j1 <= j0:
            j1 = min(len(Z), j0 + 1)
        out.append(''.join(Z[j0:j1]))
        prev_end = j1
    # 兜底：任一段为空则用比例法重切
    if any(not x.strip() for x in out):
        return _align_ratio(en, Z, K)
    return en, out


def _align_ratio(en, Z, K):
    """按累计字符比例把中文句流切成 K 段（DP 对齐失效时的兜底）"""
    te = float(sum(len(x) for x in en)) or 1.0
    bounds, acc = [], 0
    for x in en:
        acc += len(x)
        bounds.append(acc / te)
    tz = float(sum(len(x) for x in Z)) or 1.0
    zpos, acc = [], 0
    for x in Z:
        acc += len(x)
        zpos.append(acc / tz)
    out, prev = [], 0
    for bi, r in enumerate(bounds):
        rest = K - bi - 1
        if bi == K - 1:
            j = len(Z)
        else:
            best, bd = prev + 1, None
            for j2 in range(prev + 1, min(len(Z) - rest + 1, len(Z))):
                d = abs(zpos[j2 - 1] - r)
                if bd is None or d < bd:
                    bd, best = d, j2
            j = max(prev + 1, best)
        out.append(''.join(Z[prev:j]))
        prev = j
    return en, out


# ---------------- 押题库 51 篇 ----------------
def extract_yatiku():
    path = os.path.join(SRC, '2610押题库短文.txt')
    L = open(path, encoding='utf-8', errors='ignore').read().splitlines()

    # 目录区（含真题命中标注）
    toc = '\n'.join(L[17:126])
    meta = {}
    for p in re.split(r'(?=第\s*\d+\s*篇)', toc):
        m = re.match(r'第\s*(\d+)\s*篇', p)
        if not m:
            continue
        n = int(m.group(1))
        body = re.sub(r'\.{4,}', ' ', p)
        body = re.sub(r'\s+', ' ', body)
        pg = re.search(r'P?\s*(P\d{3}|\d{3})(?:\s*-\s*(\d{3}))?', body)
        page = (pg.group(1) if pg else '').lstrip('P')
        if pg and pg.group(2):
            page += '-' + pg.group(2)
        hits = []
        for y, mo, t in re.findall(r'((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月([^()（）]{0,60}?)(?:来源|）|\))', body):
            for seg in re.split(r'[、,]', t):
                seg = seg.strip()
                if not seg:
                    continue
                ym = re.match(r'((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月(.+)$', seg)
                if ym:
                    y, mo, seg = int(ym.group(1)), int(ym.group(2)), ym.group(3).strip()
                for k in ['阅读判断', '阅读选择', '概括段落大意', '概括补全', '填句补文', '填词补文', '完形补文', '完形填空']:
                    if k in seg:
                        prov = re.sub(k, '', seg).replace('来源', '').strip(' 卷').replace('出题', '')
                        hits.append({'y': str(y), 'm': str(mo), 'type': k, 'prov': prov})
                        break
        meta[n] = {'page': page, 'hits': hits}

    # 正文区
    idx = {}
    for i in range(126, len(L)):
        m = re.match(r'^\s*第[\s]*(\d+)[ ]*篇', L[i])
        if m:
            n = int(m.group(1))
            if n not in idx:
                idx[n] = i
    keys = sorted(idx)
    out = []
    for k, n in enumerate(keys):
        st = idx[n] + 1
        en = idx[keys[k + 1]] if k + 1 < len(keys) else len(L)
        en_lines, zh_lines = split_en_zh(L[st:en])
        if not en_lines:
            continue
        out.append({
            'id': 'Y%02d' % n,
            'book': 'yatiku',
            'no': n,
            'page': meta.get(n, {}).get('page', ''),
            'title': '',
            'hits': meta.get(n, {}).get('hits', []),
            'en': join_en(en_lines),
            'zh': join_zh(zh_lines),
        })
    return out


# ---------------- 补充版 24 篇 ----------------
# 解析/题目特征标记：正文区一旦出现即视为课文结束（行内截断并丢弃后续）
CUT_MARKS = [
    'information given in the text', '答案为', '答案是', '译为', '由此可知',
    '由此看出', '可知，', '句意', '意思是', '【答案解析】', '【正确答案】',
]


def extract_buchong():
    """补充版 24 篇：以「官方教材网页版（课文+单词）」HTML 为准（data/official.json，
    由 tools/extract_official.py 生成——英文分段与官方对照翻译均来自教材原文件）；
    官方缺篇时回退到 PDF 文本解析。官方数据分段权威，后续 align 不再切段。"""
    off_path = os.path.join(BASE, 'data', 'official.json')
    off = {}
    if os.path.exists(off_path):
        try:
            off = json.load(open(off_path, encoding='utf-8'))
        except Exception as e:
            print('official.json 读取失败，全部回退 PDF:', e)

    pdf = extract_buchong_pdf()
    pdf_by_id = {p['id']: p for p in pdf}

    units = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
    out = []
    for u in units:
        for ab in 'AB':
            pid = 'B%s%s' % (u, ab)
            if pid in off:
                d = off[pid]
                if not d['en']:
                    print(pid, '官方数据缺课文，回退 PDF')
                else:
                    out.append({
                        'id': pid, 'book': 'buchong', 'unit': u, 'ab': ab,
                        'title': d.get('title_en', ''),
                        'hits': [],
                        'en': d['en'], 'zh': d['zh'],
                        '_nosplit': True,
                    })
                    continue
            if pid in pdf_by_id:
                out.append(pdf_by_id[pid])
    # 兜底：PDF 里有但顺序表没覆盖的篇目
    seen = {p['id'] for p in out}
    for p in pdf:
        if p['id'] not in seen:
            out.append(p)
    return out


def extract_buchong_pdf():
    """PDF 文本解析（官方 HTML 缺篇时的回退路径）"""
    path = os.path.join(SRC, '2610押题库短文 补充.txt')
    L = open(path, encoding='utf-8', errors='ignore').read().splitlines()
    units = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
    pos = []
    for i, l in enumerate(L):
        m = re.match(r'^\s*第(%s)单元课文' % '|'.join(units), l)
        if m and i > 140:
            pos.append((m.group(1), i))
    out = []
    for k, (u, st) in enumerate(pos):
        end = pos[k + 1][1] if k + 1 < len(pos) else len(L)
        seg = L[st:end]
        # 找 TEXT A / TEXT B 的位置
        marks = []
        for j, l in enumerate(seg):
            m = re.match(r'^\s*TEXT\s*([AB])\b', l.strip())
            if m:
                marks.append((m.group(1), j))
        for mi, (ab, j) in enumerate(marks):
            jend = marks[mi + 1][1] if mi + 1 < len(marks) else len(seg)
            block = seg[j + 1:jend]
            en_raw, zh_raw = [], []
            in_trans = False   # 参考翻译区
            in_ex = False      # 题目/解析区（Directions 之后全部丢弃）
            for raw in block:
                s = clean_line(raw)
                if not s:
                    continue
                if re.match(r'^参考翻译[:：]?', s):
                    in_trans = True
                    in_ex = False
                    s = re.sub(r'^参考翻译[:：]?', '', s)
                if re.match(r'^Directions\s*[:：]', s) or re.match(r'^说明\s*[:：]', s):
                    in_trans = False
                    in_ex = True          # 之后全部是题目与解析
                    continue
                if in_ex:
                    continue
                if in_trans:
                    if is_zh(s):
                        zh_raw.append(s)
                    continue
                # ---- 正文区 ----
                if is_zh(s):
                    continue              # 正文区的中文行（解析混排）跳过
                hit = next((m for m in CUT_MARKS if m in s), None)
                if hit is not None:       # 课文到此结束，后面全是题目/解析
                    head = s.split(hit)[0].strip()
                    if len(head) > 30:
                        en_raw.append(head)
                    break
                if re.match(r'^\d+[.、]', s):       # 题号
                    continue
                if re.match(r'^\s*[A-D][.、]\s', s):  # 选项
                    continue
                en_raw.append(s)
            # 标题：英文块第一行若为短标题则取出
            title = ''
            if en_raw and len(en_raw[0]) < 60 and not en_raw[0].endswith('.'):
                title = en_raw[0]
                en_raw = en_raw[1:]
            if not en_raw:
                continue
            out.append({
                'id': 'B%s%s' % (u, ab),
                'book': 'buchong',
                'unit': u,
                'ab': ab,
                'title': title,
                'hits': [],
                'en': join_en(en_raw),
                'zh': join_zh(zh_raw),
            })
    return out


# ---------------- 档位与主题 ----------------
LEVEL = {
    'Y01': 'A', 'Y06': 'A', 'Y34': 'A', 'Y51': 'A', 'B一A': 'A', 'B四B': 'A',
    'Y21': 'B', 'Y25': 'B', 'Y26': 'B', 'Y28': 'B', 'Y32': 'B', 'Y37': 'B', 'Y47': 'B',
    'B三A': 'B', 'B十一A': 'B',
    'Y04': 'C', 'Y07': 'C', 'Y08': 'C', 'Y10': 'C', 'Y13': 'C', 'Y15': 'C', 'Y18': 'C',
    'Y27': 'C', 'Y38': 'C', 'Y41': 'C', 'Y46': 'C',
}

TOPIC = {
    'Y01': '语言的力量', 'Y02': '灵活读者的四种阅读风格', 'Y03': '学语言要关注表达方式',
    'Y04': '英语在职场中的重要作用', 'Y05': '菲利普·伦道夫（黑人民权领袖）',
    'Y06': '不要怕犯错，错误铺就成功路', 'Y07': '向前失败', 'Y08': '成功者"向前失败"的四种能力',
    'Y09': '如何买到可靠的二手车', 'Y10': '如何选择朋友', 'Y11': '老朋友如同旧手套',
    'Y12': '你心目中的好朋友', 'Y13': '我的小侄女', 'Y14': 'Monday Blues（周一综合症）',
    'Y15': '把爱带进工作', 'Y16': '择业前先看清动机', 'Y17': '第一次约会的四种结局',
    'Y18': '人生的目的', 'Y19': '一位热爱万物的老人', 'Y20': '沃尔特·迪士尼的名言与梦想',
    'Y21': '理财其实很简单：先付给自己', 'Y22': '孩子的零花钱怎么给', 'Y23': '如何成为一个阅读者',
    'Y24': '人们如何看待金钱', 'Y25': '语言有力量', 'Y26': '内心的声音', 'Y27': '微笑的价值',
    'Y28': '劳动力市场"中层"萎缩的原因', 'Y29': '天赋与技能的区别', 'Y30': '质疑自身存在的时刻',
    'Y31': '谁是民主之父', 'Y32': '史蒂夫·乔布斯的早年', 'Y33': '电子邮件的三种类型',
    'Y34': '胡萝卜、鸡蛋与咖啡豆', 'Y35': '职场中的恐惧与自我怀疑', 'Y36': '困境使人强大还是压垮人',
    'Y37': '网络聊天安全', 'Y38': '可持续交通', 'Y39': '公共交通比开车更好吗',
    'Y40': '房地产的"地段"法则', 'Y41': '个人理财', 'Y42': '满街的广告牌',
    'Y43': '网络无处不在', 'Y44': '网络关系', 'Y45': '教妈妈上网', 'Y46': '网络电视',
    'Y47': '家乡与大学城的共同点', 'Y48': '压力与健康', 'Y49': '不要拿自己和别人比',
    'Y50': '与自己相处的时间最长', 'Y51': '养一只小狗的三大影响',
    'B一A': '批判性阅读', 'B一B': '自信的语言', 'B二A': '打翻的牛奶', 'B二B': '辛迪的午夜',
    'B三A': '友谊与忠诚', 'B三B': '人最好的朋友也可能反目', 'B四A': '工作是一种福分',
    'B四B': '如何创业', 'B五A': '生活是艰难的', 'B五B': '重新开始',
    'B六A': '教孩子明智使用零花钱', 'B六B': '金钱在生活中的重要性',
    'B七A': '内心的声音', 'B七B': '留下良好的第一印象', 'B八A': '假如生来没有双臂',
    'B八B': '不被期待的婴儿：乔布斯', 'B九A': '生活给你负数也能变美景', 'B九B': '三弦小提琴',
    'B十A': '公共交通的重要性', 'B十B': '乘坐公共交通的个人好处', 'B十一A': '网恋',
    'B十一B': '互联网对社会的影响', 'B十二A': '糟糕的早晨与情绪', 'B十二B': '自尊与身体意象',
}


def spacing_zh(p):
    """译文中英交界补空格：'的Ask' → '的 Ask'，'kick球' → 'kick 球'（引号/括号交界不动）"""
    p = re.sub(r'(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])', ' ', p)
    p = re.sub(r'(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])', ' ', p)
    return p


def main():
    y = extract_yatiku()
    b = extract_buchong()
    allp = y + b
    for p in allp:
        nosplit = p.pop('_nosplit', False)
        p['en'], p['zh'] = align(p['en'], p['zh'], split=not nosplit)
        p['zh'] = [spacing_zh(z) for z in p['zh']]
        p['level'] = LEVEL.get(p['id'], 'D' if p['book'] == 'buchong' else 'E')
        p['topic'] = TOPIC.get(p['id'], p.get('title', ''))
    out = {
        'meta': {
            'course': '英语（专升本）',
            'code': '13000',
            'book': ['2610押题库短文', '2610押题库短文 补充版'],
            'count': len(allp),
            'generated': '2026-10-10',
        },
        'passages': allp,
    }
    dst = os.path.join(BASE, 'data', 'passages.json')
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('押题库 %d 篇 / 补充版 %d 篇 = 共 %d 篇' % (len(y), len(b), len(allp)))
    miss_en = [p['id'] for p in allp if not p['en']]
    miss_zh = [p['id'] for p in allp if not p['zh']]
    print('缺英文:', miss_en)
    print('缺中文:', miss_zh)
    for p in allp[:2] + allp[-1:]:
        print('\n---', p['id'], p['topic'], '| level', p['level'])
        print('  EN段数', len(p['en']), '首段:', p['en'][0][:90])
        print('  ZH段数', len(p['zh']), '首段:', (p['zh'][0][:70] if p['zh'] else '（无）'))


if __name__ == '__main__':
    main()

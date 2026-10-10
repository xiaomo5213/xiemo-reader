# -*- coding: utf-8 -*-
"""
从「官方教材网页版（课文+单词）」24 个 HTML 提取课文与官方对照翻译。
输出 data/official.json：
    { "B一A": {"title_en":..., "title_zh":..., "en":[...], "zh":[...], "vocab":[...]} }

要点：
- .article 下的 <p> = 英文段落（权威分段，不做任何重新分段）
- .translation 下的 <p> = 中文翻译段落
- 内联标签（span/b/em/i/a/u）直接剥离【不加空格】，否则 "assertion<span>s</span>"
  会被拆成 "assertion s"；块级标签（p/div/br/h*）换成换行。
- 英中两侧与 h1 重复的标题段各自剔除，剩余段落交给 extract_passages.py 的 DP 句对齐。
"""
import re, json, os, sys

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'C:/Users/taozhenlong/Desktop/官方教材网页版（课文+单词）'
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'official.json')

CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']

ENT = {
    '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"',
    '&#39;': "'", '&apos;': "'", '&rsquo;': '\u2019', '&lsquo;': '\u2018',
    '&ldquo;': '\u201c', '&rdquo;': '\u201d', '&mdash;': '—', '&ndash;': '–',
    '&hellip;': '…', '&middot;': '·',
}


def strip_html(s):
    s = re.sub(r'(?i)<(script|style)\b.*?</\1>', '', s, flags=re.S)
    s = re.sub(r'(?i)</?(?:p|div|br|h[1-6]|li|ul|ol|section|article|table|tr)[^>]*>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)                    # 内联标签：直接剥离，不加空格
    for k, v in ENT.items():
        s = s.replace(k, v)
    out = []
    for line in s.split('\n'):
        line = re.sub(r'\s+', ' ', line).strip()
        if line:
            out.append(line)
    return out


def block(t, cls):
    """取 <div class="cls"> 到下一个 <section 之间的内容（避开嵌套 div 的配对问题）"""
    m = re.search(r'<div class="%s"[^>]*>' % cls, t)
    if not m:
        return ''
    rest = t[m.end():]
    i = rest.find('<section')
    return rest[:i] if i >= 0 else rest


def paras(t, cls):
    ps = re.findall(r'<p[^>]*>(.*?)</p>', block(t, cls), re.S)
    return [x for x in (strip_html(p)[0] if strip_html(p) else '' for p in ps) if x]


def norm(s):
    return re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', s.lower())


def parse(path):
    t = open(path, encoding='utf-8').read()
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S)
    title_en = strip_html(h1.group(1))[0] if h1 else ''
    mt = re.search(r'<title>(.*?)</title>', t, re.S)
    title_zh = ''
    if mt:
        seg = strip_html(mt.group(1))
        if seg:
            seg = seg[0]
            if ' - ' in seg:
                seg = seg.split(' - ')[1]
            title_zh = seg.split('|')[0].strip()
    en = paras(t, 'article')
    zh = paras(t, 'translation')
    # 去掉与标题重复的首段
    if en and norm(en[0]) == norm(title_en):
        en = en[1:]
    if zh and norm(zh[0]) == norm(title_zh):
        zh = zh[1:]
    # 单词表：脚本区的 const vocabulary = [{word, phonetic, pos, definition}, ...]
    vocab = []
    for m in re.finditer(r'\{\s*word:\s*"([^"]+)"\s*,\s*phonetic:\s*"([^"]*)"\s*,\s*'
                         r'pos:\s*"([^"]*)"\s*,\s*definition:\s*"([^"]*)"', t):
        vocab.append({'w': m.group(1), 'ph': m.group(2), 'pos': m.group(3), 'd': m.group(4)})
    return {'title_en': title_en, 'title_zh': title_zh, 'en': en, 'zh': zh, 'vocab': vocab}


def main():
    out = {}
    for n in range(1, 13):
        for ab in 'AB':
            f = os.path.join(SRC, '%d%s.html' % (n, ab))
            pid = 'B%s%s' % (CN[n - 1], ab)
            if not os.path.exists(f):
                print('缺失文件:', f)
                continue
            d = parse(f)
            out[pid] = d
            flag = '' if len(d['en']) == len(d['zh']) else '  ← 段数差 %d' % (len(d['en']) - len(d['zh']))
            print('%-6s %-38s EN=%2d ZH=%2d 词表=%d%s' %
                  (pid, d['title_en'][:36], len(d['en']), len(d['zh']), len(d['vocab']), flag))
    json.dump(out, open(DST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('→', DST)


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""
批量抓取离线词库（有道词典 jsonapi），生成 data/dict.json

用法：
    python tools/fetch_dict.py            # 增量抓取（跳过已有词条）
    python tools/fetch_dict.py --all      # 强制重抓

输出 data/dict.json 结构：
    {
      "language": {"us":"ˈlæŋɡwɪdʒ","uk":"ˈlæŋɡwɪdʒ","d":"n. 语言，语言文字；言语…"}
    }
"""
import re, json, os, sys, time, argparse
import urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_PATH = os.path.join(BASE, 'data', 'dict.json')
PASSAGES = os.path.join(BASE, 'data', 'passages.json')

API = 'https://dict.youdao.com/jsonapi?q=%s'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://dict.youdao.com/',
}
MAX_DEF = 150   # 释义最大长度


def strip_tags(s):
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def fetch(word, retry=2):
    for attempt in range(retry + 1):
        try:
            url = API % urllib.parse.quote(word)
            req = urllib.request.Request(url, headers=HEADERS)
            raw = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', 'ignore')
            d = json.loads(raw)
            ec = d.get('ec') or {}
            words = ec.get('word') or []
            if not words:
                return None
            w0 = words[0]
            us = w0.get('usphone') or w0.get('phone') or ''
            uk = w0.get('ukphone') or w0.get('phone') or ''
            defs = []
            for tr in (w0.get('trs') or [])[:4]:
                for item in tr.get('tr', []):
                    lis = item.get('l', {}).get('i')
                    if lis:
                        if isinstance(lis, list):
                            lis = '；'.join(strip_tags(x) for x in lis)
                        defs.append(strip_tags(str(lis)))
            if not defs:
                return None
            joined = '；'.join(defs)
            if len(joined) > MAX_DEF:
                joined = joined[:MAX_DEF].rstrip('；，, ') + '…'
            return {'us': us, 'uk': uk, 'd': joined}
        except Exception:
            if attempt == retry:
                return None
            time.sleep(0.4 * (attempt + 1))
    return None


def collect_words():
    d = json.load(open(PASSAGES, encoding='utf-8'))
    txt = ' '.join(' '.join(p['en']) for p in d['passages'])
    ws = re.findall(r"[A-Za-z][A-Za-z'’\-]*", txt)
    return sorted({w.lower().strip("'-") for w in ws if len(w.strip("'-")) > 1})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true', help='强制重抓')
    args = ap.parse_args()

    words = collect_words()
    db = {}
    if os.path.exists(DICT_PATH) and not args.all:
        db = json.load(open(DICT_PATH, encoding='utf-8'))
    todo = [w for w in words if w not in db]
    print('词条总数 %d，已收录 %d，待抓 %d' % (len(words), len(db), len(todo)))
    if not todo:
        print('词库已是最新')
        return

    done = 0
    fail = []
    t0 = time.time()

    def work(w):
        return w, fetch(w)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, w) for w in todo]
        for i, f in enumerate(as_completed(futs), 1):
            w, r = f.result()
            if r:
                db[w] = r
                done += 1
            else:
                fail.append(w)
            if i % 200 == 0:
                json.dump(db, open(DICT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
                print('  进度 %d/%d  收录 %d  未收 %d  用时 %.0fs' % (i, len(todo), done, len(fail), time.time() - t0))
                sys.stdout.flush()

    json.dump(db, open(DICT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    size = os.path.getsize(DICT_PATH) / 1024
    print('完成：新增 %d 条，累计 %d 条，未收录 %d 个（%.0f KB，用时 %.0fs）'
          % (done, len(db), len(fail), size, time.time() - t0))
    if fail:
        print('未收录示例:', fail[:25])


if __name__ == '__main__':
    main()

/* 押题库短文精读 · 主逻辑
 * 数据与代码分离：data/passages.json（75 篇短文）、data/dict.json（离线词库）、data/config.json（可选）
 * 纯静态，无框架无构建，可直接 push 到 GitHub Pages / 宝塔 / Vercel。
 */
(function () {
  'use strict';

  var LS = 'xiemo-reader-v1';

  var LEVELS = [
    ['A', 'A 档 · 必背（真题高频命中）', '#c0392b'],
    ['B', 'B 档 · 重点（多次命中）', '#e07b39'],
    ['C', 'C 档 · 常考', '#17a67a'],
    ['D', 'D 档 · 补充版', '#2f6fb5'],
    ['E', 'E 档 · 泛读（暂无命中）', '#6b7b8a']
  ];
  var LEVEL_TXT = { A: 'A', B: 'B', C: 'C', D: 'D', E: 'E' };

  var TYPE_SHORT = {
    '完形补文': '完形', '填词补文': '填词', '填句补文': '填句',
    '阅读判断': '判断', '阅读选择': '选择',
    '概括段落大意和补全句子': '概括'
  };

  // ---------- 状态 ----------
  var S = {
    mode: 'bi',      // en | bi | zh
    fs: 0,           // 字号增量 -2 ~ +3
    done: {},        // {id:1} 已读
    pos: {},         // {id:0~1} 每篇阅读滚动位置（学习进度）
    wb: [],          // 生词本
    last: '',        // 当前篇 id
    hide: false      // 生词本遮释义
  };

  var DATA = { meta: {}, passages: [] };
  var FILTER = 'ALL';
  var KW = '';
  var CUR = null;         // 当前篇对象
  var CUR_WORD = null;    // 弹窗当前词

  // ---------- 工具 ----------
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function save() {
    try { localStorage.setItem(LS, JSON.stringify(S)); } catch (e) { }
  }
  function load() {
    try {
      var s = JSON.parse(localStorage.getItem(LS) || '{}');
      if (s && typeof s === 'object') {
        S.mode = s.mode || 'bi';
        S.fs = typeof s.fs === 'number' ? s.fs : 0;
        S.done = s.done || {};
        S.pos = (s.pos && typeof s.pos === 'object') ? s.pos : {};
        S.wb = Array.isArray(s.wb) ? s.wb : [];
        S.last = s.last || '';
        S.hide = !!s.hide;
      }
    } catch (e) { }
  }
  var TOAST_T = null;
  function toast(msg) {
    var t = $('toast');
    t.textContent = msg;
    t.classList.add('on');
    clearTimeout(TOAST_T);
    TOAST_T = setTimeout(function () { t.classList.remove('on'); }, 1900);
  }
  function getJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(url + ' ' + r.status);
      return r.json();
    });
  }

  // ---------- 篇目辅助 ----------
  function pTitle(p) {
    if (p.title) return p.title;
    if (p.book === 'buchong') return '补充版 第' + p.unit + '单元 TEXT ' + p.ab;
    return '第 ' + p.no + ' 篇';
  }
  function pTag(p) {
    if (p.book === 'buchong') return '补 ' + p.unit + '-' + p.ab;
    return String(p.no);
  }
  function pFrom(p) { return p.book === 'buchong' ? '补充版' : '押题库'; }
  function shortHits(p) {
    var out = [], seen = {};
    (p.hits || []).forEach(function (h) {
      var y = String(h.y == null ? '' : h.y), m = String(h.m == null ? '' : h.m);
      var t = TYPE_SHORT[h.type] || h.type || '';
      var k = y + '.' + m + t;
      if (seen[k]) return;
      seen[k] = 1;
      out.push(y.slice(2) + '.' + m + (t ? ' ' + t : ''));
    });
    return out;
  }
  function matchKW(p) {
    if (!KW) return true;
    var t = (pTitle(p) + ' ' + (p.topic || '') + ' ' + pFrom(p) + ' 第' + p.no + '篇 ' +
      (p.en || []).join(' ')).toLowerCase();
    return t.indexOf(KW) >= 0;
  }
  function visible(p) {
    if (FILTER === 'UNDONE' && S.done[p.id]) return false;
    if (FILTER !== 'ALL' && FILTER !== 'UNDONE' && p.level !== FILTER) return false;
    return matchKW(p);
  }

  // ---------- 渲染：筛选 chips ----------
  function renderChips() {
    var items = [['ALL', '全部'], ['A', 'A 档'], ['B', 'B 档'], ['C', 'C 档'], ['D', 'D 档'], ['E', 'E 档'], ['UNDONE', '未读']];
    $('chips').innerHTML = items.map(function (it) {
      return '<button class="chip' + (FILTER === it[0] ? ' on' : '') + '" data-f="' + it[0] + '">' + it[1] + '</button>';
    }).join('');
  }

  // ---------- 渲染：篇目列表 ----------
  function renderList() {
    var box = $('plist');
    var html = '';
    var shown = 0;
    LEVELS.forEach(function (L) {
      var arr = DATA.passages.filter(function (p) { return p.level === L[0] && visible(p); });
      if (!arr.length) return;
      shown += arr.length;
      html += '<div class="pgroup"><div class="gh"><span class="dot" style="background:' + L[2] + '"></span>' +
        esc(L[1]) + ' · ' + arr.length + ' 篇</div>';
      arr.forEach(function (p) {
        var hits = shortHits(p).slice(0, 3);
        html += '<div class="pitem' + (p.id === S.last ? ' on' : '') + '" data-id="' + p.id + '">' +
          '<div class="l1"><span class="no">' + esc(pTag(p)) + '</span>' +
          '<span>' + esc(p.topic || pTitle(p)) + '</span>' +
          (S.done[p.id] ? '<span class="done">✓</span>' : '') + '</div>' +
          (p.title ? '<div class="l2">' + esc(p.title) + '</div>' : '<div class="l2">' + esc(pFrom(p)) + (p.page ? ' · P' + p.page : '') + '</div>') +
          (hits.length ? '<div class="hits">' + hits.map(function (h) { return '<i>' + esc(h) + '</i>'; }).join('') + '</div>' : '') +
          '</div>';
      });
      html += '</div>';
    });
    if (!shown) html = '<div class="empty">没有符合条件的篇目</div>';
    box.innerHTML = html;

    var total = DATA.passages.length;
    var dn = Object.keys(S.done).length;
    $('cntShown').textContent = shown;
    var pct = total ? Math.round(dn / total * 100) : 0;
    $('cntDone').textContent = '已读 ' + dn + ' / ' + total + ' · ' + pct + '%';
    var fill = $('pbarFill');
    if (fill) fill.style.width = pct + '%';
  }

  // ---------- 渲染：阅读区 ----------
  function tokenize(t) {
    var parts = String(t).split(/([A-Za-z]+(?:['’\-][A-Za-z]+)*)/g);
    var out = '';
    for (var i = 0; i < parts.length; i++) {
      if (i % 2) out += '<span class="w" data-w="' + parts[i].toLowerCase() + '">' + esc(parts[i]) + '</span>';
      else out += esc(parts[i]);
    }
    return out;
  }

  function renderReader() {
    var w = $('rwrap');
    if (!CUR) {
      w.innerHTML = '<div class="empty">从左侧选择一篇短文开始阅读<br><span style="font-size:12.5px;color:#9aa9b3">手机端点底部「目录」</span></div>';
      return;
    }
    var en = CUR.en || [], zh = CUR.zh || [];
    var tags = shortHits(CUR);
    var h = '';

    h += '<div class="rhead">' +
      '<div class="t1"><h1>' + esc(pTitle(CUR)) + '</h1>' +
      '<span class="no">' + esc(pFrom(CUR)) + (CUR.page ? ' · P' + CUR.page : '') + ' · ' + CUR.id + '</span></div>' +
      '<div class="topic">' + esc(CUR.topic || '') + '</div>' +
      '<div class="meta">' +
      '<span>' + LEVEL_TXT[CUR.level] + ' 档</span>' +
      '<span>' + en.length + ' 段 / ' + wordCount(en) + ' 词</span>' +
      (CUR.hits && CUR.hits.length ? '<span class="hit">真题命中 ' + CUR.hits.length + ' 次</span>' : '<span>暂无命中记录</span>') +
      tags.map(function (t) { return '<span class="hit">' + esc(t) + '</span>'; }).join('') +
      '</div>' +
      '<div class="tools">' +
      '<div class="seg" id="seg">' +
      '<button data-m="en" class="' + (S.mode === 'en' ? 'on' : '') + '">仅英文</button>' +
      '<button data-m="bi" class="' + (S.mode === 'bi' ? 'on' : '') + '">双语对照</button>' +
      '<button data-m="zh" class="' + (S.mode === 'zh' ? 'on' : '') + '">仅中文</button>' +
      '</div>' +
      '<button class="mini" id="fsDown" title="缩小字号">A－</button>' +
      '<button class="mini" id="fsUp" title="放大字号">A＋</button>' +
      '<button class="mini' + (S.done[CUR.id] ? ' on' : '') + '" id="btnDone">' +
      (S.done[CUR.id] ? '✓ 已读过' : '标记已读') + '</button>' +
      '<button class="mini" id="btnReadAll">🔊 全文朗读</button>' +
      '</div>' +
      '</div>';

    // 主题头图（16:9，数据里 img 字段指向 assets/img/<id>.svg）
    if (CUR.img) {
      h += '<div class="hero"><img src="' + esc(CUR.img) + '" alt="' +
        esc(CUR.topic || pTitle(CUR)) + ' 主题插图"></div>';
    }

    if (S.mode === 'en' || S.mode === 'bi') {
      h += '<div class="card"><div class="ch">原文 · ENGLISH</div>';
      if (S.mode === 'en') {
        en.forEach(function (t, i) {
          h += '<p class="enp"><i class="pn">' + (i + 1) + '</i>' + tokenize(t) + '</p>';
        });
      } else {
        var n = Math.max(en.length, zh.length);
        for (var i = 0; i < n; i++) {
          h += '<div class="bi"><div class="e"><i class="pn">' + (i + 1) + '</i>' +
            tokenize(en[i] || '') + '</div>' +
            (zh[i] ? '<div class="z"><em class="zl">译</em>' + esc(zh[i]) + '</div>' : '') +
            '</div>';
        }
      }
      h += '</div>';
    }
    if (S.mode === 'zh') {
      h += '<div class="card"><div class="ch">参考译文 · 中文</div>';
      zh.forEach(function (t, i) {
        h += '<p class="zhp"><i class="pn">' + (i + 1) + '</i>' + esc(t) + '</p>';
      });
      h += '</div>';
    }

    var idx = DATA.passages.indexOf(CUR);
    var prev = DATA.passages[idx - 1], next = DATA.passages[idx + 1];
    h += '<div class="pnav">' +
      '<button data-go="' + (prev ? prev.id : '') + '"' + (prev ? '' : ' disabled') + '>' +
      '<i>上一篇</i><b>' + esc(prev ? pTitle(prev) : '已是第一篇') + '</b></button>' +
      '<button class="next" data-go="' + (next ? next.id : '') + '"' + (next ? '' : ' disabled') + '>' +
      '<i>下一篇</i><b>' + esc(next ? pTitle(next) : '已是最后一篇') + '</b></button>' +
      '</div>';

    w.innerHTML = h;
    markKnownWords();
    applyFont();
  }

  function wordCount(arr) {
    var s = (arr || []).join(' ');
    var m = s.match(/[A-Za-z][A-Za-z'’-]*/g);
    return m ? m.length : 0;
  }

  /** 给已加入生词本的词加金色下划线 */
  function markKnownWords() {
    var set = {};
    S.wb.forEach(function (x) { set[x.w] = 1; if (x.base) set[x.base] = 1; });
    var ws = document.querySelectorAll('#rwrap .w');
    for (var i = 0; i < ws.length; i++) {
      var k = ws[i].getAttribute('data-w');
      if (set[k]) ws[i].classList.add('marked');
      else {
        var r = window.Dict.lookup(k);
        if (r && set[r.base]) ws[i].classList.add('marked');
      }
    }
  }

  function applyFont() {
    var en = 17 + S.fs, zh = 15 + S.fs;
    if (window.innerWidth <= 860) en = 16.5 + S.fs;
    document.documentElement.style.setProperty('--fen', en + 'px');
    document.documentElement.style.setProperty('--fzh', zh + 'px');
  }

  // ---------- 打开某篇 ----------
  function openPassage(id, keepScroll) {
    var p = DATA.passages.filter(function (x) { return x.id === id; })[0];
    if (!p) return;
    CUR = p;
    S.last = id;
    save();
    renderReader();
    renderList();
    // 恢复该篇上次阅读位置（学习进度）
    var rd = $('reader');
    var saved = S.pos[id] || 0;
    if (!keepScroll) {
      if (saved > 0.02) {
        requestAnimationFrame(function () {
          rd.scrollTop = saved * (rd.scrollHeight - rd.clientHeight);
        });
        toast('已恢复上次阅读进度');
      } else {
        rd.scrollTop = 0;
      }
    }
    if (window.innerWidth <= 860) closeDrawer();
    try { history.replaceState(null, '', '#' + id); } catch (e) { }
  }

  // ---------- 单词弹窗 ----------
  function sentenceOf(text, word) {
    var sents = String(text).match(/[^.!?]+[.!?]*/g) || [String(text)];
    var re = new RegExp('(^|[^a-z])' + word.replace(/[-'’]/g, '.') + '([^a-z]|$)', 'i');
    for (var i = 0; i < sents.length; i++) {
      if (re.test(sents[i])) return sents[i].trim();
    }
    return sents[0].trim();
  }

  var CTX = '';
  function openWord(el) {
    var raw = el.getAttribute('data-w') || '';
    if (!raw) return;
    var para = el.closest ? el.closest('.enp, .bi .e') : null;
    CTX = para ? sentenceOf(para.textContent, raw) : '';

    var r = window.Dict.lookup(raw);
    CUR_WORD = {
      w: raw,
      base: r ? r.base : raw,
      us: r ? r.us : '', uk: r ? r.uk : '', d: r ? r.d : '',
      found: !!r
    };
    paintWord();
    $('mask').classList.add('on');

    document.querySelectorAll('#rwrap .w.active').forEach(function (x) { x.classList.remove('active'); });
    el.classList.add('active');
  }

  function paintWord() {
    var c = CUR_WORD;
    $('pWord').textContent = c.w;
    var ph = '';
    if (c.uk) ph += '<span>英 <b>/' + esc(c.uk) + '/</b></span>';
    if (c.us) ph += '<span>美 <b>/' + esc(c.us) + '/</b></span>';
    if (c.found && c.base !== c.w) ph += '<span>（原形 ' + esc(c.base) + '）</span>';
    $('pPhn').innerHTML = ph || '<span>暂无音标</span>';

    if (c.found && c.d) {
      $('pDef').innerHTML = window.Dict.parseDef(c.d).map(function (x) {
        return '<div>' + (x.pos ? '<span class="pos">' + esc(x.pos) + '</span>' : '') + esc(x.def) + '</div>';
      }).join('');
    } else {
      $('pDef').innerHTML = '<div class="none">离线词库暂未收录该词。' +
        '可在电脑上执行 <b>python tools/fetch_dict.py</b> 补全词库，或直接点发音试听。</div>';
    }

    if (CTX) {
      var hl = CTX.replace(new RegExp('(' + c.w.replace(/[-'’]/g, '.') + ')', 'ig'), '<b>$1</b>');
      $('pCtx').innerHTML = '例句：' + hl;
      $('pCtx').style.display = '';
    } else {
      $('pCtx').style.display = 'none';
    }

    var inWb = !!S.wb.filter(function (x) { return x.w === c.w; }).length;
    var b = $('pAdd');
    b.textContent = inWb ? '✓ 已在生词本' : '＋ 加入生词本';
    b.classList.toggle('in', inWb);
  }

  function closeWord() {
    $('mask').classList.remove('on');
    document.querySelectorAll('#rwrap .w.active').forEach(function (x) { x.classList.remove('active'); });
  }

  function addWord() {
    if (!CUR_WORD) return;
    var c = CUR_WORD;
    var i = S.wb.findIndex(function (x) { return x.w === c.w; });
    if (i >= 0) {
      S.wb.splice(i, 1);
      toast('已从生词本移除 ' + c.w);
    } else {
      S.wb.unshift({
        w: c.w, base: c.base, us: c.us, uk: c.uk, d: c.d,
        s: CTX, p: CUR ? pTitle(CUR) : '', pid: CUR ? CUR.id : '', t: Date.now()
      });
      toast('已加入生词本 ' + c.w);
    }
    save(); paintWord(); renderWBBadge(); markKnownWords();
    if ($('wbPage').classList.contains('on')) renderWB();
  }

  // ---------- 生词本 ----------
  function renderWBBadge() {
    var n = S.wb.length;
    $('wbBadge').textContent = n;
    $('wbBadge2').textContent = n;
    $('wbBadge').style.display = n ? '' : 'none';
    $('wbBadge2').style.display = n ? '' : 'none';
  }

  function renderWB() {
    var box = $('wbList');
    $('wbCnt').textContent = S.wb.length + ' 个词';
    if (!S.wb.length) {
      box.innerHTML = '<div class="empty">生词本是空的<br><span style="font-size:12.5px;color:#9aa9b3">阅读时点击任意单词 → 加入生词本</span></div>';
      return;
    }
    box.innerHTML = S.wb.map(function (x, i) {
      var defs = window.Dict.parseDef(x.d);
      return '<div class="wbcard" data-i="' + i + '">' +
        '<div class="info">' +
        '<div class="w">' + esc(x.w) + (x.base && x.base !== x.w ? ' <span class="phn">原形 ' + esc(x.base) + '</span>' : '') +
        (x.uk ? ' <span class="phn">/' + esc(x.uk) + '/</span>' : (x.us ? ' <span class="phn">/' + esc(x.us) + '/</span>' : '')) +
        '</div>' +
        '<div class="d' + (S.hide ? ' hide' : '') + '">' +
        (x.d ? defs.map(function (t) {
          return '<div>' + (t.pos ? '<span class="pos">' + esc(t.pos) + '</span>' : '') + esc(t.def) + '</div>';
        }).join('') : '<span style="color:#9aa9b3">（无释义）</span>') +
        '</div>' +
        '<div class="src">' + (x.p ? '来自《' + esc(x.p) + '》' : '') + (x.s ? ' · ' + esc(x.s.slice(0, 60)) : '') + '</div>' +
        '</div>' +
        '<div class="op">' +
        '<button class="iconbtn spk" title="发音">🔊</button>' +
        '<button class="iconbtn del" title="删除">🗑</button>' +
        '</div></div>';
    }).join('');
  }

  function openWB() {
    renderWB();
    $('wbPage').classList.add('on');
    try { history.replaceState(null, '', '#wb'); } catch (e) { }
    document.querySelectorAll('#tabbar button').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-tab') === 'wb');
    });
  }
  function closeWB() {
    $('wbPage').classList.remove('on');
    try { history.replaceState(null, '', '#' + (S.last || '')); } catch (e) { }
    document.querySelectorAll('#tabbar button').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-tab') === 'read');
    });
  }

  function exportWB() {
    if (!S.wb.length) { toast('生词本为空'); return; }
    var rows = [['单词', '原形', '音标(英)', '释义', '例句', '来源']];
    S.wb.forEach(function (x) {
      rows.push([x.w, x.base || '', x.uk || x.us || '', x.d || '', x.s || '', x.p || '']);
    });
    var csv = '\ufeff' + rows.map(function (r) {
      return r.map(function (c) { return '"' + String(c).replace(/"/g, '""') + '"'; }).join(',');
    }).join('\r\n');
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = '生词本_' + new Date().toISOString().slice(0, 10) + '.csv';
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    toast('已导出 ' + S.wb.length + ' 个单词');
  }

  // 连读发音（移动端需先有用户手势，逐词播放）
  function speakAll() {
    if (!S.wb.length) { toast('生词本为空'); return; }
    var i = 0;
    toast('开始朗读 ' + Math.min(S.wb.length, 30) + ' 个单词');
    (function step() {
      if (i >= S.wb.length || i >= 30) return;
      var w = S.wb[i++];
      window.Dict.speak(w.w, 1, step);
    })();
  }

  // ---------- 抽屉（移动端） ----------
  function openDrawer() {
    $('side').classList.add('on');
    $('sideMask').classList.add('on');
  }
  function closeDrawer() {
    $('side').classList.remove('on');
    $('sideMask').classList.remove('on');
  }

  // ---------- 事件绑定 ----------
  function bind() {
    $('plist').addEventListener('click', function (e) {
      var it = e.target.closest('.pitem');
      if (it) openPassage(it.getAttribute('data-id'));
    });

    $('chips').addEventListener('click', function (e) {
      var b = e.target.closest('.chip');
      if (!b) return;
      FILTER = b.getAttribute('data-f');
      renderChips(); renderList();
    });

    $('q').addEventListener('input', function (e) {
      KW = (e.target.value || '').trim().toLowerCase();
      renderList();
    });

    $('rwrap').addEventListener('click', function (e) {
      var w = e.target.closest ? e.target.closest('.w') : null;
      if (w) { openWord(w); return; }

      var seg = e.target.closest('#seg');
      if (seg) {
        var b = e.target.closest('button');
        if (b && b.getAttribute('data-m')) {
          S.mode = b.getAttribute('data-m'); save(); renderReader();
        }
        return;
      }
      if (e.target.id === 'fsUp') { if (S.fs < 4) { S.fs++; save(); applyFont(); } return; }
      if (e.target.id === 'fsDown') { if (S.fs > -2) { S.fs--; save(); applyFont(); } return; }
      if (e.target.id === 'btnDone') {
        if (S.done[CUR.id]) delete S.done[CUR.id]; else S.done[CUR.id] = 1;
        save(); renderReader(); renderList();
        toast(S.done[CUR.id] ? '已标记为读过 ✓' : '已取消标记');
        return;
      }
      if (e.target.id === 'btnReadAll') {
        var txt = (CUR.en || []).join(' ');
        var sents = txt.match(/[^.!?]+[.!?]*/g) || [txt];
        var i = 0;
        toast('开始朗读全文（' + sents.length + ' 句）');
        (function step() {
          if (i >= sents.length || i >= 25) return;
          var s = sents[i++].trim().replace(/["'“”]/g, '');
          if (s.length > 110) s = s.slice(0, 110);
          window.Dict.speak(s, 1, step);
        })();
        return;
      }
      var nav = e.target.closest('.pnav button');
      if (nav && nav.getAttribute('data-go')) openPassage(nav.getAttribute('data-go'));
    });

    // 单词弹窗
    $('mask').addEventListener('click', function (e) { if (e.target === $('mask')) closeWord(); });
    $('pClose').addEventListener('click', closeWord);
    $('pAdd').addEventListener('click', addWord);
    $('pUk').addEventListener('click', function () {
      this.classList.add('playing');
      var b = this;
      window.Dict.speak(CUR_WORD.w, 1, function () { b.classList.remove('playing'); });
    });
    $('pUs').addEventListener('click', function () {
      this.classList.add('playing');
      var b = this;
      window.Dict.speak(CUR_WORD.w, 2, function () { b.classList.remove('playing'); });
    });

    // 生词本
    $('btnWb').addEventListener('click', openWB);
    $('wbBack').addEventListener('click', closeWB);
    $('wbClear').addEventListener('click', function () {
      if (!S.wb.length) { toast('生词本为空'); return; }
      if (confirm('确定清空生词本（' + S.wb.length + ' 个词）？')) {
        S.wb = []; save(); renderWB(); renderWBBadge(); markKnownWords(); toast('已清空');
      }
    });
    $('wbHide').addEventListener('click', function () {
      S.hide = !S.hide; save(); renderWB();
      this.classList.toggle('on', S.hide);
      this.textContent = S.hide ? '显示释义' : '遮住释义';
      toast(S.hide ? '已遮住释义，点击卡片可单独查看' : '已显示释义');
    });
    $('wbExport').addEventListener('click', exportWB);
    $('wbSpeak').addEventListener('click', speakAll);
    $('wbList').addEventListener('click', function (e) {
      var card = e.target.closest('.wbcard');
      if (!card) return;
      var i = parseInt(card.getAttribute('data-i'), 10);
      var x = S.wb[i];
      if (!x) return;
      if (e.target.closest('.del')) {
        S.wb.splice(i, 1); save(); renderWB(); renderWBBadge(); markKnownWords();
        toast('已删除 ' + x.w);
        return;
      }
      if (e.target.closest('.spk')) {
        window.Dict.speak(x.w, 1);
        return;
      }
      var d = card.querySelector('.d');
      if (d && d.classList.contains('hide')) d.classList.remove('hide');
    });

    // 抽屉 / tabbar
    $('btnMenu').addEventListener('click', openDrawer);
    $('sideMask').addEventListener('click', closeDrawer);
    $('tabbar').addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      var t = b.getAttribute('data-tab');
      document.querySelectorAll('#tabbar button').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on');
      if (t === 'list') openDrawer();
      if (t === 'read') { closeDrawer(); $('reader').scrollTop = 0; }
      if (t === 'wb') openWB();
    });

    // 阅读位置自动保存（学习进度，防抖 400ms）
    var scT = null;
    $('reader').addEventListener('scroll', function () {
      if (!CUR) return;
      clearTimeout(scT);
      scT = setTimeout(function () {
        var rd = $('reader');
        var max = rd.scrollHeight - rd.clientHeight;
        if (max <= 0) return;
        S.pos[CUR.id] = Math.min(1, Math.max(0, rd.scrollTop / max));
        // 读完（滚到底部 95%）自动标记已读
        if (S.pos[CUR.id] > 0.95 && !S.done[CUR.id]) {
          S.done[CUR.id] = 1;
          renderList();
        }
        save();
      }, 400);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if ($('mask').classList.contains('on')) closeWord();
        else if ($('wbPage').classList.contains('on')) closeWB();
        else if ($('side').classList.contains('on')) closeDrawer();
      }
    });

    window.addEventListener('resize', applyFont);
  }

  // ---------- 启动 ----------
  function boot() {
    load();
    renderChips();
    bind();
    applyFont();

    var jobs = [
      getJSON('data/passages.json').then(function (d) {
        DATA = d;
        DATA.passages = d.passages || [];
      }),
      getJSON('data/dict.json').then(function (d) {
        window.Dict.setDB(d);
      }).catch(function () {
        console.warn('dict.json 未加载，查词将不可用');
      }),
      getJSON('data/config.json').then(function (c) {
        window.Dict.setConfig(c);
      }).catch(function () {
        window.Dict.setConfig({ enableOnline: false, onlineEndpoint: '' });
      })
    ];

    Promise.all(jobs).then(function () {
      renderList();
      renderWBBadge();
      var hash = (location.hash || '').replace('#', '');
      var first = DATA.passages[0];
      if (hash === 'wb') { openWB(); openPassage((S.last || (first && first.id)), true); }
      else if (hash && DATA.passages.some(function (p) { return p.id === hash; })) openPassage(hash);
      else if (S.last && DATA.passages.some(function (p) { return p.id === S.last; })) openPassage(S.last);
      else if (first) openPassage(first.id);
    }).catch(function (err) {
      $('rwrap').innerHTML = '<div class="empty">数据加载失败：' + esc(err.message) +
        '<br><span style="font-size:12.5px">请通过 http(s) 访问（不要双击 index.html 直接打开）</span></div>';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();

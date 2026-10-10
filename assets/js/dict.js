/* 词典模块：离线词库优先 + 词形还原 + 在线兜底 + 发音
 * 数据：data/dict.json  {word: {us, uk, d}}
 */
(function (global) {
  'use strict';

  var DB = {};        // 离线词库
  var CONFIG = {};    // 配置（在线兜底）
  var ready = false;

  // ---------- 不规则变化 ----------
  var IRREG = {
    am: 'be', is: 'be', are: 'be', was: 'be', were: 'be', been: 'be', being: 'be',
    has: 'have', had: 'have', having: 'have', does: 'do', did: 'do', done: 'do', doing: 'do',
    went: 'go', gone: 'go', goes: 'go', made: 'make', said: 'say', saw: 'see', seen: 'see',
    took: 'take', taken: 'take', came: 'come', got: 'get', gotten: 'get', knew: 'know', known: 'know',
    thought: 'think', found: 'find', gave: 'give', given: 'give', told: 'tell', became: 'become',
    left: 'leave', felt: 'feel', kept: 'keep', held: 'hold', wrote: 'write', written: 'write',
    stood: 'stand', understood: 'understand', began: 'begin', begun: 'begin', ran: 'run',
    brought: 'bring', bought: 'buy', taught: 'teach', caught: 'catch', spoke: 'speak', spoken: 'speak',
    broke: 'break', broken: 'break', chose: 'choose', chosen: 'choose', drove: 'drive', driven: 'drive',
    ate: 'eat', eaten: 'eat', fell: 'fall', fallen: 'fall', flew: 'fly', flown: 'fly',
    forgot: 'forget', forgotten: 'forget', grew: 'grow', grown: 'grow', hid: 'hide', lay: 'lie',
    lost: 'lose', meant: 'mean', met: 'meet', paid: 'pay', read: 'read', rode: 'ride',
    rang: 'ring', rose: 'rise', risen: 'rise', sang: 'sing', sank: 'sink', sat: 'sit',
    slept: 'sleep', spent: 'spend', spread: 'spread', threw: 'throw', thrown: 'throw',
    wore: 'wear', worn: 'wear', won: 'win', wound: 'wind',
    children: 'child', people: 'person', men: 'man', women: 'woman', feet: 'foot', teeth: 'tooth',
    geese: 'goose', mice: 'mouse', oxen: 'ox', lives: 'life', wives: 'wife', knives: 'knife',
    leaves: 'leaf', halves: 'half', selves: 'self', wolves: 'wolf', shelves: 'shelf',
    better: 'good', best: 'good', worse: 'bad', worst: 'bad', further: 'far', furthest: 'far',
    more: 'many', most: 'many', less: 'little', least: 'little',
    myself: 'I', himself: 'he', herself: 'she', itself: 'it', themselves: 'they', ourselves: 'we'
  };

  var VOWEL = 'aeiou';

  function isVowel(ch) { return VOWEL.indexOf(ch) >= 0; }

  /** 生成词形还原候选（按可能性排序，含原形） */
  function candidates(raw) {
    var w = String(raw || '').toLowerCase().replace(/[^a-z'-]/g, '');
    if (!w) return [];
    var out = [w], seen = {};
    seen[w] = 1;
    function add(x) {
      if (x && x.length > 1 && !seen[x]) { seen[x] = 1; out.push(x); }
    }
    if (IRREG[w]) add(IRREG[w]);

    // 复数 / 第三人称
    if (/ies$/.test(w)) { add(w.slice(0, -3) + 'y'); }
    if (/(ches|shes|sses|xes|zes)$/.test(w)) { add(w.slice(0, -2)); }
    if (/ves$/.test(w)) { add(w.slice(0, -3) + 'f'); add(w.slice(0, -3) + 'fe'); }
    if (/s$/.test(w) && !/ss$/.test(w)) {
      add(w.slice(0, -1));
      if (/oes$/.test(w)) add(w.slice(0, -2));
    }
    // 过去式 / 分词
    if (/ied$/.test(w)) add(w.slice(0, -3) + 'y');
    if (/ed$/.test(w)) {
      add(w.slice(0, -2));
      add(w.slice(0, -1));                       // liked → like
      var st = w.slice(0, -2);
      // 双写辅音还原 stopped → stop
      if (st.length > 2 && st[st.length - 1] === st[st.length - 2] &&
        !isVowel(st[st.length - 1]) && st[st.length - 1] !== 'l') {
        add(st.slice(0, -1));
      }
    }
    // -ing
    if (/ing$/.test(w)) {
      var s2 = w.slice(0, -3);
      add(s2); add(s2 + 'e');                    // making → make
      if (s2.length > 2 && s2[s2.length - 1] === s2[s2.length - 2] &&
        !isVowel(s2[s2.length - 1])) {
        add(s2.slice(0, -1));                    // running → run
      }
    }
    // 副词 / 比较级
    if (/ally$/.test(w)) add(w.slice(0, -4) + 'al');
    if (/ly$/.test(w)) { add(w.slice(0, -2)); add(w.slice(0, -2) + 'e'); }
    if (/(er|est)$/.test(w)) {
      var s3 = w.slice(0, w.length - (/est$/.test(w) ? 3 : 2));
      add(s3); add(s3 + 'e');
      if (s3.length > 2 && s3[s3.length - 1] === s3[s3.length - 2] && !isVowel(s3[s3.length - 1])) {
        add(s3.slice(0, -1));
      }
      if (/ier$/.test(w) || /iest$/.test(w)) add(w.slice(0, -3) + 'y');
    }
    // 名词化 / 派生
    if (/tion$/.test(w)) { add(w.slice(0, -3) + 'te'); add(w.slice(0, -4)); }
    if (/ment$/.test(w)) add(w.slice(0, -4));
    if (/ness$/.test(w)) add(w.slice(0, -4));
    if (/ful$/.test(w)) add(w.slice(0, -3));
    if (/able$/.test(w)) { add(w.slice(0, -4)); add(w.slice(0, -4) + 'e'); }
    if (/ive$/.test(w)) { add(w.slice(0, -3)); add(w.slice(0, -3) + 'e'); }
    if (/(un|dis|im|in|ir)$/.test(w)) add(w.slice(0, -2));
    if (/^un/.test(w)) add(w.slice(2));
    if (/^dis/.test(w)) add(w.slice(3));
    if (/^im/.test(w)) add(w.slice(2));
    if (/^in/.test(w)) add(w.slice(2));
    return out;
  }

  /** 本地查询，返回 {word, us, uk, d, base} 或 null */
  function lookup(raw) {
    var cs = candidates(raw);
    for (var i = 0; i < cs.length; i++) {
      if (DB[cs[i]]) {
        var e = DB[cs[i]];
        return {
          word: String(raw).toLowerCase(),
          base: cs[i],
          us: e.us || '', uk: e.uk || '',
          d: e.d || '',
          fromBase: cs[i] !== String(raw).toLowerCase()
        };
      }
    }
    return null;
  }

  /** 在线兜底（需配置代理，默认关闭） */
  function lookupOnline(word, cb) {
    var ep = CONFIG.onlineEndpoint;
    if (!CONFIG.enableOnline || !ep) { cb(null); return; }
    var url = ep.replace('{w}', encodeURIComponent(word));
    var t = setTimeout(function () { cb(null); }, 6000);
    fetch(url).then(function (r) { return r.json(); }).then(function (j) {
      clearTimeout(t);
      cb(j && (j.d || j.definition) ? {
        word: word, base: word,
        us: j.us || j.usphone || '', uk: j.uk || j.ukphone || '',
        d: j.d || j.definition || ''
      } : null);
    }).catch(function () { clearTimeout(t); cb(null); });
  }

  /** 发音：有道 dictvoice。type 1=英音 2=美音 */
  function audioUrl(word, type) {
    return 'https://dict.youdao.com/dictvoice?audio=' + encodeURIComponent(word) +
      '&type=' + (type === 1 ? 1 : 2);
  }

  var AUDIO = null;
  function speak(word, type, onEnd) {
    try {
      if (AUDIO) { AUDIO.pause(); AUDIO = null; }
      var a = new Audio(audioUrl(word, type));
      AUDIO = a;
      a.onended = a.onerror = function () { if (onEnd) onEnd(); };
      a.play().catch(function () { if (onEnd) onEnd(); });
      return a;
    } catch (e) { if (onEnd) onEnd(); return null; }
  }

  global.Dict = {
    setDB: function (d) { DB = d || {}; ready = true; },
    setConfig: function (c) { CONFIG = c || {}; },
    isReady: function () { return ready; },
    size: function () { return Object.keys(DB).length; },
    candidates: candidates,
    lookup: lookup,
    lookupOnline: lookupOnline,
    audioUrl: audioUrl,
    speak: speak,
    /** 把释义按词性切成 [{pos, def}] */
    parseDef: function (d) {
      if (!d) return [];
      var parts = String(d).split(/；(?=[a-z]{1,5}\.\s)/);
      var out = [];
      parts.forEach(function (p) {
        p = p.trim(); if (!p) return;
        var m = p.match(/^([a-z]{1,5}\.)\s*(.*)$/i);
        if (m) out.push({ pos: m[1], def: m[2] });
        else if (out.length) out[out.length - 1].def += '；' + p;
        else out.push({ pos: '', def: p });
      });
      return out.length ? out : [{ pos: '', def: d }];
    }
  };
})(window);

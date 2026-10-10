/* 冒烟测试（仅开发用，部署可删）：用 jsdom 跑一遍 index.html，验证渲染与交互
 * 运行：先起静态服务 python -m http.server 8123
 *       node tools/smoke_test.js
 */
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require(process.env.JSDOM_PATH ||
  'C:/Users/taozhenlong/.workbuddy/binaries/node/workspace/node_modules/jsdom');

const BASE = 'http://127.0.0.1:8123/';
const ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

const vc = new VirtualConsole();
const errs = [];
vc.on('jsdomError', e => errs.push('jsdomError: ' + e.message));
vc.on('error', (...a) => errs.push('console.error: ' + a.join(' ')));
vc.on('warn', (...a) => errs.push('console.warn: ' + a.join(' ')));

const dom = new JSDOM(html, {
  url: BASE,
  runScripts: 'dangerously',
  resources: 'usable',
  pretendToBeVisual: true,
  virtualConsole: vc,
  beforeParse(win) {
    win.fetch = (u, o) => fetch(new URL(u, BASE).href, o);
    win.Audio = function () { return { play: () => Promise.resolve(), pause() { } }; };
  }
});

const win = dom.window, doc = win.document;

function q(sel) { return doc.querySelector(sel); }
function qa(sel) { return Array.from(doc.querySelectorAll(sel)); }
const results = [];
function ck(name, cond, extra) {
  results.push((cond ? '✅' : '❌') + ' ' + name + (extra ? '  → ' + extra : ''));
}

(async () => {
  // 等待 boot 完成
  for (let i = 0; i < 60; i++) {
    if (qa('#plist .pitem').length) break;
    await new Promise(r => setTimeout(r, 200));
  }

  const items = qa('#plist .pitem');
  ck('篇目列表渲染', items.length === 75, items.length + ' 篇');
  ck('档位分组', qa('#plist .pgroup').length === 5, qa('#plist .pgroup').length + ' 组');
  ck('默认打开首篇', !!q('.rhead h1'), q('.rhead h1') && q('.rhead h1').textContent);
  ck('双语对照模式', qa('#rwrap .bi').length > 0, qa('#rwrap .bi').length + ' 段');
  ck('单词可点（已 tokenize）', qa('#rwrap .w').length > 50, qa('#rwrap .w').length + ' 个词');
  ck('词库加载', win.Dict && win.Dict.size() > 3000, win.Dict ? win.Dict.size() + ' 条' : 'Dict 未定义');

  // 点词
  const w = qa('#rwrap .w')[3];
  const wordText = w.getAttribute('data-w');
  w.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('点击单词弹出弹窗', q('#mask').classList.contains('on'), '词=' + wordText + ' 显示=' + q('#pWord').textContent);
  ck('弹窗含音标', /\/|\(|美|英/.test(q('#pPhn').textContent) || q('#pPhn').textContent.length > 0, q('#pPhn').textContent.slice(0, 40));
  ck('弹窗含释义', q('#pDef').textContent.length > 5, q('#pDef').textContent.slice(0, 60));
  ck('弹窗含例句', q('#pCtx').textContent.indexOf('例句') === 0, q('#pCtx').textContent.slice(0, 50));

  // 加入生词本
  q('#pAdd').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('加入生词本', q('#wbBadge').textContent === '1', 'badge=' + q('#wbBadge').textContent);
  ck('按钮变已加入', q('#pAdd').classList.contains('in'), q('#pAdd').textContent);
  ck('原文词被金色标记', qa('#rwrap .w.marked').length > 0, qa('#rwrap .w.marked').length + ' 个');
  ck('localStorage 持久化', JSON.parse(win.localStorage.getItem('xiemo-reader-v1')).wb.length === 1);

  q('#pClose').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('关闭弹窗', !q('#mask').classList.contains('on'));

  // 生词本页
  q('#btnWb').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('生词本页打开', q('#wbPage').classList.contains('on'));
  ck('生词本卡片', qa('#wbList .wbcard').length === 1, qa('#wbList .wbcard').length + ' 张');
  ck('生词本含释义', q('#wbList .d').textContent.length > 3, q('#wbList .d').textContent.slice(0, 50));
  q('#wbHide').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 30));
  ck('遮住释义', q('#wbList .d').classList.contains('hide'));
  q('#wbBack').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 30));
  ck('返回阅读页', !q('#wbPage').classList.contains('on'));

  // 切换模式
  q('#seg button[data-m="en"]').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('切仅英文', qa('#rwrap .enp').length > 0 && qa('#rwrap .bi').length === 0, qa('#rwrap .enp').length + ' 段');
  q('#seg button[data-m="zh"]').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('切仅中文', qa('#rwrap .zhp').length > 0 && qa('#rwrap .enp').length === 0, qa('#rwrap .zhp').length + ' 段');
  q('#seg button[data-m="bi"]').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));

  // 标记已读
  q('#btnDone').dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('标记已读', JSON.parse(win.localStorage.getItem('xiemo-reader-v1')).done['Y01'] === 1, q('#cntDone').textContent);

  // 搜索
  const inp = q('#q');
  inp.value = '胡萝卜';
  inp.dispatchEvent(new win.Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('搜索过滤', qa('#plist .pitem').length > 0 && qa('#plist .pitem').length < 75, qa('#plist .pitem').length + ' 命中');
  inp.value = '';
  inp.dispatchEvent(new win.Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));

  // 档位筛选
  qa('#chips .chip').find(c => c.getAttribute('data-f') === 'A')
    .dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ck('A 档筛选 = 6 篇', qa('#plist .pitem').length === 6, qa('#plist .pitem').length + ' 篇');

  // 切换篇目
  qa('#plist .pitem')[1].dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 80));
  ck('切换篇目', q('.rhead h1').textContent.length > 0, q('.rhead h1').textContent);
  ck('上下篇导航存在', qa('#rwrap .pnav button').length === 2);
  ck('主题头图渲染', !!q('.hero img') && q('.hero img').getAttribute('src').indexOf('.svg') > 0,
    q('.hero img') && q('.hero img').getAttribute('src'));
  ck('学习进度条存在', !!q('#pbarFill') && /%\s*$/.test(q('#cntDone').textContent),
    q('#cntDone').textContent);
  ck('阅读位置已存入进度', typeof JSON.parse(win.localStorage.getItem('xiemo-reader-v1')).pos === 'object');

  console.log(results.join('\n'));
  console.log('\n控制台错误：' + (errs.length ? '\n' + errs.join('\n') : '无'));
  const bad = results.filter(r => r[0] === '❌').length;
  console.log('\n结果：' + (results.length - bad) + ' 通过 / ' + bad + ' 失败');
  process.exit(bad || errs.length ? 1 : 0);
})();

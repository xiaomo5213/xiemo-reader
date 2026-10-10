# 撷墨 · 押题库短文精读

自考英语（专升本，课程代码 **13000**）备考用的**短文精读应用**。
75 篇原文 + 全译文，**点任意单词查音标/词性/释义、发音、一键进生词本**，生词本独立页面。

- 纯静态：**HTML + 原生 JS + CSS**，无框架、无构建、无依赖
- **数据与代码分离**：所有内容在 `data/` 下，改数据不用动代码
- PC / 手机 / 微信内置浏览器 三端自适应
- 可直接 push 到 **GitHub Pages / 宝塔 / Vercel / 任意静态空间**

---

## 一、目录结构

```
xiemo-reader/
├── index.html                 # 应用主页面（唯一入口）
├── assets/
│   ├── css/app.css            # 样式（薄荷绿主题 + 响应式）
│   ├── img/                   # ★ 75 张主题插图（每篇一张 SVG，共约 350 KB）
│   └── js/
│       ├── dict.js            # 词典模块：离线词库 + 词形还原 + 发音
│       └── app.js             # 主逻辑：渲染 / 交互 / 生词本 / 本地存储
├── data/                      # ★ 数据层（与代码完全分离）
│   ├── passages.json          # 75 篇短文（原文 + 译文 + 真题命中 + 档位）
│   ├── dict.json              # 离线词库（有道词典抓取，约 3.8k 词条）
│   └── config.json            # 可选配置（在线兜底查词开关，默认关闭）
└── tools/                     # 数据生产脚本（只在电脑上跑，不上传也能用）
    ├── extract_official.py    # 官方教材 HTML(课文+翻译+词表) → data/official.json
    ├── extract_passages.py    # PDF 文本 → passages.json
    ├── fetch_dict.py          # 有道词典 → dict.json
    ├── gen_illustrations.py   # 按篇目主题批量生成 SVG 插图
    └── smoke_test.js          # 本机冒烟测试（jsdom，可选）
```

## 二、本地预览（必须走 http，不要双击 index.html）

```bash
cd xiemo-reader
python -m http.server 8080
# 浏览器打开 http://localhost:8080
```

> 直接双击打开（`file://`）会因浏览器安全策略无法读取 `data/*.json`，页面会提示"数据加载失败"。

## 三、功能说明

| 功能 | 说明 |
|---|---|
| 主题插图 | 每篇按文章主题生成一张 16:9 扁平矢量插画（`assets/img/<id>.svg`），显示在标题卡下方；75 张仅约 350 KB，手机端秒开 |
| 篇目列表 | 75 篇按 **A/B/C/D/E 档位**分组（A 档=真题高频必背），显示真题命中记录（如 `25.4 填词`） |
| 搜索 / 筛选 | 按篇号、主题、标题、正文关键词搜索；按档位 / "未读" 筛选 |
| 三种显示模式 | 仅英文 / **双语对照**（逐段对照，默认）/ 仅中文 |
| 一段一译 | 英文第 n 段 ↔ 中文第 n 段**严格一一对应**，段首带序号徽标、译文带「译」标签，永不串行 |
| 点词查义 | 点击任意单词弹出：单词 + 英美音标 + 词性+释义 + 所在例句 |
| 发音 | 英音 / 美音（有道 `dictvoice` 直连）；全文朗读（逐句） |
| 生词本 | 独立全屏页；金色下划线标记已收藏词；**遮住释义**做默写；导出 CSV |
| 学习进度 | **每篇阅读位置自动保存**，重新打开自动恢复到上次读到的地方；滚到篇尾 95% 自动标记已读；侧栏顶部**进度条 + 百分比**（已读 n / 75） |
| 字号调节 | A－ / A＋，记忆偏好 |
| 数据存储 | localStorage（键 `xiemo-reader-v1`），换设备不同步 |

### 段落与译文如何保证一一对应

**补充版 24 篇以「官方教材网页版（课文+单词）」HTML 为准**（`tools/extract_official.py` 解析 1A~12B.html）：
英文段落与中文翻译直接取自教材原文件的 `.article` / `.translation`，分段权威；官方缺篇才回退 PDF 解析。
译文中英交界自动补空格（`的Ask` → `的 Ask`、`kick球` → `kick 球`）。

押题库 51 篇仍从 PDF 文本提取。教材 PDF 里英文段落和参考译文的分段习惯并不一致，
直接按段数配对必然错位，`tools/extract_passages.py` 的做法是：

1. **只保留课文正文**：`Directions:` 之后的内容、题号、选项、`【答案解析】`、`答案为/译为/由此可知` 等解析文字一律丢弃；正文里插入的题号标记（如 `... off. (3)I needed`）也清除。
2. **英文保留原段落**，仅当整篇连排成一段且超过 600 字符时，按句子切成阅读块。
3. **中文不再信任原分段**：先把全部译文切成句子流，再与英文句做**动态规划句对齐**（允许 1:1 / 1:2 / 1:3 / 1:4 / 2:1 / 3:1 / 4:1 对应，代价 = 等效长度差，英文按 5.5 字符 ≈ 1 汉字折算），最后按英文段落覆盖的句子范围合并回段落。
4. 相邻段若因多句共用而重叠，自动去重；DP 无解时退回**长度比例切分**兜底。

自检结果：75 篇共 376 段，`len(en) == len(zh)` 全部成立，无空译文段，无试题/解析残留。

### 词形还原
离线词库只收原形。点击 `words` / `making` / `better` 这类变形词时，`dict.js` 会做不规则表 + 规则后缀还原（`ies→y`、`ves→f/fe`、`ed/ing` 双写还原、`er/est`、`ly`、`tion`、`un-/dis-/im-` 等），自动命中 `word` / `make` / `good`，并标注"（原形 xxx）"。

## 四、部署

### GitHub Pages
```bash
git init && git add . && git commit -m "押题库短文精读"
git remote add origin git@github.com:<你的账号>/xiemo-reader.git
git push -u origin main
```
仓库 Settings → Pages → Source 选 `main` / `/(root)`，几分钟后即可访问。

### 宝塔 / 自有服务器
把整个目录上传到站点根目录，Nginx 无需特殊配置（纯静态）。建议开启 HTTPS（发音接口为 https，http 页面下部分浏览器会拦截）。

### 微信内访问
直接把网址发到聊天/收藏即可打开；也可放到公众号菜单或小程序 `web-view`（业务域名需在公众号后台配置为 JS 接口安全域名 / 小程序业务域名）。

## 五、更新数据

```bash
# 1）重新从 PDF 文本提取短文（会把 pdf_txt 下两个 txt 解析成 data/passages.json）
python tools/extract_passages.py

# 2）补全/更新离线词库（增量，已有词条跳过；--all 强制重抓）
python tools/fetch_dict.py

# 3）重新生成主题插图（默认全部 75 篇；也可指定篇目只重画某几张）
python tools/gen_illustrations.py            # 全部
python tools/gen_illustrations.py Y01 B九B   # 只画指定篇目
```
插图规则：每篇在 `tools/gen_illustrations.py` 的 `MAP` 里配置「场景模板 + 调色板 + 变体」，35 个场景 × 5 套薄荷绿系调色板组合生成，改配置重跑即可换风格。

`data/passages.json` 结构：

```json
{
  "meta": {"course":"英语（专升本）","code":"13000","count":75},
  "passages": [{
    "id": "Y01", "book": "yatiku", "no": 1, "page": "111",
    "title": "", "topic": "语言的力量", "level": "A",
    "hits": [{"y":"2025","m":"4","type":"填词补文","prov":"重庆"}],
    "en": ["Language is one of the things ..."],
    "zh": ["语言是使我们成为人类的 ..."]
  }]
}
```

- `level`：`A` 必背 / `B` 重点 / `C` 常考 / `D` 补充版 / `E` 泛读
- `book`：`yatiku`（押题库 51 篇）/ `buchong`（补充版 24 篇）

## 六、自检（可选）

```bash
python -m http.server 8123          # 另开一个终端
node tools/smoke_test.js            # 需 node + jsdom，30 项检查
```
覆盖：75 篇渲染、档位分组、点词弹窗（音标/释义/例句）、加入生词本、金色标记、localStorage 持久化、生词本页（遮释义/返回）、三种显示模式、标记已读、搜索、档位筛选、切换篇目。

## 七、已知说明

- **离线优先**：词库内置在 `data/dict.json`，断网也能查词；发音需要联网。
- **在线兜底**：默认关闭。如需开启，编辑 `data/config.json`，`enableOnline: true` 并填写一个返回 JSON 的代理地址（`{w}` 会被替换为单词），因为浏览器同源策略无法直接请求有道接口。
- 词库未收录的词会提示"暂未收录"，仍可发音和加入生词本。

---

闽ICP备19027462号-2 · 厦门撷墨教育

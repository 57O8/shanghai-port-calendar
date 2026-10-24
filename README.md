# ⚽ 上海海港赛程自动同步日历 (iCalendar)

利用 GitHub Pages 免费托管 `.ics` 日历文件，在 iPhone / Outlook 上自动同步上海海港（**一线队 + 梯队**）的赛程。
**中超与中乙全自动抓取，亚冠与足协杯手工维护 + 官方赛程图自动监控 + 核对面板 30 秒校验**，改完即同步，几乎零维护。

---

## 一、数据源说明（重要）

各赛事的数据来源与自动化程度（均为 2026-10 实测结论）：

| 赛事 | 自动/手工 | 数据来源 |
|------|----------|----------|
| 中超 (CSL) | ✅ 自动 | 中足联官方接口 `api.cfl-china.cn`（一线队） |
| 中乙 (CL2) | ✅ 自动 | 中足联官方接口（**梯队：上海海港富盛经开队**） |
| 亚冠 | 🖼️ 手工 + 官方图自动监控 | 海港官网官方赛程图，数据写入 `data/manual_matches.json` |
| 足协杯 | 🖼️ 手工 + 官方图自动监控 | 海港官网官方赛程图 + 中国足协杯官方微博口径 |

**关键事实（踩坑记录）：**

1. 中足联只发布国内联赛（中超/中甲/中乙/U21），**亚冠、足协杯不在其中**。
2. 亚冠、中超、足协杯的「官方口径」由**上海海港官网**以**图片**形式发布：
   `https://www.fcshanghaiport.com/battle` 页面右侧的
   `saicheng_afc`（亚冠）/ `saicheng_csl`（中超）/ `saicheng_cfa`（足协杯）三张 JPG。
   （下载需带 `Referer` 防盗链头，图片文件名为中文需 URL 编码。）
3. 海港官网月度日历是 WordPress + `admin-ajax.php` 动态加载，**无法静态抓取**。
4. Transfermarkt 有强反爬（405/Cloudflare），**只适合人工交叉验证，不能自动化**。
5. **亚足联官网 the-afc.com** 的亚冠 fixtures 页（`/en/club/afc_champions_league_elite/fixtures__standings.html`）
   是 Nuxt SPA，**赛程靠 JS 客户端异步加载**，静态 HTML 无数据；其底层数据接口（CMS 赛程接口 /
   opta-gracenote 路由）要么竞赛编码不可推断（实测 15+ 组合全部 404 / No query results），
   要么返回结构极稀疏（仅 teamId + 比分，无赛事字段、无队名，team 详情接口 404）。
   **因此该源不适合自动化抓取**，定位为亚冠的人工交叉验证书签。

**交叉验证渠道（人工）：** 懂球帝、微博 `@中国足协杯`、小红书、抖音、Transfermarkt
（上海海港球队页：verein/27190）、**亚足联官网 the-afc.com 亚冠 fixtures 页**（权威口径）。

---

## 二、仓库文件结构

```
shanghai-port-calendar/
├── .github/workflows/update.yml   # 自动化：定时/手动触发，抓数→生成→部署
├── scripts/
│   ├── fetch_cfl.py               # 抓取 中超+中乙 + 监控海港官网官方赛程图
│   ├── generate_ics.py            # 合并 自动+手工 数据，生成 output/shanghai_port.ics
│   └── build_review.py            # 生成人工核对面板 output/review.html（左图右表）
├── data/
│   ├── auto_matches.json          # 自动生成的缓存（会自动提交回仓库，作容错备份）
│   └── manual_matches.json        # 手工维护：亚冠 + 足协杯
├── official/schedules/            # 官方赛程图自动存档（afc/csl/cfa.jpg）
│   └── UPDATE_NOTICE.md           # ⚠️ 官方图更新时自动生成的提醒（处理后可删）
├── output/
│   ├── shanghai_port.ics          # 最终订阅文件（由 Actions 部署到 gh-pages）
│   ├── review.html                # 核对面板（部署后可直接访问）
│   └── images/                    # 核对面板引用的官方图副本
└── README.md
```

---

## 三、搭建步骤（一次性）

1. 注册并登录 [GitHub](https://github.com/)。
2. 新建仓库 `shanghai-port-calendar`，**勾选 Public**（必须公开才能订阅）。
3. 把本仓库里的以下文件原样上传（可直接拖拽或 Add file）：
   - `.github/workflows/update.yml`
   - `scripts/fetch_cfl.py`
   - `scripts/generate_ics.py`
   - `scripts/build_review.py`
   - `data/manual_matches.json`
   - `official/schedules/` 整个目录（含三张官方图与 `state.json`，防止首轮误报）
   - `.gitignore`
   - （`data/auto_matches.json` 与 `output/` 首次运行后会自动生成，无需提前建）
4. 开启自动化：
   - 进入仓库 **Actions** 标签 → 若提示则点 **I understand…** → 左侧 **Update ICS** → **Run workflow** 手动跑一次。
   - 等待约 1 分钟，看到绿色 ✅ 即成功，并自动生成 `gh-pages` 分支与 `data/auto_matches.json`。
5. 开启托管：
   - **Settings → Pages → Source** 选 `Deploy from a branch`；
   - **Branch** 选 `gh-pages`，目录 `/ (root)`；点 **Save**。
   - 1–2 分钟后顶部会显示你的专属网址。

---

## 四、订阅日历

把下面链接里的 `你的用户名` 换成你的 GitHub 用户名：

```
https://你的用户名.github.io/shanghai-port-calendar/shanghai_port.ics
```

- **iPhone / iPad**：把链接复制到 Safari，将 `https://` 改成 `webcal://` 访问即可订阅；
  或 `设置 → 日历 → 账户 → 添加账户 → 其他 → 添加已订阅的日历` 粘贴链接。
- **Outlook**：`添加日历 → 从 Internet 订阅`，粘贴链接。

---

## 五、全自动是怎么运作的

`update.yml` 在以下时机自动运行：

- **每天北京时间 06:00**（cron `0 22 * * *` UTC）自动跑一次；
- 你 **push 到 main 分支**（例如改了手工数据）时自动跑；
- 也可在 Actions 页面 **手动 Run workflow**。

每次运行：

1. `fetch_cfl.py` 抓最新中超/中乙 → 写 `data/auto_matches.json` 并自动提交回仓库（容错缓存）；
2. 同一脚本解析海港官网三张**官方赛程图**的 URL 并下载存档到 `official/schedules/`；
   **一旦发现俱乐部更新了官方图**，自动生成 `official/schedules/UPDATE_NOTICE.md`，
   且提交信息会带上 `[!] 官方赛程图已更新` 标记；
3. `generate_ics.py` 合并手工数据生成 `.ics`；
4. `build_review.py` 生成**核对面板** `output/review.html`（左官方图 / 右当前数据表）；
5. 上述产物一起部署到 `gh-pages`。

**容错**：中足联接口或官网任一环节临时不可达时，仅告警并复用上次缓存，日历不会断更。

---

## 六、日后维护

- **中超 / 中乙（含梯队）**：完全不用管，官方一出赛程自动同步。
- **亚冠 / 足协杯**：
  - 官方赛程图更新时，Actions 提交信息会出现 `[!] 官方赛程图已更新`，且仓库出现
    `official/schedules/UPDATE_NOTICE.md`——此时**打开核对面板**（见下节）逐行扫一遍，
    有差异就改 `data/manual_matches.json`（用 `{}` 包裹、逗号隔开）。
  - 拿不准时用懂球帝 / 微博 `@中国足协杯` / Transfermarkt / **亚足联官网 the-afc.com 亚冠 fixtures 页** 交叉验证。
  - 提交后 Actions 自动重新生成并同步。
- 订阅端（iPhone/Outlook）会自动拉取更新，无需重新订阅。

> 已用官方口径校准过的记录（2026-10-24）：足协杯 7/21 vs 深圳新鹏城开球 **19:00**
> （非 19:35）；足协杯半决赛 **11/20（周五）19:35 北京国安 vs 上海海港 @ 北京工人体育场**
> （足协官网 7 月新闻的「11/21–22」为原定窗口，10/08 官方微博已确认为 11/20）。

---

## 七、快速人工核对流程（30 秒版）

> 只有**亚冠、足协杯**需要人工核对（中超/中乙全自动）。全年合计约 12 场，实际动手 < 10 分钟。

**核对面板地址（部署后可用，建议存为书签）：**

```
https://<你的用户名>.github.io/shanghai-port-calendar/review.html
```

面板**左侧是官方赛程图**（俱乐部发布），**右侧是日历当前采用的亚冠/足协杯数据表**，按日期排序、待赛场次红色标记、已赛灰显。三步扫完：

1. **看图**：在官方图上找到「上海海港」的场次。
2. **对表**：逐行核对 **日期 / 时间 / 主客 / 场地**，重点看红字「待赛」行。
3. **改**：有差异就点面板底部「编辑 manual_matches.json」（直接跳 GitHub 编辑页），改完提交，Actions 自动重建日历。

**触发时机（任一即可）：**
- 收到 `[!] 官方赛程图已更新` 的提交通知，或仓库出现 `official/schedules/UPDATE_NOTICE.md`；
- 或固定习惯：**每月看一眼面板**（2 分钟，最省心）。

**核对顺序（先粗后细，最快）：**
1. **先数场次**：官方图上有几场海港 vs 表里有几场 → 数量不符说明有漏/多；
2. **再对最近一场**：下一场比赛的日期/时间/主客场最容易记错；
3. **最后扫历史**：已赛场次基本不会再变，快速掠过。

---

## 八、架构决策记录（ADR）

记录"为什么这样做"，避免日后重复调研或误改。

### ADR-1：亚冠/足协杯不做 OCR 全自动，改为"官方图自动监控 + 人工 30 秒核对"

- **背景**：亚冠、足协杯不在中足联接口内，俱乐部以**图片**形式发布官方赛程表；曾评估用 OCR 把图片转成结构化数据。
- **决策**：**不**做 OCR 全自动；保留人工核对，但用核对面板把成本压到 30 秒。
- **理由**：
  1. **容错极低**——赛程漏一场或错半小时，日历里就是真实错误；OCR 即便 95% 字符准确率，也可能恰好错在关键的时间/队名上。
  2. **版式脆弱**——俱乐部改一次图排版，解析逻辑就崩，等于埋一个不定时故障源，违背"免维护"初衷。
  3. **ROI 不划算**——全年只需核对约 12 场，每场 30 秒；而 OCR 要引入较重依赖（PaddleOCR/EasyOCR）并持续维护解析逻辑。
- **保留的替代方案**：若日后确实想减少人工，正确姿势是 **OCR 只生成"草稿" + 自动 diff 提示**，仍由人确认，绝不让 OCR 结果直接进日历。

### ADR-2：不引入"外部定时任务 + 网络中转存储"，直接用 GitHub Actions

- **背景**：曾设想用本地/服务器定时任务生成赛程，存到一个网络位置，再让 GitHub 去取。
- **决策**：**不引入**外部定时任务，维持 GitHub Actions 单一链路。
- **理由**：GitHub Actions 本身就是**托管定时任务**（`cron`）+ **网络存储**（`gh-pages` / Pages），7×24 运行、不依赖本地开机。再套一层外部服务器 = 多一跳、多一份运维，自动化程度却没变。
- **唯一起作用的例外**：抓取需要 Actions 做不到的能力（真实浏览器渲染反爬 SPA、登录态/Cookie、GPU 大模型）。本项目的中超/中乙是普通 API、官方图是静态下载，均不构成刚需。

### ADR-3：the-afc.com 不作为自动源，仅作人工交叉验证书签

- **背景**：亚足联官网是亚冠权威源，曾尝试自动化抓取。
- **决策**：**不**做自动抓取，列入人工交叉验证渠道。
- **理由**：该站 fixtures 页为 Nuxt SPA，数据靠 JS 异步加载；底层 CMS 赛程接口的竞赛编码无法公开推断（实测 15+ 组合全部 404 / No query results），opta-gracenote 路由前缀不稳定（全 404），唯一跑通的按日接口又极度稀疏（仅 teamId + 比分，无赛事字段、无队名）。硬写爬虫 = 脆弱故障源。

---

## 九、本地调试

```bash
python scripts/fetch_cfl.py      # 抓取并写 data/auto_matches.json + 下载官方赛程图
python scripts/generate_ics.py   # 生成 output/shanghai_port.ics
python scripts/build_review.py   # 生成 output/review.html 核对面板（本地直接双击预览）
```

> 需要 Python 3.10+（用到 `zoneinfo` 与时区数据；GitHub Actions 的 Ubuntu 自带，本机 Windows 需 `pip install tzdata`）。

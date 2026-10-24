#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成人工核对面板 output/review.html。

把「海港官网发布的官方赛程图」与「data/manual_matches.json 中的亚冠/足协杯数据」
并排展示，供官方图更新时快速核对；同时把官方图复制到 output/images/，
随 gh-pages 一起发布，因此页面不依赖任何外部资源。

部署后访问：https://<用户名>.github.io/<仓库名>/review.html
"""
import json
import os
import shutil
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL_FILE = os.path.join(BASE_DIR, "data", "manual_matches.json")
OFFICIAL_DIR = os.path.join(BASE_DIR, "official", "schedules")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "review.html")
INDEX_FILE = os.path.join(OUTPUT_DIR, "index.html")

# 需要人工核对的赛事 -> 官方图代号
REVIEW_COMPS = [("亚冠", "afc"), ("足协杯", "cfa")]

# Actions 中自动注入；本地运行时为空，则隐藏"编辑"按钮
REPO = os.environ.get("GITHUB_REPOSITORY", "").strip()

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--line:#e5e7eb;--txt:#1f2328;--muted:#6b7280;--accent:#c8102e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
header{padding:24px 20px 4px;max-width:1240px;margin:0 auto}
header h1{margin:0;font-size:21px;font-weight:600}
header .sub{margin:8px 0 0;color:var(--muted);font-size:13px}
main{max-width:1240px;margin:0 auto;padding:10px 20px 30px}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:16px 0}
section h2{margin:0 0 14px;font-size:16px;font-weight:600;display:flex;align-items:baseline;flex-wrap:wrap;gap:8px}
.count{font-size:12px;color:var(--muted);font-weight:400}
.imgtime{font-size:12px;color:var(--muted);font-weight:400}
.row{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}
.col-img{flex:1 1 340px;min-width:280px}
.col-tbl{flex:1 1 470px;min-width:320px;overflow-x:auto}
.col-img img{max-width:100%;border:1px solid var(--line);border-radius:8px;display:block}
.hint,.missing{font-size:12px;color:var(--muted);margin:6px 0 0}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f3f4f6;font-weight:600;white-space:nowrap}
td.c{white-space:nowrap}
.vs{color:var(--muted)}
tr.past td{color:var(--muted)}
tr.past td.tag{color:var(--muted)}
tr.future td.tag{color:var(--accent);font-weight:600}
tbody tr:hover{background:#fafafa}
.empty{color:var(--muted);text-align:center;padding:18px}
footer{max-width:1240px;margin:0 auto;padding:0 20px 60px}
footer h2{font-size:15px;margin:24px 0 8px}
footer ol{margin:0 0 16px;padding-left:20px}
footer li{margin:5px 0}
.btn{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;padding:9px 15px;border-radius:8px;font-size:13px}
.btn.ghost{background:transparent;color:var(--txt);border:1px solid var(--line)}
code{background:#f3f4f6;padding:2px 6px;border-radius:4px}
@media (max-width:640px){.col-img,.col-tbl{flex:1 1 100%}}
"""

INDEX_CSS = """
:root{--bg:#f6f7f9;--card:#fff;--line:#e5e7eb;--txt:#1f2328;--muted:#6b7280;--accent:#c8102e}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:var(--bg);color:var(--txt);font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;display:flex;align-items:center;justify-content:center;padding:24px}
.wrap{width:100%;max-width:520px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:28px 26px}
.badge{display:inline-block;background:#fdecef;color:var(--accent);font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px}
h1{margin:14px 0 6px;font-size:23px;font-weight:700;letter-spacing:.3px}
.sub{margin:0;color:var(--muted);font-size:14px}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0 6px}
.btn{display:inline-flex;align-items:center;justify-content:center;text-decoration:none;padding:11px 18px;border-radius:10px;font-size:14px;font-weight:600;border:1px solid transparent}
.btn.primary{background:var(--accent);color:#fff}
.btn.ghost{background:#fff;color:var(--txt);border-color:var(--line)}
.meta{margin:18px 0 0;padding-top:16px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
.meta b{color:var(--txt);font-weight:600}
.ics{margin:10px 0 0;display:flex;gap:8px;align-items:center;background:#f3f4f6;border-radius:8px;padding:8px 10px}
.ics code{font-size:12px;color:var(--txt);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.mini{background:#fff;border:1px solid var(--line);border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;color:var(--txt);white-space:nowrap}
.hint{font-size:12px;color:var(--muted);margin:12px 0 0}
"""


def load_manual():
    if not os.path.exists(MANUAL_FILE):
        return []
    with open(MANUAL_FILE, encoding="utf-8") as f:
        return json.load(f)


def mtime_str(path):
    if not os.path.exists(path):
        return ""
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")


def sync_images():
    """把官方图复制到 output/images/，返回 {赛事: 相对路径 或 None}。"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    mapping = {}
    for comp, code in REVIEW_COMPS:
        src = os.path.join(OFFICIAL_DIR, code + ".jpg")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(IMAGES_DIR, code + ".jpg"))
            mapping[comp] = "images/" + code + ".jpg"
        else:
            mapping[comp] = None
    return mapping


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_table(matches):
    today = date.today().isoformat()
    rows = []
    for m in matches:
        d = m.get("date", "")
        is_past = bool(d) and d < today
        cls = "past" if is_past else "future"
        tag = "已赛" if is_past else "待赛"
        home_raw = m.get("home", "")
        away_raw = m.get("away", "")
        home = esc(home_raw)
        away = esc(away_raw)
        if "上海海港" in home_raw:
            home = "<b>" + home + "</b>"
        if "上海海港" in away_raw:
            away = "<b>" + away + "</b>"
        rows.append(
            '<tr class="' + cls + '">'
            '<td class="c">' + esc(d) + '</td>'
            '<td class="c">' + esc(m.get("time", "")) + '</td>'
            '<td>' + home + ' <span class="vs">vs</span> ' + away + '</td>'
            '<td>' + esc(m.get("venue", "")) + '</td>'
            '<td class="c">' + esc(m.get("round", "")) + '</td>'
            '<td class="c tag">' + tag + '</td>'
            '</tr>')
    if not rows:
        body = '<tr><td colspan="6" class="empty">暂无数据：请先在 data/manual_matches.json 中添加该赛事场次</td></tr>'
    else:
        body = "\n".join(rows)
    return ('<table><thead><tr><th>日期</th><th>时间</th><th>对阵</th>'
            '<th>场地</th><th>轮次</th><th>状态</th></tr></thead>'
            '<tbody>' + body + '</tbody></table>')


def render_section(comp, code, matches, img, img_time):
    if img:
        img_html = ('<a href="' + img + '" target="_blank" rel="noopener">'
                    '<img src="' + img + '" alt="' + esc(comp) + '官方赛程图"></a>'
                    '<p class="hint">点击图片可查看原图</p>')
    else:
        img_html = ('<p class="missing">未找到官方赛程图：official/schedules/'
                    + code + '.jpg</p>')
    time_html = ('<span class="imgtime">官方图更新：' + esc(img_time) + '</span>'
                 if img_time else "")
    return ('<section><h2>' + esc(comp)
            + ' <span class="count">' + str(len(matches)) + ' 场</span>'
            + time_html + '</h2>'
            '<div class="row">'
            '<div class="col-img">' + img_html + '</div>'
            '<div class="col-tbl">' + render_table(matches) + '</div>'
            '</div></section>')


def render_index(now):
    """生成站点首页 index.html：订阅入口 + 核对面板入口。

    订阅链接在浏览器端用 location 拼出绝对地址，故部署到任意域名都正确。
    """
    head = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>上海海港 · 赛程日历</title>\n'
            '<style>' + INDEX_CSS + '</style>\n</head>\n<body>\n')
    body = (
        '<div class="wrap"><div class="card">\n'
        '<span class="badge">自动更新</span>\n'
        '<h1>上海海港 · 赛程日历</h1>\n'
        '<p class="sub">中超 / 中乙(梯队) / 亚冠 / 足协杯 · 一键订阅，自动同步</p>\n'
        '<div class="actions">\n'
        '<a class="btn primary" id="sub" href="shanghai_port.ics">订阅到日历</a>\n'
        '<a class="btn ghost" href="review.html">赛程核对面板</a>\n'
        '</div>\n'
        '<p class="hint">iPhone 点「订阅到日历」可直接唤起日历；'
        'Outlook 用下方链接「从 Internet 订阅」。</p>\n'
        '<div class="meta">\n'
        '<div>覆盖赛事：<b>中超 · 中乙(梯队) · 亚冠 · 足协杯</b></div>\n'
        '<div>自动更新：<b>每天 06:00</b>（GitHub Actions）</div>\n'
        '<div>最近生成：<b>' + now + '</b></div>\n'
        '<div class="ics"><code id="ics">shanghai_port.ics</code>'
        '<button class="mini" id="copy">复制链接</button></div>\n'
        '</div>\n</div></div>\n')
    script = (
        '<script>\n(function(){\n'
        'var base = new URL(".", location.href).href;\n'
        'var ics = base + "shanghai_port.ics";\n'
        'var webcal = ics.replace(/^https:/, "webcal:");\n'
        'var a = document.getElementById("sub");\n'
        'if (a) { a.href = webcal; }\n'
        'var code = document.getElementById("ics");\n'
        'if (code) { code.textContent = ics; }\n'
        'var copy = document.getElementById("copy");\n'
        'if (copy) { copy.addEventListener("click", function(){\n'
        '  navigator.clipboard.writeText(ics).then(function(){\n'
        '    copy.textContent = "已复制";\n'
        '    setTimeout(function(){ copy.textContent = "复制链接"; }, 1500);\n'
        '  });\n'
        '}); }\n'
        '})();\n</script>\n')
    return head + body + script + '</body>\n</html>\n'


def main():
    manual = load_manual()
    imgs = sync_images()

    sections = []
    for comp, code in REVIEW_COMPS:
        rows = [m for m in manual if m.get("competition") == comp]
        rows.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))
        img_time = mtime_str(os.path.join(OFFICIAL_DIR, code + ".jpg"))
        sections.append(render_section(comp, code, rows, imgs.get(comp), img_time))

    if REPO:
        edit_html = (
            '<a class="btn" href="https://github.com/' + esc(REPO)
            + '/edit/main/data/manual_matches.json" target="_blank" rel="noopener">'
            '编辑 manual_matches.json</a> '
            '<a class="btn ghost" href="https://github.com/' + esc(REPO)
            + '/commits/main/data/manual_matches.json" target="_blank" rel="noopener">'
            '查看改动历史</a>')
    else:
        edit_html = '请在仓库中编辑 <code>data/manual_matches.json</code>'

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    tracked = {c for c, _ in REVIEW_COMPS}
    total = sum(1 for m in manual if m.get("competition") in tracked)

    html = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>上海海港 · 赛程核对面板</title>\n'
        '<style>' + CSS + '</style>\n'
        '</head>\n<body>\n'
        '<header>\n'
        '<h1>上海海港 · 赛程核对面板</h1>\n'
        '<p class="sub">官方赛程图 vs 日历数据 · 共 ' + str(total)
        + ' 场需核对 · 生成于 ' + now + '</p>\n'
        '</header>\n<main>\n'
        + "".join(sections)
        + '\n</main>\n<footer>\n'
        '<h2>30 秒核对法</h2>\n<ol>\n'
        '<li>看左侧官方图，找「上海海港」的场次。</li>\n'
        '<li>对照右侧表格，逐行核对 <b>日期 / 时间 / 主客 / 场地</b>'
        '（灰底为已赛，重点看红字「待赛」）。</li>\n'
        '<li>有差异 → 编辑 <code>manual_matches.json</code> → 提交，'
        'Actions 会自动重建日历。</li>\n'
        '</ol>\n<p>' + edit_html + '</p>\n'
        '</footer>\n</body>\n</html>\n')

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("[done] 生成核对面板 -> " + OUTPUT_FILE)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(render_index(now))
    print("[done] 生成首页     -> " + INDEX_FILE)

    for comp, code in REVIEW_COMPS:
        print("  " + comp + ": 官方图 = " + ("有" if imgs.get(comp) else "缺"))


if __name__ == "__main__":
    main()

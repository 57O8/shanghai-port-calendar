#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成人工核对面板 output/review.html。

把「海港官网发布的官方赛程图」与「data/manual_matches.json 中的亚冠/足协杯数据」
并排展示，供官方图更新时快速核对；同时把官方图复制到 output/images/，
随 gh-pages 一起发布，因此页面不依赖任何外部资源。

部署后访问：https://<用户名>.github.io/<仓库名>/review.html
"""
import base64
import json
import os
import re
import shutil
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL_FILE = os.path.join(BASE_DIR, "data", "manual_matches.json")
OFFICIAL_DIR = os.path.join(BASE_DIR, "official", "schedules")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "review.html")
INDEX_FILE = os.path.join(OUTPUT_DIR, "index.html")
QR_FILE = os.path.join(OUTPUT_DIR, "qrcode.svg")

# 需要人工核对的赛事 -> 官方图代号
REVIEW_COMPS = [("亚冠", "afc"), ("足协杯", "cfa")]

# 作者信息（首页展示）——如需指向个人主页，替换下面对应的 URL 即可
AUTHOR = "57O8"
AUTHOR_TAGLINE = "上海海港球迷"
# (显示名, 链接, 样式类, 附加标识如抖音号)；排序即展示顺序
SOCIALS = [
    ("抖音", "https://v.douyin.com/SFy1bkRlnwA/", "dy", ""),
    ("微博", "https://weibo.com/u/1862203482", "wb", ""),
    ("小红书", "https://www.xiaohongshu.com/user/profile/5d3405510000000011006339", "xhs", ""),
]
AVATAR_SRC = os.path.join(BASE_DIR, "assets", "ego.jpg")

# Actions 中自动注入；本地运行时为空，则隐藏"编辑"按钮
REPO = os.environ.get("GITHUB_REPOSITORY", "").strip()

# 访问统计（GoatCounter：无 cookie、不存 IP、不跨站追踪）——**当前关闭**。
# 站点码 = 注册用户名的小写形式；后台看板 https://57o8.goatcounter.com
#
# 现状：留空 → 页面不注入任何统计代码，零外部请求（这是默认状态）。
# 想开启：把下面的空串换成 "57o8"，重新构建即可；页面文案会自动跟着变。
#         同时记得在 make_qrcode.py 里把 QR_REF 设成 "qr"，二维码才会带渠道标记。
#
# 实现刻意"不加载 count.js"：用内联的 1×1 信标直接打 /count 接口。
#   · 少一个来自 gc.zgo.at 的第三方脚本（国内网络更稳，也不用担心 CDN 被墙）；
#   · 页面上只有一个指向 goatcounter.com 的图片请求，隐私边界清楚可解释。
# 局限：统计不到真实订阅数——.ics 由日历客户端后台拉取，不执行 JS。
GOATCOUNTER_CODE = os.environ.get("GOATCOUNTER_CODE", "").strip()

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
.sig{font-size:12px;color:var(--muted);margin-top:22px}
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
.profile{display:flex;gap:16px;align-items:center}
.avatar{width:86px;height:86px;border-radius:50%;object-fit:cover;border:3px solid #fff;box-shadow:0 2px 10px rgba(200,16,46,.18);flex:none;background:#f3f4f6}
.avatar-ph{display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:700;color:var(--accent)}
.who{min-width:0}
.name{font-size:27px;font-weight:700;letter-spacing:.6px;line-height:1.1}
.tagline{font-size:13px;color:var(--muted);margin-top:3px}
.socials{display:flex;gap:8px;margin-top:11px;flex-wrap:wrap}
.pill{font-size:12px;text-decoration:none;padding:4px 12px;border-radius:999px;font-weight:600;transition:opacity .15s}
.pill:hover{opacity:.75}
.pill .handle{font-weight:400;opacity:.6;margin-left:5px;font-size:11px}
.pill.xhs{background:#fff1f3;color:#e0173b}
.pill.dy{background:#f2f2f2;color:#111}
.pill.wb{background:#fff3ec;color:#d9480f}
.divider{height:1px;background:var(--line);margin:20px 0 18px}
/* 备用订阅通道（jsDelivr CDN）：折叠起来，不干扰主流程 */
.alt{margin:14px 0 0;border:1px solid var(--line);border-radius:10px;padding:0 12px;background:#fcfcfd}
.alt summary{cursor:pointer;font-size:13px;color:var(--txt);padding:10px 0;font-weight:600;outline:none}
.alt summary::marker{color:var(--muted)}
.alt p{margin:0 0 8px;font-size:12px;color:var(--muted);line-height:1.6}
.alt[open]{padding-bottom:12px}
/* 信任说明：降低"陌生链接不敢点"的门槛 */
.trust{margin:16px 0 0;padding:12px 14px;background:#fafbfc;border-left:3px solid var(--accent);border-radius:8px}
.trust-h{font-size:13px;font-weight:700;margin-bottom:7px}
.trust ul{margin:0;padding-left:17px}
.trust li{font-size:12.5px;color:var(--muted);margin:4px 0;line-height:1.6}
.trust li b{color:var(--txt);font-weight:600}
.trust a{color:var(--accent);text-decoration:none}
.trust a:hover{text-decoration:underline}
.trust-note{margin:8px 0 0;font-size:12px;color:var(--muted)}
/* 二维码：内联 SVG，宽度交给 CSS 控制 */
.qrbox{display:flex;justify-content:center;padding:6px 0 2px}
.qrbox svg{width:172px;height:172px;border:1px solid var(--line);border-radius:8px;background:#fff}
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


def load_avatar_uri():
    """读取头像并转成 data URI。

    内嵌进 index.html 后页面自包含，不依赖部署时的资源路径，
    换了 assets/ego.jpg 重新构建即可自动生效。
    """
    if not os.path.exists(AVATAR_SRC):
        return None
    with open(AVATAR_SRC, "rb") as f:
        raw = f.read()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


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


def load_qrcode_svg():
    """读取构建期生成的二维码 SVG 并内联进首页（页面自包含，不依赖外部资源）。

    去掉固定的 width/height，改由 CSS 控制尺寸，避免 410px 的原生尺寸撑破卡片。
    """
    if not os.path.exists(QR_FILE):
        return ""
    with open(QR_FILE, encoding="utf-8") as f:
        svg = f.read().strip()
    svg = re.sub(r'\s(?:width|height)="\d+"', "", svg, count=2)
    return svg


def render_trust():
    """信任说明区：直接回答"这链接靠谱吗、点下去会发生什么"。"""
    if REPO:
        repo_link = ('<a href="https://github.com/' + esc(REPO)
                     + '" target="_blank" rel="noopener">GitHub 仓库</a>')
    else:
        repo_link = "GitHub 仓库"
    stat_line = (
        '<li><b>不加载任何第三方脚本</b>，只看总量不认人：一条匿名计数请求'
        '（GoatCounter，不写 cookie、不存 IP、不做跨站追踪）；不想被计入就在地址后加 '
        '<code>#toggle-goatcounter</code></li>\n'
        if GOATCOUNTER_CODE else
        '<li><b>不加载任何第三方脚本</b>，页面没有任何外部请求</li>\n')
    return (
        '<div class="trust">\n'
        '<div class="trust-h">订阅前你可能想知道的</div>\n'
        '<ul>\n'
        '<li><b>不用登录、不用授权任何账号</b>，只是往你的日历里加一个只读订阅源</li>\n'
        '<li><b>不做用户画像、不要手机号</b>：页面没有 cookie，也没有广告</li>\n'
        + stat_line +
        '<li><b>数据来源公开</b>：中足联官网、上海海港官网发布的赛程</li>\n'
        '<li><b>全部代码公开可查</b>：' + repo_link + '，赛程怎么来的都能追溯</li>\n'
        '</ul>\n'
        '<p class="trust-note">随时可退订：在日历 App 里删掉这个日历即可，不影响其他日程。</p>\n'
        '</div>\n')


def render_profile(avatar_uri):
    """首页作者卡：头像 + 57O8 + 全平台账号（抖音置首）。"""
    if avatar_uri:
        avatar = '<img class="avatar" src="' + avatar_uri + '" alt="57O8 头像">'
    else:
        avatar = '<div class="avatar avatar-ph">57</div>'
    pills = []
    for item in SOCIALS:
        name, url, cls = item[0], item[1], item[2]
        handle = item[3] if len(item) > 3 else ""
        label = esc(name)
        if handle:
            label += '<span class="handle">' + esc(handle) + '</span>'
        pills.append('<a class="pill ' + cls + '" href="' + esc(url)
                     + '" target="_blank" rel="noopener" title="' + esc(name)
                     + (' ' + esc(handle) if handle else '') + '">'
                     + label + '</a>')
    pills = "\n".join(pills)
    return (
        '<div class="profile">\n' + avatar + '\n'
        '<div class="who">\n'
        '<div class="name">' + esc(AUTHOR) + '</div>\n'
        '<div class="tagline">' + esc(AUTHOR_TAGLINE) + ' · 全平台同名</div>\n'
        '<div class="socials">\n' + pills + '\n</div>\n'
        '</div>\n</div>\n')


def track_script(extra_js=""):
    """GoatCounter 统计代码：内联 1×1 信标，不加载任何第三方脚本。

    - 每次页面浏览发一次 GET 到 <code>.goatcounter.com/count，带 cookie 说明为"无"；
    - 非 http(s) 环境（本地 file:// 预览）自动不统计，避免污染线上数据；
    - 在自己浏览器访问时，地址后加 #toggle-goatcounter 可把本机排除，再加一次恢复；
      ?notrack=1 / ?notrack=0 是同一开关的显式写法。
    extra_js 用于在页面里补挂点击事件（订阅、复制、二维码等）。
    """
    if not GOATCOUNTER_CODE:
        return ""
    return (
        '<script>\n(function(){\n'
        'var GC = ' + json.dumps(GOATCOUNTER_CODE) + ';\n'
        'if (!GC || !/^https?:$/.test(location.protocol)) return;\n'
        'function off(){ try { return localStorage.getItem("gc-off") === "1"; }'
        ' catch(e) { return false; } }\n'
        'function setOff(v){ try { localStorage.setItem("gc-off", v ? "1" : "0"); }'
        ' catch(e) {} }\n'
        'var q = {};\n'
        'location.search.replace(/^\\?/, "").split("&").forEach(function(kv){\n'
        '  if (!kv) return;\n'
        '  var i = kv.indexOf("=");\n'
        '  q[decodeURIComponent(i < 0 ? kv : kv.slice(0, i))] ='
        ' i < 0 ? "" : decodeURIComponent(kv.slice(i + 1));\n'
        '});\n'
        'if (q.notrack === "1") setOff(true);\n'
        'if (q.notrack === "0") setOff(false);\n'
        'if (location.hash.indexOf("toggle-goatcounter") >= 0) {\n'
        '  var to = !off(); setOff(to);\n'
        '  alert(to ? "已停止统计这台设备的访问" : "已恢复统计这台设备");\n'
        '}\n'
        'function track(path, title, ev){\n'
        '  if (off()) return;\n'
        '  var u = "https://" + GC + ".goatcounter.com/count?p="'
        ' + encodeURIComponent(path);\n'
        '  if (title) u += "&t=" + encodeURIComponent(title);\n'
        '  if (ev) u += "&e=true";\n'
        '  var ref = "";\n'
        '  if (q.ref) { ref = q.ref; }\n'
        '  else if (document.referrer'
        ' && document.referrer.indexOf(location.origin) !== 0) {\n'
        '    ref = document.referrer;\n'
        '  }\n'
        '  if (ref) u += "&ref=" + encodeURIComponent(ref);\n'
        '  (new Image()).src = u;\n'
        '}\n'
        'window.__track = track;\n'
        'var basePath = new URL(".", location.href).pathname;\n'
        'var p = "/" + location.pathname.slice(basePath.length);\n'
        'if (p === "/index.html") p = "/";\n'
        'track(p, document.title, false);\n'
        + extra_js +
        '})();\n</script>\n')


def render_index(now, avatar_uri):
    """生成站点首页 index.html：作者卡 + 订阅入口 + 核对面板入口。

    订阅链接在浏览器端用 location 拼出绝对地址，故部署到任意域名都正确。
    """
    profile = render_profile(avatar_uri)
    qr_svg = load_qrcode_svg()
    if qr_svg:
        qr_block = ('<details class="alt">\n'
                    '<summary>扫码订阅 / 分享给朋友</summary>\n'
                    '<p>二维码指向本页，扫码后先看到说明与订阅按钮，再决定要不要订。'
                    '可截图发到小红书、抖音图文，或直接让朋友扫。</p>\n'
                    '<div class="qrbox">' + qr_svg + '</div>\n'
                    '</details>\n')
    else:
        qr_block = ""
    head = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>上海海港 · 赛程日历</title>\n'
            '<style>' + INDEX_CSS + '</style>\n</head>\n<body>\n')
    body = (
        '<div class="wrap"><div class="card">\n'
        + profile +
        '<div class="divider"></div>\n'
        '<span class="badge">自动更新</span>\n'
        '<h1>上海海港 · 赛程日历</h1>\n'
        '<p class="sub">中超 / 中乙(梯队) / 亚冠 / 足协杯 · 一键订阅，自动同步</p>\n'
        '<div class="actions">\n'
        '<a class="btn primary" id="sub" href="shanghai_port.ics">订阅到日历</a>\n'
        '<a class="btn ghost" href="review.html">赛程核对面板</a>\n'
        '</div>\n'
        '<p class="hint">iPhone 点「订阅到日历」可直接唤起日历；'
        'Outlook 用下方链接「从 Internet 订阅」。</p>\n'
        + render_trust() +
        '<div class="meta">\n'
        '<div>覆盖赛事：<b>中超 · 中乙(梯队) · 亚冠 · 足协杯</b></div>\n'
        '<div>自动更新：<b>每天 06:00</b>（GitHub Actions）</div>\n'
        '<div>最近生成：<b>' + now + '</b></div>\n'
        '<div class="ics"><code id="ics">shanghai_port.ics</code>'
        '<button class="mini" id="copy">复制链接</button></div>\n'
        '</div>\n'
        '<details class="alt" id="alt" hidden>\n'
        '<summary>订阅后一直不更新？试试备用链接</summary>\n'
        '<p>主链接走 GitHub Pages，改动后约 10 分钟生效；备用链接走 jsDelivr CDN，'
        '国内访问通常更稳，但内容更新最长会延迟约 12 小时。两者内容一致，'
        '<b>任选一个订阅即可——不要同时订阅两个</b>，否则同一场比赛会出现两次。</p>\n'
        '<div class="ics"><code id="mirror">&hellip;</code>'
        '<button class="mini" id="copy2">复制</button></div>\n'
        '</details>\n'
        + qr_block +
        '</div></div>\n')
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
        # ---- 备用订阅通道：jsDelivr CDN（不消耗 GitHub 带宽，更新延迟约 12h）----
        'var repo = ' + json.dumps(REPO) + ';\n'
        'if (!repo) {\n'
        '  var h = location.hostname, seg = location.pathname.split("/").filter(Boolean);\n'
        '  if (/\\.github\\.io$/i.test(h) && seg.length) { repo = h.split(".")[0] + "/" + seg[0]; }\n'
        '}\n'
        'var altBox = document.getElementById("alt");\n'
        'if (repo && altBox) {\n'
        '  var mirror = "https://cdn.jsdelivr.net/gh/" + repo + "@gh-pages/shanghai_port.ics";\n'
        '  document.getElementById("mirror").textContent = mirror;\n'
        '  altBox.hidden = false;\n'
        '  var copy2 = document.getElementById("copy2");\n'
        '  if (copy2) { copy2.addEventListener("click", function(){\n'
        '    navigator.clipboard.writeText(mirror).then(function(){\n'
        '      copy2.textContent = "已复制";\n'
        '      setTimeout(function(){ copy2.textContent = "复制"; }, 1500);\n'
        '    });\n'
        '  }); }\n'
        '}\n'
        '})();\n</script>\n')
    # 统计：页面浏览 + 4 个关键点击（都在 track_script 里统一注入）
    extra = (
        'function hook(id, path, title){\n'
        '  var el = document.getElementById(id);\n'
        '  if (el) el.addEventListener("click", function(){'
        ' track(path, title, true); });\n'
        '}\n'
        'hook("sub", "/click/subscribe", "点击订阅到日历");\n'
        'hook("copy", "/click/copy-ics", "复制订阅链接");\n'
        'hook("copy2", "/click/copy-mirror", "复制备用链接");\n'
        'var qrd = document.querySelector("details.alt .qrbox");\n'
        'if (qrd) {\n'
        '  var qd = qrd.parentNode;\n'
        '  qd.addEventListener("toggle", function(){\n'
        '    if (qd.open) track("/click/qrcode", "展开二维码", true);\n'
        '  });\n'
        '}\n'
        'var rv = document.querySelector(\'a[href="review.html"]\');\n'
        'if (rv) rv.addEventListener("click", function(){'
        ' track("/click/review-panel", "打开核对面板", true); });\n')
    return head + body + script + track_script(extra) + '</body>\n</html>\n'


def main():
    manual = load_manual()
    imgs = sync_images()
    avatar_uri = load_avatar_uri()

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
        '<p class="sig">上海海港赛程日历 · by ' + esc(AUTHOR) + '</p>\n'
        '</footer>\n'
        + track_script() +
        '</body>\n</html>\n')

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("[done] 生成核对面板 -> " + OUTPUT_FILE)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(render_index(now, avatar_uri))
    print("[done] 生成首页     -> " + INDEX_FILE)

    for comp, code in REVIEW_COMPS:
        print("  " + comp + ": 官方图 = " + ("有" if imgs.get(comp) else "缺"))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成首页二维码（SVG），指向站点首页。

为什么指向首页而不是 .ics：
  直接扫到 .ics 会看到一屏纯文本或触发下载，反而加重"这链接靠谱吗"的疑虑；
  指向首页则先看到说明与订阅按钮，转化与信任都更好。

实现：借 node 跑 assets/vendor/qrcode.js 拿到模块矩阵，再用 Python 拼 SVG。
  - 不引入 Pillow 等图像依赖，输出矢量、任意缩放不失真；
  - node 缺失时优雅退出（返回非 0 但不影响主流程，由 workflow 决定是否阻断）。
"""
import json
import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_JS = os.path.join(BASE_DIR, "assets", "vendor", "qrcode.js")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "qrcode.svg")

QUIET = 4      # 静默区（模块数）。4 是 QR 规范要求的最小值，少于此部分扫码器会失败。
SCALE = 10     # 每个模块的像素边长

NODE_JS = r"""
const qrcode = require(process.env.QR_LIB);
const qr = qrcode(0, 'M');
qr.addData(process.env.QR_URL);
qr.make();
const n = qr.getModuleCount();
const rows = [];
for (let r = 0; r < n; r++) {
  let row = '';
  for (let c = 0; c < n; c++) row += qr.isDark(r, c) ? '1' : '0';
  rows.push(row);
}
process.stdout.write(JSON.stringify(rows));
"""


def find_node():
    """按优先级找 node：环境变量 NODE_BIN -> PATH -> 托管目录。"""
    explicit = os.environ.get("NODE_BIN", "").strip()
    if explicit and os.path.exists(explicit):
        return explicit
    found = shutil.which("node") or shutil.which("node.exe")
    if found:
        return found
    home = os.path.expanduser("~")
    pattern = os.path.join(home, ".workbuddy", "binaries", "node", "versions")
    if os.path.isdir(pattern):
        for name in sorted(os.listdir(pattern), reverse=True):
            for exe in ("node.exe", "node"):
                cand = os.path.join(pattern, name, exe)
                if os.path.exists(cand):
                    return cand
    return None


def build_svg(rows):
    """把矩阵拼成 SVG；同一行相邻的暗模块合并为一个 rect，显著减小体积。"""
    n = len(rows)
    total = (n + QUIET * 2) * SCALE
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" shape-rendering="crispEdges" role="img" '
        'aria-label="订阅二维码">' % (total, total, total, total),
        '<rect width="%d" height="%d" fill="#ffffff"/>' % (total, total),
    ]
    for r, row in enumerate(rows):
        c = 0
        while c < n:
            if row[c] == "1":
                start = c
                while c < n and row[c] == "1":
                    c += 1
                x = (QUIET + start) * SCALE
                y = (QUIET + r) * SCALE
                w = (c - start) * SCALE
                parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#111111"/>'
                             % (x, y, w, SCALE))
            else:
                c += 1
    parts.append("</svg>")
    return "".join(parts)


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    url = os.environ.get("SITE_URL", "").strip()
    if not url:
        if not repo:
            print("[skip] 未提供 GITHUB_REPOSITORY / SITE_URL，跳过二维码生成")
            return 0
        owner, _, name = repo.partition("/")
        url = "https://%s.github.io/%s/" % (owner.lower(), name)

    # 渠道标记：二维码单独算一路来源，便于判断"扫图来的"占多少。
    # 目前统计关闭，故默认留空（二维码指向干净地址）；开启 GoatCounter 后设 QR_REF=qr。
    ref = os.environ.get("QR_REF", "").strip()
    if ref and "ref=" not in url:
        url += ("&" if "?" in url else "?") + "ref=" + ref

    node = find_node()
    if not node:
        print("[skip] 未找到 node，跳过二维码生成（不影响日历）")
        return 0
    if not os.path.exists(VENDOR_JS):
        print("[skip] 缺少 assets/vendor/qrcode.js，跳过二维码生成")
        return 0

    env = dict(os.environ)
    env["QR_LIB"] = VENDOR_JS
    env["QR_URL"] = url
    proc = subprocess.run([node, "-e", NODE_JS], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        print("[warn] node 生成二维码矩阵失败：%s" % (proc.stderr or "")[:300])
        return 0

    rows = json.loads(proc.stdout)
    svg = build_svg(rows)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(svg)
    print("[done] 二维码 -> %s（%s，%d 模块，%d 字节）"
          % (OUTPUT_FILE, url, len(rows), len(svg)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

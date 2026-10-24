#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从中足联官方 API 自动抓取上海海港赛程，写入 data/auto_matches.json。

覆盖：
  - 中超 (CSL, competition_code=CSL)        -> 一线队
  - 中乙 (CL2, competition_code=CL2)        -> 梯队（上海海港富盛经开队）

说明：
  - 中足联只发布国内联赛（中超/中甲/中乙），亚冠、足协杯不在此源，
    由 data/manual_matches.json 手工维护并合并。
  - 若某赛事抓取失败（如官网临时不可达），自动复用上一次成功缓存，
    保证日历不会因此“断更/报错”。
  - 关键词 "上海海港" 同时命中一线队与梯队（上海海港富盛经开队）。

官方赛程图监控（亚冠/中超/足协杯的“官方口径”）：
  - 上海海港官网 www.fcshanghaiport.com/battle 右侧以图片形式发布
    三项赛事的官方赛程表（saicheng_afc / saicheng_csl / saicheng_cfa）。
  - 本脚本每次运行会解析这些图片 URL 并下载到 official/schedules/，
    一旦发现 URL 变化（即俱乐部更新了官方赛程），写入
    official/schedules/UPDATE_NOTICE.md 提醒人工核对 manual_matches.json。
  - 官网图片需要带 Referer 防盗链访问；任一环节失败仅告警，不中断主流程。
"""
import json
import os
import re
import sys
import ssl
import urllib.request
import urllib.error
from urllib.parse import urlsplit, urlunsplit, quote

API_BASE = "https://api.cfl-china.cn/frontweb/api"
TEAM_KEYWORDS = ["上海海港"]  # 同时命中 上海海港 与 上海海港富盛经开队

# competition_code -> 中文名（仅用于日志与缓存回退标识）
COMPETITIONS = {
    "CSL": "中超",
    "CL2": "中乙",
}

UA = "Mozilla/5.0 (compatible; shanghai-port-calendar/1.0)"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE_DIR, "data", "auto_matches.json")

# ---- 官方赛程图监控（海港官网）----
OFFICIAL_PAGE = "https://www.fcshanghaiport.com/battle"
OFFICIAL_DIR = os.path.join(BASE_DIR, "official", "schedules")
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
OFFICIAL_NAMES = {"afc": "亚冠", "csl": "中超", "cfa": "足协杯"}
SAICHENG_PATTERN = re.compile(
    r'id="saicheng_([a-z]+)"[^>]*?cg_jfb\(\'([^\']+?)\'\)', re.S)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def team_match(m):
    home = m.get("home_contestant_name", "") or ""
    away = m.get("away_contestant_name", "") or ""
    return any(k in home or k in away for k in TEAM_KEYWORDS)


def get_active_season(comp_code):
    data = fetch_json(f"{API_BASE}/tournaments?competition_code={comp_code}")
    dl = (data.get("data") or {}).get("dataList") or []
    for t in dl:
        if t.get("active") == "yes":
            return t["id"]
    return dl[0]["id"] if dl else None


def fetch_matches(comp_code, season_id):
    url = (f"{API_BASE}/matches/page?competition_code={comp_code}"
           f"&tournament_calendar_id={season_id}&pageSize=999&curPage=1")
    data = fetch_json(url)
    return (data.get("data") or {}).get("dataList") or []


def normalize(m):
    date = (m.get("local_date") or "").strip()
    time = (m.get("local_time") or "").strip()
    if len(time) >= 5:
        time = time[:5]  # 去掉秒，保留 HH:MM
    week = m.get("week")
    round_label = f"第{week}轮" if isinstance(week, (int, float)) else (str(week) if week else "")
    venue = m.get("venue_short_name") or m.get("venue_long_name") or ""
    return {
        "date": date,
        "time": time,
        "home": m.get("home_contestant_name", "") or "",
        "away": m.get("away_contestant_name", "") or "",
        "competition": m.get("competition_name") or "",
        "venue": venue,
        "round": round_label,
        "status": m.get("match_status", ""),
    }


def load_previous():
    prev = {}
    if os.path.exists(OUTPUT):
        try:
            for m in json.load(open(OUTPUT, encoding="utf-8")):
                prev.setdefault(m.get("competition"), []).append(m)
        except Exception:
            prev = {}
    return prev


def _quote_url(url):
    """URL 含中文文件名时，百分号编码路径部分。"""
    sp = urlsplit(url)
    return urlunsplit((sp.scheme, sp.netloc, quote(sp.path, safe="/%"),
                       sp.query, sp.fragment))


def _http_get(url, referer=None, timeout=30):
    headers = {"User-Agent": BROWSER_UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def fetch_official_images():
    """监控海港官网发布的官方赛程图（亚冠/中超/足协杯）。

    URL 变化（俱乐部更新官方赛程）时写 UPDATE_NOTICE.md，
    提醒人工核对 data/manual_matches.json。任何失败仅告警不中断。
    """
    os.makedirs(OFFICIAL_DIR, exist_ok=True)
    state_file = os.path.join(OFFICIAL_DIR, "state.json")
    try:
        html = _http_get(OFFICIAL_PAGE, referer=OFFICIAL_PAGE).decode("utf-8", "ignore")
    except Exception as e:
        print(f"[warn] 官方赛程图监控: 官网页面抓取失败 ({e})", file=sys.stderr)
        return
    pairs = SAICHENG_PATTERN.findall(html)
    if not pairs:
        print("[warn] 官方赛程图监控: 未找到 saicheng 锚点（官网可能改版）", file=sys.stderr)
        return
    prev = {}
    if os.path.exists(state_file):
        try:
            prev = json.load(open(state_file, encoding="utf-8"))
        except Exception:
            prev = {}
    changed, current = [], {}
    for code, url in pairs:
        if code not in OFFICIAL_NAMES:
            continue
        current[code] = url
        try:
            data = _http_get(_quote_url(url), referer=OFFICIAL_PAGE, timeout=60)
            if len(data) > 1000:  # 官网 404 页约 146 字节
                with open(os.path.join(OFFICIAL_DIR, f"{code}.jpg"), "wb") as f:
                    f.write(data)
            else:
                print(f"[warn] 官方赛程图 {code}: 返回内容过小，疑似 404", file=sys.stderr)
        except Exception as e:
            print(f"[warn] 官方赛程图 {code}: 下载失败 ({e})", file=sys.stderr)
        if prev.get(code) != url:
            changed.append(code)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    notice = os.path.join(OFFICIAL_DIR, "UPDATE_NOTICE.md")
    if changed:
        names = "、".join(OFFICIAL_NAMES[c] for c in changed)
        with open(notice, "w", encoding="utf-8") as f:
            f.write(
                "# ⚠️ 官方赛程图已更新\n\n"
                f"俱乐部官网的官方赛程图发生变化：**{names}**。\n\n"
                "请查看本目录下对应 jpg，核对并更新 `data/manual_matches.json`"
                "（亚冠/足协杯）。可配合懂球帝、微博 @中国足协杯、"
                "transfermarkt 等渠道交叉验证。\n")
        print(f"[notice] 官方赛程图已更新: {names} -> {notice}")
    elif os.path.exists(notice):
        os.remove(notice)


def main():
    prev = load_previous()
    results = []
    for code, name in COMPETITIONS.items():
        try:
            sid = get_active_season(code)
            if not sid:
                print(f"[warn] {name}: 未找到赛季，使用缓存 {len(prev.get(name, []))} 条", file=sys.stderr)
                results.extend(prev.get(name, []))
                continue
            raw = fetch_matches(code, sid)
            got = [normalize(m) for m in raw if team_match(m)]
            print(f"[ok] {name}: 共 {len(raw)} 场，命中上海海港 {len(got)} 场")
            results.extend(got)
        except Exception as e:
            print(f"[warn] {name}: 抓取失败 ({e})，使用缓存 {len(prev.get(name, []))} 条", file=sys.stderr)
            results.extend(prev.get(name, []))

    results.sort(key=lambda x: (x["date"], x["time"]))

    if not results and not os.path.exists(OUTPUT):
        print("[error] 未获取到任何赛程且无历史缓存", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[done] 写入 {len(results)} 场 -> {OUTPUT}")

    fetch_official_images()


if __name__ == "__main__":
    main()

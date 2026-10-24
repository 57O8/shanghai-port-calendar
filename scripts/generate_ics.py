#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取 data/auto_matches.json（自动抓取）与 data/manual_matches.json（手工维护），
合并、去重后生成 output/shanghai_port.ics。
"""
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTO_FILE = os.path.join(BASE_DIR, "data", "auto_matches.json")
MANUAL_FILE = os.path.join(BASE_DIR, "data", "manual_matches.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "shanghai_port.ics")


def parse_datetime(date_str, time_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=TZ)


def escape_ics(text):
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    auto = load(AUTO_FILE)
    manual = load(MANUAL_FILE)
    merged = auto + manual

    seen = set()
    events = []
    for m in merged:
        key = (m.get("date"), m.get("time"), m.get("home"), m.get("away"), m.get("competition"))
        if key in seen:
            continue
        seen.add(key)
        events.append(m)

    events.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Shanghai Port FC//Calendar//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:上海海港赛程",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    for i, m in enumerate(events):
        try:
            start = parse_datetime(m["date"], m["time"])
        except Exception:
            continue
        end = start + timedelta(hours=2)
        uid = f"shanghai-port-{start.strftime('%Y%m%d%H%M')}-{i}@fcshanghaiport"
        summary = f"【{m.get('competition', '')}】{m.get('home', '')} vs {m.get('away', '')}"
        description = f"{m.get('round', '')} | {m.get('competition', '')}"
        location = m.get("venue", "")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;TZID=Asia/Shanghai:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Asia/Shanghai:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{escape_ics(summary)}",
            f"LOCATION:{escape_ics(location)}",
            f"DESCRIPTION:{escape_ics(description)}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines))

    print(f"生成 {len(events)} 场（自动 {len(auto)} + 手工 {len(manual)}） -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

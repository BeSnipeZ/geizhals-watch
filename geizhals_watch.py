"""Watch prices on geizhals.de and get a Telegram message when one drops.

watchlist.json:
    [{"name": "Raspberry Pi 5 8GB", "url": "https://geizhals.de/...-a3061627.html", "target": 80.0}]
`target` is optional. You get a message when a price falls below its lowest seen value,
and once when it reaches the target.

    python geizhals_watch.py          check once (run it from cron or Task Scheduler, e.g. twice a day)
    python geizhals_watch.py --test   self-test without network

Telegram: set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID. Without them the result is only printed.
Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
WATCHLIST = HERE / "watchlist.json"
STATE = HERE / "state.json"  # per URL: low, last, history
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
    "Accept-Language": "de-DE",
}


def price_from(html: str) -> float | None:
    """Geizhals page title: '<title>Shelly Plug S Gen3 ab € 14,99 (2026) | ...'."""
    html = re.sub(r"&#xa0;|&nbsp;|&#160;", " ", html[:20000])  # Geizhals writes "€&#xa0;14,99"
    m = re.search(r"<title>[^<]*?ab\s*€\s*([\d.]+,\d\d)", html)
    return float(m[1].replace(".", "").replace(",", ".")) if m else None


def fetch(url: str) -> float | None:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20) as r:
        return price_from(r.read().decode("utf-8", "replace"))


def judge(item: dict, price: float, old: dict | None) -> str | None:
    """Message text or None. The first price seen is only remembered."""
    target = item.get("target")
    if target and price <= target and (not old or old["last"] > target):
        return f"🎯 {item['name']}: {price:.2f} € (target {target:.2f} €)"
    if old and price < old["low"] - 0.005:
        return f"📉 {item['name']}: {price:.2f} € (lowest so far {old['low']:.2f} €)"
    return None


def telegram(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=15).close()
    return True


def run() -> None:
    items = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    for item in items:
        try:
            price = fetch(item["url"])
        except Exception as e:
            print(f"{item['name']}: {e}")
            continue
        if price is None:
            print(f"{item['name']}: no price on the page")
            continue
        old = state.get(item["url"])
        msg = judge(item, price, old)
        if msg:
            try:
                telegram(msg)
            except Exception as e:
                # keep the old state, otherwise the drop counts as reported and the message is lost
                print(f"Telegram: {e} - next run reports again")
                continue
        state[item["url"]] = {
            "last": price,
            "low": min(price, old["low"]) if old else price,
            "history": ((old or {}).get("history", []) + [[datetime.now().strftime("%Y-%m-%d %H:%M"), price]])[-60:],
        }
        print(f"{item['name']}: {price:.2f} €" + (f"  -> {msg}" if msg else ""))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def selftest() -> None:
    assert price_from("<title>Shelly Plug S Gen3 ab € 14,99 (2026) | Geizhals</title>") == 14.99
    assert price_from("<title>Pi 5 ab € 1.202,90 (2026)</title>") == 1202.90
    assert price_from("<title>Shelly Plug S Gen3 ab €&#xa0;14,99 (2026) | Preisvergleich") == 14.99
    assert price_from("<title>nothing</title>") is None
    item = {"name": "X", "target": 12.0}
    assert judge(item, 13.0, None) is None
    assert judge(item, 12.5, {"low": 13.0, "last": 13.0}).startswith("📉")
    assert judge(item, 11.9, {"low": 12.5, "last": 12.5}).startswith("🎯")
    assert judge(item, 11.9, {"low": 11.9, "last": 11.9}) is None  # not again every day
    print("self-test ok")


if __name__ == "__main__":
    selftest() if "--test" in sys.argv else run()

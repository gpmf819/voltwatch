#!/usr/bin/env python3
"""
Volt & Watt Market Watch - Daily Pre-fetch
Runs via GitHub Actions each morning.
Fetches EV, Energy, and V2X news via Anthropic API + web search,
writes market-watch-cache.json for the HTML page to consume.
"""

import os, json, re, urllib.request, urllib.error
from datetime import datetime, timezone

API_KEY = os.environ["ANTHROPIC_API_KEY"]

SECTORS = [
    {
        "key": "ev",
        "prompt": (
            "Use web_search to find the 8 most recent, significant news articles "
            "from the last 48 hours about electric vehicles and automotive industry. "
            "Include EV launches, sales data, charging infrastructure, battery technology, "
            "automaker strategy, and EV policy. "
            "Return ONLY a raw JSON array (no markdown fences, no explanation). "
            "Each element must have: headline (exact article title), "
            "summary (1-2 sentence paraphrase in your own words), "
            "source (publication name), "
            "url (full direct article URL, not a homepage), "
            "time (e.g. '2h ago'), "
            "tags (array of 1-2 from [\"EV\",\"Market\",\"Policy\"]), "
            "sentiment (one emoji: 📈 📉 ⚠️ ✅ ⚡ 🔬 📊 🛠️). "
            "Start with [ end with ]."
        )
    },
    {
        "key": "energy",
        "prompt": (
            "Use web_search to find the 8 most recent, significant news articles "
            "from the last 48 hours about residential energy, rooftop solar, "
            "home battery storage, net metering, solar incentives, and home electrification. "
            "Return ONLY a raw JSON array (no markdown fences, no explanation). "
            "Each element must have: headline (exact article title), "
            "summary (1-2 sentence paraphrase in your own words), "
            "source (publication name), "
            "url (full direct article URL, not a homepage), "
            "time (e.g. '3h ago'), "
            "tags (array of 1-2 from [\"Energy\",\"Market\",\"Policy\"]), "
            "sentiment (one emoji: 📈 📉 ⚠️ ✅ ⚡ 🔬 📊 🛠️). "
            "Start with [ end with ]."
        )
    },
    {
        "key": "v2x",
        "prompt": (
            "Use web_search to find the 8 most recent, significant news articles "
            "from the last 48 hours about Vehicle-to-Everything (V2X) technology: "
            "V2G (vehicle-to-grid), V2H (vehicle-to-home), V2L (vehicle-to-load), "
            "bidirectional EV charging, and EV grid integration. "
            "Return ONLY a raw JSON array (no markdown fences, no explanation). "
            "Each element must have: headline (exact article title), "
            "summary (1-2 sentence paraphrase in your own words), "
            "source (publication name), "
            "url (full direct article URL, not a homepage), "
            "time (e.g. '4h ago'), "
            "tags (array of 1-2 from [\"V2X\",\"Market\",\"Policy\"]), "
            "sentiment (one emoji: 📈 📉 ⚠️ ✅ ⚡ 🔬 📊 🛠️). "
            "Start with [ end with ]."
        )
    }
]


def fetch_sector(sector):
    print(f"Fetching sector: {sector['key']}...")

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": sector["prompt"]}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Extract text blocks only
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")

        # Strip markdown fences
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```', '', text)

        # Extract outermost JSON array
        start = text.find('[')
        end   = text.rfind(']')
        if start == -1 or end == -1 or end <= start:
            print(f"  ERROR: No JSON array found")
            return []

        items = json.loads(text[start:end+1])
        valid = [i for i in items if i.get("headline") and i.get("url", "").startswith("http")]
        print(f"  OK: {len(valid)} articles")
        return valid

    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def main():
    cache = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "ev":     fetch_sector(SECTORS[0]),
        "energy": fetch_sector(SECTORS[1]),
        "v2x":    fetch_sector(SECTORS[2]),
    }

    with open("market-watch-cache.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    total = len(cache["ev"]) + len(cache["energy"]) + len(cache["v2x"])
    print(f"\nDone. {total} total articles written to market-watch-cache.json")


if __name__ == "__main__":
    main()

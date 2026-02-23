#!/usr/bin/env python3
"""
Volt & Watt Market Watch - Daily Pre-fetch
Runs via GitHub Actions each morning.
Fetches EV, Energy, and V2X news via Anthropic API + web search,
writes market-watch-cache.json for the HTML page to consume.
"""

import os, json, re, urllib.request, urllib.error, time
from datetime import datetime, timezone

API_KEY = os.environ["ANTHROPIC_API_KEY"]

EXAMPLE_JSON = (
    '[{"headline": "Title here", "summary": "Summary here.", '
    '"source": "Reuters", "url": "https://example.com/article", '
    '"time": "3h ago", "tags": ["EV"], "sentiment": "📈"}]'
)

SECTORS = [
    {
        "key": "ev",
        "prompt": (
            "Search the web for recent electric vehicle and automotive industry news from the last 7 days. "
            "Find up to 8 articles about EV launches, sales, charging infrastructure, battery technology, automaker strategy, or EV policy. "
            "If fewer than 8 exist, return however many you find - even 2 or 3 is fine. "
            "You MUST return ONLY a JSON array. No intro text, no explanation, no markdown fences. "
            "Start your response with [ and end with ]. "
            'Each object must have: headline (string), summary (string, 1-2 sentences), source (string), '
            'url (string, full URL starting with https), time (string, e.g. "2h ago"), '
            'tags (array of 1-2 from ["EV","Market","Policy"]), sentiment (string, one emoji). '
            "Example format: " + EXAMPLE_JSON
        )
    },
    {
        "key": "energy",
        "prompt": (
            "Search the web for recent residential energy and solar news from the last 7 days. "
            "Find up to 8 articles about rooftop solar, home battery storage, net metering, solar incentives, or home electrification. "
            "If fewer than 8 exist, return however many you find - even 2 or 3 is fine. "
            "You MUST return ONLY a JSON array. No intro text, no explanation, no markdown fences. "
            "Start your response with [ and end with ]. "
            'Each object must have: headline (string), summary (string, 1-2 sentences), source (string), '
            'url (string, full URL starting with https), time (string, e.g. "3h ago"), '
            'tags (array of 1-2 from ["Energy","Market","Policy"]), sentiment (string, one emoji). '
            "Example format: " + EXAMPLE_JSON
        )
    },
    {
        "key": "v2x",
        "prompt": (
            "Search the web for recent news about bidirectional EV charging, vehicle-to-grid V2G, "
            "vehicle-to-home V2H, and EV battery grid integration from the last 7 days. "
            "If fewer than 8 exist, return however many you find - even 2 or 3 is fine. "
            "You MUST return ONLY a JSON array. No intro text, no explanation, no markdown fences. "
            "Start your response with [ and end with ]. "
            'Each object must have: headline (string), summary (string, 1-2 sentences), source (string), '
            'url (string, full URL starting with https), time (string, e.g. "2h ago"), '
            'tags (array with one value: "V2X"), sentiment (string, one emoji). '
            "Example format: " + EXAMPLE_JSON
        )
    }
]


def fetch_sector(sector, retries=3):
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

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
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
                print(f"  ERROR: No JSON array found. Raw text: {text[:400]}")
                return []

            items = json.loads(text[start:end+1])
            valid = [i for i in items if i.get("headline") and i.get("url", "").startswith("http")]
            print(f"  OK: {len(valid)} articles")
            return valid

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 45 * (attempt + 1)
                print(f"  Rate limited (429). Waiting {wait}s before retry {attempt+2}/{retries}...")
                time.sleep(wait)
            else:
                print(f"  ERROR: {e}")
                return []
        except Exception as e:
            print(f"  ERROR: {e}")
            return []
    return []


def main():
    results = {}
    for i, sector in enumerate(SECTORS):
        if i > 0:
            print(f"  Waiting 45s before next sector...")
            time.sleep(45)
        results[sector["key"]] = fetch_sector(sector)

    cache = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "ev":     results.get("ev", []),
        "energy": results.get("energy", []),
        "v2x":    results.get("v2x", []),
    }

    with open("market-watch-cache.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    total = len(cache["ev"]) + len(cache["energy"]) + len(cache["v2x"])
    print(f"\nDone. {total} total articles written to market-watch-cache.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Polymarket Search — find markets + lookup token IDs in one shot.

Usage:
  python3 search.py "US Iran ceasefire"
  python3 search.py "Trump" --limit 5

Output: JSON with events, markets, and token_ids ready for ordering.
"""
import sys, json, argparse
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import gamma_get, GAMMA

def search_v2(query, limit=10):
    r = gamma_get("/search-v2", params={
        "q": query, "optimized": "true",
        "limit_per_type": limit, "type": "events",
        "search_tags": "true", "cache": "true",
    })
    if r.status_code >= 400:
        return []
    data = r.json() if r.text.strip() else {}
    return data.get("events", []) if isinstance(data, dict) else []

def lookup_market(slug):
    """Lookup single market by slug to get clobTokenIds."""
    r = gamma_get("/markets", params={"slug": slug, "limit": 1})
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list) and data:
            return data[0]
    return None

def main():
    parser = argparse.ArgumentParser(description="Search Polymarket")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    events = search_v2(args.query, args.limit)
    if not events:
        print(json.dumps({"error": "No results", "query": args.query}))
        sys.exit(1)

    results = []
    for ev in events:
        event_out = {
            "title": ev.get("title"),
            "slug": ev.get("slug"),
            "markets": [],
        }
        for m in ev.get("markets", []):
            slug = m.get("slug", "")
            question = m.get("question", "")
            outcomes = m.get("outcomes", [])
            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)
            prices = m.get("outcomePrices", [])
            if isinstance(prices, str):
                prices = json.loads(prices)
            
            token_ids = m.get("clobTokenIds")
            if isinstance(token_ids, str):
                token_ids = json.loads(token_ids)

            # If no token_ids from search, lookup by slug
            if not token_ids and slug:
                detail = lookup_market(slug)
                if detail:
                    raw = detail.get("clobTokenIds", [])
                    if isinstance(raw, str):
                        raw = json.loads(raw)
                    token_ids = raw

            market_out = {
                "question": question,
                "slug": slug,
                "active": m.get("active", True),
                "closed": m.get("closed", False),
                "outcomes": [],
            }
            for i, name in enumerate(outcomes):
                entry = {"name": name}
                if i < len(prices):
                    try: entry["price"] = float(prices[i])
                    except: pass
                if token_ids and i < len(token_ids):
                    entry["token_id"] = token_ids[i]
                market_out["outcomes"].append(entry)

            event_out["markets"].append(market_out)
        results.append(event_out)

    print(json.dumps({"query": args.query, "events": results}, indent=2))

if __name__ == "__main__":
    main()

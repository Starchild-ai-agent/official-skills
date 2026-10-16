# Site audit method

How to audit any website with the primitives in `site_tools.py`. These tools
observe; you decide. No step below depends on the site's language, framework
or host. If a step's assumption fails on a site, notice it and adapt.

## 0. Scope with the user

- Start URL(s), plus every page or element the user named (they are must-checks).
- Which viewports matter (default: one desktop around 1280px wide, one phone
  around 390px wide with `mobile=True`).
- Are writes allowed? Default: no. Read-only clicks only.

## 1. Build the page map from several sources

```python
from exports import fetch, extract_refs, parse_sitemap, browse, check_urls, same_host

home = fetch(start)
refs = extract_refs(home["body"], home["final_url"])
robots = fetch(urljoin(start, "/robots.txt"))        # look for "Sitemap:" lines yourself
sm = parse_sitemap(fetch(urljoin(start, "/sitemap.xml"))["body"])   # follow sm["sitemaps"]
rendered = browse(start)                               # rendered links + controls
```

Read the results instead of filtering them blindly:

- `a[href]` / `area[href]`: ordinary navigation.
- `inline-script` / `attr[on…]` / `attr[data-…]`: candidate routes, API
  endpoints and assets. Open the surrounding script (`home["body"]`) to see
  what the strings mean, such as a route table or a redirect map. Pages that
  only exist here are the ones a link-only crawler misses.
- `link[rel=canonical|alternate]`, `meta[refresh]`, `form[action]`: separate
  signals. Note them, and think before fetching (a form action may be a write).
- Rendered links missing from the raw HTML mean JS builds navigation. Use
  `browse` for every page of that kind.

Visit each same-site page you found and repeat the extraction. This is a loop
you write. Keep a `seen` set, normalise only what you have checked is
equivalent on this site, and stop at a page budget you state in the report.

Reconcile: compare sitemap pages, linked pages, script-referenced pages and
user-named pages. Pages in one source but not another are findings (orphans,
stale sitemap entries, hidden routes).

## 2. Learn this site's error signature

```python
real = fetch(some_known_good_page)
probe = fetch(urljoin(start, "/" + uuid4().hex))
```

Compare status, `final_url`, `<title>`, body length and visible text:

- `probe.status` is 404/410: the server tells the truth, so trust status codes.
- `probe.status` is 200 but the title or text differs from real pages: soft-404.
  A page that returns 200 and looks like the probe is missing.
- The probe redirects to home or a login page: same idea. A "working" link that
  lands there is suspicious.
- A 403/503 bot challenge appears even for real pages: you are blocked. Say
  so; do not report pages as broken or fine.

If unsure, render both with `browse` and compare `title` and `text_sample`.

## 3. Check every reference

- `check_urls(urls)` (HEAD). Re-check 403/405/501 and errors with
  `method="GET"`, because many servers reject HEAD. Re-check timeouts and 5xx
  once before calling them broken.
- Group the results yourself: same-site pages, same-site assets, third-party.
  Third-party 401/403/429 or LinkedIn-style refusals usually mean "cannot
  verify from a bot". Report them separately.
- For same-site 200s, apply the step-2 signature to catch soft-404s.
- For each broken URL, record where it is referenced (the page and the `source`
  from `extract_refs`). That is what the user needs to fix it.

## 4. Click what users click

Choose targets from `browse(url)["controls"]` and `["links"]`: navigation,
logo, CTAs, menus/toggles (`aria_expanded`), anything the user named, and a
sample of repeated components. Then:

```python
r = browse(url, actions=[{"click": "#menu"}, {"click": "a.logo"}], viewport=(1280, 800))
m = browse(url, actions=[...], viewport=(390, 844), mobile=True)
```

Read each action record:

| Observation | What it suggests |
|---|---|
| `navigations` has a status ≥400 | the click leads to an error page |
| `new_pages[i].status` ≥400 or None | the new tab is broken or unverified. Never use the original page's status |
| `downloads[i].failure` set | the download failed |
| `url_after` changed only in `#…` or via pushState, `dom_changed` | in-page navigation worked |
| no URL change, no new page, `dom_changed` False, no new links | nothing visible happened. Check whether that is expected (already on that page? menu already open?) before calling it broken |
| `element.topmost_at_center.is_element_or_child` False | another element covers the target at this viewport |
| new `page_errors` entries during the action | the handler threw |
| `error` "no visible match" | the target is hidden at this viewport (e.g. inside a collapsed menu). Open the menu first, then retry |
| `blocked_writes` not empty | something tried to write (`phase` says when: `load`, `action[i]`, `after-actions`). You did not test the real effect; say so |
| `new_pages[i].timeout` True | the new window did not answer within `popup_timeout_ms`. Not verified; re-check it with a larger timeout or `fetch`, never call it fine |

Menus and lazy content: click the toggle, then read the action's `new_links`.
Scroll (`{"scroll": "bottom"}`) and check again for lazy-loaded links.
Paginate by clicking the control you identified, never by guessing URLs.

## 5. Explain before reporting

For every anomaly, write one sentence on why you believe it is (or is not) a
user-visible problem, citing the observation. If you can't explain it,
report it as "unexplained" with the raw evidence. Don't drop it, and don't
call it broken.

## 6. Report

- Coverage: pages found per source, pages checked, viewports, budget limits hit.
- Broken: URL / element, where referenced, observation, viewport, screenshot if taken.
- Could not verify: what and why (blocked, auth, writes, Playwright missing).
- Not covered: what you skipped.
- If the user named a page or element, answer about it explicitly.

Never write "everything works" when steps 1–4 were incomplete.

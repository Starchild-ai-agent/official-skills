"""
Site link audit + click verification for the web-crawler skill.

Why this exists (root-caused 2026-10-16): an agent asked to "check all links on
every page" hand-rolled a crawler that only followed <a href> in the raw HTML.
It missed a live page that was referenced only from an inline script config
(no <a> link, no sitemap), never rendered or clicked anything, and then told the
user "everything works" with no stated coverage. When the user pushed back
("really? none of the links 404?") it re-ran the same method.

This module makes the robust path the default:
  1. Discover pages from several sources, not just <a>: sitemap(s) via
     robots.txt, <a>/<area>, canonical/alternate, quoted same-site paths in
     inline scripts / data-* / onclick, and (if Playwright is available) the
     rendered DOM.
  2. Check every discovered URL; classify known false positives instead of
     reporting them as broken.
  3. Return an explicit coverage block + blind spots so the report can never
     claim more than was checked.
  4. click_check(): open one page in a real browser at desktop + mobile widths,
     click a specific element, report where it lands, whether something covers
     it, console errors. Use this whenever the user names a page/button.

Pure stdlib except optional Playwright. Target sites are fetched directly
(public pages, no credentials involved).
"""
import re
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_ASSET_RE = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|avif|ico|css|js|mjs|map|woff2?|ttf|otf|eot|"
    r"mp4|webm|mp3|wav|pdf|zip|json|xml|txt)(\?|$)", re.I)
# Quoted site-relative paths inside scripts / attributes: "/quero-fazer-parte"
_SCRIPT_PATH_RE = re.compile(r"""["'](/[A-Za-z0-9][A-Za-z0-9._~%/\-]*(?:\?[^"'\s<>]*)?)["']""")
_ABS_URL_RE = re.compile(r"""https?://[^\s"'<>\\)]+""")

# Known non-breakages: report them separately, never as "broken".
FALSE_POSITIVES = [
    (re.compile(r"/cdn-cgi/l/email-protection"),
     "Cloudflare email obfuscation; decoded to mailto: by JS in real browsers"),
    (re.compile(r"^https?://fonts\.(googleapis|gstatic)\.com/?$"),
     "preconnect/dns-prefetch hint, not a clickable link"),
]


def _same_site(a, b):
    ha, hb = urlparse(a).hostname or "", urlparse(b).hostname or ""
    strip = lambda h: h[4:] if h.startswith("www.") else h  # noqa: E731
    return strip(ha) == strip(hb)


def _norm(url):
    url = urldefrag(url.strip())[0]
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return None
    return url


def false_positive_note(url):
    for rx, note in FALSE_POSITIVES:
        if rx.search(url):
            return note
    return None


class _Extractor(HTMLParser):
    """Collect URLs by discovery source."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = {"a": [], "asset": [], "hint": [], "meta": [], "script": []}
        self._in_script = False
        self._script_buf = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in ("a", "area") and d.get("href"):
            self.found["a"].append(d["href"])
        elif tag == "link" and d.get("href"):
            rel = (d.get("rel") or "").lower()
            if any(r in rel for r in ("preconnect", "dns-prefetch")):
                self.found["hint"].append(d["href"])
            elif any(r in rel for r in ("canonical", "alternate", "next", "prev")):
                self.found["meta"].append(d["href"])
            else:
                self.found["asset"].append(d["href"])
        elif tag in ("img", "script", "source", "iframe", "video", "audio") and d.get("src"):
            self.found["asset"].append(d["src"])
        elif tag == "form" and d.get("action"):
            self.found["a"].append(d["action"])
        if tag == "script" and not d.get("src"):
            self._in_script = True
        # Navigation hidden in attributes: data-href, data-url, onclick="location=..."
        for k, v in attrs:
            if not v:
                continue
            if k.startswith("data-") or k.startswith("on"):
                self.found["script"].extend(_SCRIPT_PATH_RE.findall(v))
                self.found["script"].extend(_ABS_URL_RE.findall(v))
                if k in ("data-href", "data-url", "data-link") and v.startswith("/"):
                    self.found["script"].append(v)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            body = "".join(self._script_buf)
            self.found["script"].extend(_SCRIPT_PATH_RE.findall(body))
            self.found["script"].extend(_ABS_URL_RE.findall(body))
            self._script_buf, self._in_script = [], False

    def handle_data(self, data):
        if self._in_script:
            self._script_buf.append(data)


def extract_urls(html, base_url):
    """Return {source: set(absolute_url)} for one page.
    Sources: a, asset, hint, meta, script (script = quoted paths/URLs found in
    inline scripts or data-*/on* attributes — the class of links a plain <a>
    crawler misses)."""
    ex = _Extractor()
    try:
        ex.feed(html)
        ex.close()
    except Exception:  # malformed HTML: keep what we got
        pass
    base = base_url
    m = re.search(r"<base[^>]+href=[\"']([^\"']+)", html, re.I)
    if m:
        base = urljoin(base_url, m.group(1))
    out = {}
    for src, vals in ex.found.items():
        s = set()
        for v in vals:
            u = _norm(urljoin(base, v))
            if not u:
                continue
            if src == "script":
                # only same-site page-like references; scripts are noisy
                if not _same_site(u, base_url) or _ASSET_RE.search(urlparse(u).path):
                    continue
            s.add(u)
        out[src] = s
    return out


def parse_sitemap(xml):
    """Return (page_urls, child_sitemap_urls) from a sitemap or sitemap index."""
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml or "", re.I)
    if re.search(r"<sitemapindex", xml or "", re.I):
        return [], locs
    return locs, []


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
_CTX = ssl.create_default_context()


def _fetch(url, method="GET", timeout=15, read=True):
    """Return dict(status, final_url, body, error). Never raises."""
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            ctype = r.headers.get("Content-Type", "")
            body = r.read(3_000_000).decode("utf-8", "ignore") if read else ""
            return {"status": r.status, "final_url": r.geturl(), "body": body,
                    "content_type": ctype, "error": None}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "final_url": url, "body": "", "content_type": "",
                "error": None}
    except Exception as e:  # DNS, TLS, timeout
        return {"status": None, "final_url": url, "body": "", "content_type": "",
                "error": f"{type(e).__name__}: {e}"[:200]}


def check_url(url, timeout=15):
    """HEAD first, fall back to GET when servers reject HEAD (403/405/501)."""
    r = _fetch(url, "HEAD", timeout, read=False)
    if r["status"] in (None, 400, 403, 405, 429, 501) or (r["status"] or 0) >= 500:
        r = _fetch(url, "GET", timeout, read=False)
    return r


def _render_links(url, timeout_ms=30000):
    """Rendered-DOM hrefs via Playwright, or None if Playwright is unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(user_agent=UA)
            pg.goto(url, wait_until="networkidle", timeout=timeout_ms)
            hrefs = pg.eval_on_selector_all(
                "a[href], area[href], [data-href]",
                "els => els.map(e => e.href || e.getAttribute('data-href'))")
            b.close()
            return {u for u in (_norm(urljoin(url, h)) for h in hrefs if h) if u}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Site audit
# ---------------------------------------------------------------------------
def _discover_sitemaps(origin, timeout):
    """Sitemap URLs from robots.txt + the conventional location."""
    found, robots_ok = [], False
    r = _fetch(origin + "/robots.txt", timeout=timeout)
    if r["status"] == 200 and "html" not in r["content_type"]:
        robots_ok = True
        found += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", r["body"])
    found.append(origin + "/sitemap.xml")
    return list(dict.fromkeys(found)), robots_ok


def audit_site(start_url, max_pages=150, render=True, check_external=True,
               timeout=15, workers=8, extra_urls=None):
    """Crawl one site and check every link it references.

    extra_urls: URLs the USER named (e.g. a page they say is broken). They are
    always crawled and checked even if nothing links to them — never skip what
    the user pointed at.

    Returns a dict:
      pages:    [{url, status, found_via:[...]}]          same-site HTML pages crawled
      links:    [{url, status, ok, kind, found_via, referrers, note}]
      broken:   subset of links that are really broken (false positives removed)
      false_positives: links that fail for bots but work for people (with reason)
      coverage: what was and wasn't done — ALWAYS show this to the user
    """
    start_url = _norm(start_url)
    p = urlparse(start_url)
    origin = f"{p.scheme}://{p.netloc}"

    found_via = {}      # url -> set(source)
    referrers = {}      # url -> set(page)
    kinds = {}          # url -> page|asset|hint|external

    def note(url, source, page=None, kind=None):
        found_via.setdefault(url, set()).add(source)
        if page:
            referrers.setdefault(url, set()).add(page)
        if kind and kinds.get(url) != "page":
            kinds[url] = kind

    # 1. seeds: start page, user-named URLs, sitemap(s)
    queue = [start_url]
    note(start_url, "start", kind="page")
    for u in extra_urls or []:
        u = _norm(urljoin(start_url, u))
        if u:
            queue.append(u)
            note(u, "user", kind="page")
    sitemaps, robots_ok = _discover_sitemaps(origin, timeout)
    sitemap_ok, seen_maps = False, set()
    while sitemaps and len(seen_maps) < 20:
        sm = sitemaps.pop(0)
        if sm in seen_maps:
            continue
        seen_maps.add(sm)
        r = _fetch(sm, timeout=timeout)
        if r["status"] == 200 and "<loc>" in r["body"].lower():
            sitemap_ok = True
            pages, children = parse_sitemap(r["body"])
            sitemaps += children
            for u in pages:
                u = _norm(u)
                if u and _same_site(u, start_url):
                    queue.append(u)
                    note(u, "sitemap", kind="page")

    # 2. crawl same-site pages (BFS)
    crawled, rendered_pages, render_available = {}, 0, None
    while queue and len(crawled) < max_pages:
        url = queue.pop(0)
        if url in crawled:
            continue
        r = _fetch(url, timeout=timeout)
        crawled[url] = r["status"]
        if r["status"] != 200 or "html" not in (r["content_type"] or "html"):
            continue
        page_url = r["final_url"]
        groups = extract_urls(r["body"], page_url)
        if render and render_available is not False and rendered_pages < 30:
            dom = _render_links(page_url)
            render_available = dom is not None
            if dom is not None:
                rendered_pages += 1
                groups["rendered"] = dom - groups.get("a", set())
        for src, urls in groups.items():
            for u in urls:
                same = _same_site(u, start_url)
                if src == "hint":
                    note(u, src, url, "hint")
                elif src == "asset" or _ASSET_RE.search(urlparse(u).path):
                    note(u, src, url, "asset")
                elif same:
                    note(u, src, url, "page")
                    if u not in crawled:
                        queue.append(u)
                else:
                    note(u, src, url, "external")

    # 3. check every non-crawled URL
    to_check = [u for u in found_via if u not in crawled
                and (check_external or kinds.get(u) != "external")]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = dict(zip(to_check, ex.map(lambda u: check_url(u, timeout), to_check)))

    links, broken, fps, script_only = [], [], [], []
    for u, srcs in found_via.items():
        if u in crawled:
            status = crawled[u]
        elif u in results:
            status = results[u]["status"]
        else:
            continue
        ok = status is not None and status < 400
        row = {"url": u, "status": status, "ok": ok, "kind": kinds.get(u, "page"),
               "found_via": sorted(srcs), "referrers": sorted(referrers.get(u, []))[:5],
               "note": None}
        if not ok:
            fp = false_positive_note(u) or (
                "hint" if kinds.get(u) == "hint" else None)
            if fp:
                row["note"] = fp if fp != "hint" else "resource hint, not a clickable link"
                fps.append(row)
            elif status in (401, 403, 429, 999) and kinds.get(u) == "external":
                row["note"] = "blocks bots; verify manually in a browser"
                fps.append(row)
            elif set(srcs) <= {"script"}:
                # A path string inside JS (route table, redirect rule, config) is
                # not necessarily something a visitor can click. Report it for
                # review; do not call it a broken link without a click_check().
                row["note"] = "only referenced inside script code, not a clickable link"
                script_only.append(row)
            else:
                broken.append(row)
        links.append(row)

    pages = [{"url": u, "status": s, "found_via": sorted(found_via.get(u, []))}
             for u, s in crawled.items()]
    js_only = [pg["url"] for pg in pages
               if pg["status"] == 200 and set(pg["found_via"]) & {"script", "rendered"}
               and not set(pg["found_via"]) & {"a", "sitemap", "start"}]
    blind = [
        "Pages that nothing references (no link, no script, no sitemap) cannot be "
        "discovered by any crawler — ask the user for those URLs.",
        "Status checks prove a URL loads; they do not prove a button works. For a "
        "specific button/flow, run click_check() in a real browser.",
    ]
    if not render_available:
        blind.append("Rendered DOM was NOT inspected (Playwright unavailable or "
                     "disabled): links injected by JavaScript may be missing.")
    if len(crawled) >= max_pages:
        blind.append(f"Stopped at max_pages={max_pages}; the site may have more pages.")
    if not check_external:
        blind.append("External links were not checked.")
    coverage = {
        "pages_crawled": len(crawled), "urls_checked": len(links),
        "robots_txt": robots_ok, "sitemap": sitemap_ok,
        "rendered_dom": bool(render_available), "rendered_pages": rendered_pages,
        "pages_found_only_via_js_or_script": js_only,
        "user_named_urls": [u for u, s in found_via.items() if "user" in s],
        "blind_spots": blind,
    }
    return {"start_url": start_url, "pages": pages, "links": links,
            "broken": broken, "false_positives": fps,
            "script_only_unreachable": script_only, "coverage": coverage}


# ---------------------------------------------------------------------------
# Click verification (real browser)
# ---------------------------------------------------------------------------
VIEWPORTS = (("desktop", 1280, 800, False), ("mobile", 390, 844, True))

# Runs on the already-located element (Playwright passes it as `target`), so
# Playwright-only selectors like text=/alt= never reach document.querySelector.
_COVER_JS = """(target, [x, y]) => {
  const e = document.elementFromPoint(x, y);
  if (!e) return null;
  return {tag: e.tagName.toLowerCase(), cls: (e.className || '').toString().slice(0, 80),
          inside_target: target === e || target.contains(e)};
}"""


def click_check(url, target, viewports=VIEWPORTS, timeout_ms=30000):
    """Open `url` in headless Chromium, click `target`, report what happened.

    target: CSS selector ("a.logo"), or "text=Numa", or "alt=Numa" (image alt),
            or "href=index.html". Use exactly what the user described.
    Returns {viewport: {...}} with: found, visible, covered_by, href,
    final_url, final_status, console_errors, popup_url, error.
    Requires Playwright; returns {"error": ...} if unavailable — then say so
    instead of claiming the button works.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {"error": f"Playwright unavailable: {e}"}
    if target.startswith("alt="):
        sel = f'a:has(img[alt*="{target[4:]}" i]), img[alt*="{target[4:]}" i]'
    elif target.startswith("href="):
        sel = f'a[href*="{target[5:]}"]'
    else:
        sel = target
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, w, h, mobile in viewports:
            res = {"found": False, "visible": False, "covered_by": None, "href": None,
                   "final_url": None, "final_status": None, "console_errors": [],
                   "popup_url": None, "error": None}
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile,
                                has_touch=mobile, user_agent=UA)
            pg = ctx.new_page()
            pg.on("console", lambda m, r=res: r["console_errors"].append(m.text[:200])
                  if m.type == "error" else None)
            statuses = {}
            pg.on("response", lambda resp: statuses.__setitem__(resp.url, resp.status))
            try:
                pg.goto(url, wait_until="networkidle", timeout=timeout_ms)
                loc = pg.locator(sel)
                visible = [i for i in range(loc.count()) if loc.nth(i).is_visible()]
                res["found"] = loc.count() > 0
                if not visible:
                    res["error"] = ("element not visible at this width"
                                    if res["found"] else "element not found")
                else:
                    el = loc.nth(visible[0])
                    res["visible"] = True
                    res["href"] = el.evaluate(
                        "e => (e.closest('a') || e).getAttribute('href')")
                    box = el.bounding_box()
                    if box:
                        cover = el.evaluate(_COVER_JS, [box["x"] + box["width"] / 2,
                                                         box["y"] + box["height"] / 2])
                        if cover and not cover["inside_target"]:
                            res["covered_by"] = f'{cover["tag"]}.{cover["cls"]}'
                    before = pg.url
                    try:
                        with ctx.expect_page(timeout=3000) as pop:
                            el.click(timeout=8000)
                        res["popup_url"] = pop.value.url
                    except Exception:
                        pass  # no popup: normal same-tab navigation
                    try:
                        pg.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    res["final_url"] = pg.url
                    res["final_status"] = statuses.get(pg.url)
                    if pg.url == before and not res["popup_url"]:
                        res["error"] = "click did not navigate (no URL change, no popup)"
            except Exception as e:
                res["error"] = f"{type(e).__name__}: {e}"[:300]
            ctx.close()
            out[name] = res
        b.close()
    return out


def click_verdict(r):
    """OK only when the click navigated somewhere that loaded (status < 400) and
    nothing covered the element. HTTP error -> FAIL; unknown status -> UNVERIFIED."""
    if r.get("error") or r.get("covered_by"):
        return "FAIL"
    if r.get("popup_url") and r.get("final_status") is None:
        return "UNVERIFIED"  # popup opened; its status is not captured
    st = r.get("final_status")
    if st is None:
        return "UNVERIFIED"
    return "FAIL" if st >= 400 else "OK"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def format_report(audit, clicks=None):
    """Markdown report. Coverage + blind spots are always included — never send
    a link-check verdict without them."""
    c = audit["coverage"]
    L = [f"# Link audit: {audit['start_url']}", "",
         f"**Result:** {len(audit['broken'])} broken, "
         f"{len(audit['false_positives'])} bot-only failures (not user-facing), "
         f"{len(audit.get('script_only_unreachable', []))} script-only refs to review, "
         f"{c['urls_checked']} URLs checked across {c['pages_crawled']} pages.", ""]
    if audit["broken"]:
        L += ["## Broken", "| URL | Status | Found on | Found via |", "|---|---|---|---|"]
        for r in audit["broken"]:
            L.append(f"| {r['url']} | {r['status']} | {', '.join(r['referrers'][:2]) or '-'}"
                     f" | {', '.join(r['found_via'])} |")
        L.append("")
    if audit["false_positives"]:
        L += ["## Fails for bots only (not broken for visitors)"]
        L += [f"- {r['url']} ({r['status']}): {r['note']}" for r in audit["false_positives"]]
        L.append("")
    if audit.get("script_only_unreachable"):
        L += ["## Referenced only inside scripts, not reachable (review, not counted as broken)"]
        L += [f"- {r['url']} ({r['status']}) in script on "
              f"{', '.join(r['referrers'][:2]) or '-'}" for r in audit["script_only_unreachable"]]
        L.append("")
    L += ["## Pages crawled"]
    L += [f"- {pg['status']} {pg['url']} (via {', '.join(pg['found_via'])})"
          for pg in audit["pages"]]
    if clicks:
        L += ["", "## Click checks (real browser)"]
        for target, by_vp in clicks.items():
            if "error" in by_vp and isinstance(by_vp["error"], str):
                L.append(f"- {target}: NOT VERIFIED — {by_vp['error']}")
                continue
            for vp, r in by_vp.items():
                verdict = click_verdict(r)
                L.append(f"- {target} [{vp}]: {verdict} → {r['final_url'] or r['popup_url']}"
                         f" (status {r['final_status']}, href={r['href']}, "
                         f"covered_by={r['covered_by']}, console_errors="
                         f"{len(r['console_errors'])}{', ' + r['error'] if r['error'] else ''})")
    L += ["", "## Coverage",
          f"- robots.txt: {'yes' if c['robots_txt'] else 'no'}; sitemap: "
          f"{'yes' if c['sitemap'] else 'no'}; rendered DOM: "
          f"{'yes (' + str(c['rendered_pages']) + ' pages)' if c['rendered_dom'] else 'no'}"]
    if c["pages_found_only_via_js_or_script"]:
        L.append("- Pages found ONLY via scripts/rendered DOM (a plain <a> crawler misses "
                 "these): " + ", ".join(c["pages_found_only_via_js_or_script"]))
    if c["user_named_urls"]:
        L.append("- User-named URLs checked: " + ", ".join(c["user_named_urls"]))
    L += ["", "## Not covered"] + [f"- {b}" for b in c["blind_spots"]]
    return "\n".join(L)

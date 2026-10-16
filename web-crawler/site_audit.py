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
import os
import re
import ssl
import time
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


class _Renderer:
    """One headless Chromium reused for the whole audit; a fresh context per page.
    A failure on one page never disables rendering for the rest."""

    def __init__(self, timeout_ms=30000):
        self.timeout_ms = timeout_ms
        self.unavailable = None
        self._pw = self._b = None

    def _start(self):
        if self._b or self.unavailable:
            return
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._b = self._pw.chromium.launch()
        except Exception as e:
            self.unavailable = f"{type(e).__name__}: {e}"[:200]
            self.close()

    def render(self, url):
        """Return (set_of_urls, None) or (None, reason)."""
        self._start()
        if self.unavailable:
            return None, "browser unavailable: " + self.unavailable
        ctx = None
        try:
            ctx = self._b.new_context(user_agent=UA)
            pg = ctx.new_page()
            pg.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
            hrefs = pg.eval_on_selector_all(
                "a[href], area[href], [data-href]",
                "els => els.map(e => e.href || e.getAttribute('data-href'))")
            return {u for u in (_norm(urljoin(url, h)) for h in hrefs if h) if u}, None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"[:200]
        finally:
            if ctx:
                try:
                    ctx.close()
                except Exception:
                    pass

    def close(self):
        for obj, fn in ((self._b, "close"), (self._pw, "stop")):
            if obj:
                try:
                    getattr(obj, fn)()
                except Exception:
                    pass
        self._pw = self._b = None


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


# Statuses that mean "this checker was refused", not "the link is broken".
RESTRICTED_STATUSES = (401, 403, 407, 429, 451, 999)


def audit_site(start_url, max_pages=150, render=True, check_external=True,
               timeout=15, workers=8, extra_urls=None, max_render=30,
               max_seconds=600, render_timeout_ms=30000):
    """Crawl one site and check every link it references.

    extra_urls: URLs the USER named. Always crawled and checked even if nothing
    links to them — never skip what the user pointed at.
    Budgets: max_pages, max_render (pages rendered in a browser), max_seconds
    (crawl wall time). Hitting any budget is reported, never silent.

    Returns a dict:
      pages:      [{url, status, found_via, render, render_note, fetch_error}]
      links:      [{url, status, ok, kind, found_via, referrers, note}]
      broken:     really broken (HTTP error / unreachable, not restricted)
      restricted: refused this checker (401/403/429/...) — UNVERIFIED, needs a browser
      false_positives: mechanism-proven non-breakages (Cloudflare email
                  protection, preconnect hints)
      script_only_unreachable: path strings in JS that 404 — review items
      coverage:   what was and wasn't done — ALWAYS show this to the user
    """
    start_url = _norm(start_url)
    p = urlparse(start_url)
    origin = f"{p.scheme}://{p.netloc}"
    t0 = time.monotonic()

    found_via, referrers, kinds = {}, {}, {}

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

    # 2. crawl same-site pages (BFS), per-page fetch + render log
    crawled, page_log, rendered_pages, budget_hit = {}, {}, 0, None
    renderer = _Renderer(render_timeout_ms) if render else None
    try:
        while queue:
            if len(crawled) >= max_pages:
                budget_hit = f"max_pages={max_pages}"
                break
            if time.monotonic() - t0 > max_seconds:
                budget_hit = f"max_seconds={max_seconds}"
                break
            url = queue.pop(0)
            if url in crawled:
                continue
            r = _fetch(url, timeout=timeout)
            crawled[url] = r["status"]
            log = page_log[url] = {"fetch_error": r["error"], "render": "skipped",
                                   "render_note": None}
            if r["status"] != 200 or "html" not in (r["content_type"] or "html"):
                log["render_note"] = "not an HTML 200 page"
                continue
            page_url = r["final_url"]
            groups = extract_urls(r["body"], page_url)
            if not render:
                log["render_note"] = "rendering disabled"
            elif rendered_pages >= max_render:
                log["render_note"] = f"max_render={max_render} reached"
            else:
                dom, err = renderer.render(page_url)
                if dom is None:
                    log["render"] = "unavailable" if renderer.unavailable else "failed"
                    log["render_note"] = err
                else:
                    log["render"] = "rendered"
                    rendered_pages += 1
                    groups["rendered"] = dom - groups.get("a", set())
            for src, urls in groups.items():
                for u in urls:
                    if src == "hint":
                        note(u, src, url, "hint")
                    elif src == "asset" or _ASSET_RE.search(urlparse(u).path):
                        note(u, src, url, "asset")
                    elif _same_site(u, start_url):
                        note(u, src, url, "page")
                        if u not in crawled:
                            queue.append(u)
                    else:
                        note(u, src, url, "external")
    finally:
        if renderer:
            renderer.close()
    unvisited = sorted({u for u in queue if u not in crawled})

    # 3. check every non-crawled URL
    to_check = [u for u in found_via if u not in crawled and u not in unvisited
                and (check_external or kinds.get(u) != "external")]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = dict(zip(to_check, ex.map(lambda u: check_url(u, timeout), to_check)))

    links, broken, restricted, fps, script_only = [], [], [], [], []
    for u, srcs in found_via.items():
        if u in crawled:
            status, err = crawled[u], page_log.get(u, {}).get("fetch_error")
        elif u in results:
            status, err = results[u]["status"], results[u]["error"]
        else:
            continue
        ok = status is not None and status < 400
        row = {"url": u, "status": status, "ok": ok, "kind": kinds.get(u, "page"),
               "found_via": sorted(srcs), "referrers": sorted(referrers.get(u, []))[:5],
               "note": err}
        if not ok:
            fp = false_positive_note(u) or (
                "resource hint, not a clickable link" if kinds.get(u) == "hint" else None)
            if fp:
                row["note"] = fp
                fps.append(row)
            elif status in RESTRICTED_STATUSES:
                row["note"] = (f"refused this checker ({status}); not verified either "
                               "way — open it in a real browser before concluding")
                restricted.append(row)
            elif set(srcs) <= {"script"}:
                row["note"] = "only referenced inside script code, not a clickable link"
                script_only.append(row)
            else:
                broken.append(row)
        links.append(row)

    pages = [{"url": u, "status": s, "found_via": sorted(found_via.get(u, [])),
              **page_log.get(u, {})} for u, s in crawled.items()]
    html_pages = [pg for pg in pages if pg.get("render_note") != "not an HTML 200 page"]
    render_counts = {}
    for pg in html_pages:
        render_counts[pg["render"]] = render_counts.get(pg["render"], 0) + 1
    js_only = [pg["url"] for pg in pages
               if pg["status"] == 200 and set(pg["found_via"]) & {"script", "rendered"}
               and not set(pg["found_via"]) & {"a", "sitemap", "start"}]
    blind = [
        "Pages that nothing references (no link, no script, no sitemap) cannot be "
        "discovered by any crawler — ask the user for those URLs.",
        "Status checks prove a URL loads; they do not prove a button works. For a "
        "specific button/flow, run click_check() in a real browser.",
        "Content inside menus, tabs, lazy-loaded sections and 'load more' is only "
        "seen if it is in the HTML or the initially rendered DOM.",
    ]
    if rendered_pages == 0:
        why = (renderer.unavailable if renderer and renderer.unavailable
               else "disabled" if not render else "every render failed")
        blind.append(f"Rendered DOM was NOT inspected ({why}): links injected by "
                     "JavaScript may be missing.")
    elif rendered_pages < len(html_pages):
        blind.append(f"{len(html_pages) - rendered_pages} of {len(html_pages)} HTML pages "
                     "were not rendered (see per-page render column): JS-injected links "
                     "on those pages may be missing.")
    if budget_hit:
        blind.append(f"Stopped at {budget_hit}; {len(unvisited)} discovered pages were "
                     "not visited or checked.")
    if restricted:
        blind.append(f"{len(restricted)} URLs refused this checker (401/403/429...); "
                     "they are unverified, not confirmed working.")
    if not check_external:
        blind.append("External links were not checked.")
    coverage = {
        "pages_crawled": len(crawled), "urls_checked": len(links),
        "robots_txt": robots_ok, "sitemap": sitemap_ok,
        "rendered_dom": rendered_pages > 0, "rendered_pages": rendered_pages,
        "render_counts": render_counts, "budget_hit": budget_hit,
        "unvisited": unvisited, "elapsed_s": round(time.monotonic() - t0, 1),
        "pages_found_only_via_js_or_script": js_only,
        "user_named_urls": [u for u, s in found_via.items() if "user" in s],
        "blind_spots": blind,
    }
    return {"start_url": start_url, "pages": pages, "links": links,
            "broken": broken, "restricted": restricted, "false_positives": fps,
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

# Cheap page-state fingerprint to detect in-page changes (menu, tab, dialog).
_STATE_JS = """() => {
  const vis = [...document.querySelectorAll('body *')]
    .filter(e => e.getClientRects().length).length;
  const aria = [...document.querySelectorAll('[aria-expanded],[aria-selected],[aria-pressed],[open]')]
    .map(e => [e.getAttribute('aria-expanded'), e.getAttribute('aria-selected'),
               e.getAttribute('aria-pressed'), e.hasAttribute('open')].join(':')).join(',');
  const dlg = document.querySelectorAll('dialog[open],[aria-modal="true"]').length;
  return [vis, aria, dlg, (document.body && document.body.innerText || '').length].join('|');
}"""

# outcome -> what the click demonstrably did
OUTCOMES = ("navigation", "popup", "download", "anchor", "client_navigation",
            "dom_change", "no_change")
EXPECTATIONS = {
    "navigate": {"navigation", "popup", "client_navigation"},
    "popup": {"popup"},
    "download": {"download"},
    "anchor": {"anchor"},
    "change": set(OUTCOMES) - {"no_change"},
}


def _target_selector(target):
    if target.startswith("alt="):
        return f'a:has(img[alt*="{target[4:]}" i]), img[alt*="{target[4:]}" i]'
    if target.startswith("href="):
        return f'a[href*="{target[5:]}"]'
    return target


def click_check(url, target, viewports=VIEWPORTS, timeout_ms=30000, expect=None,
                evidence_dir=None, settle_ms=1500):
    """Open `url` in headless Chromium, click `target`, report what happened.

    target: CSS selector ("a.logo"), "text=Numa", "alt=Numa", or "href=index.html".
    expect: optional "navigate" | "popup" | "download" | "anchor" | "change".
            Without it, an in-page change is reported as CHANGED (a fact), not
            as OK/FAIL — whether it is correct needs an expectation.
    evidence_dir: if set, a screenshot is saved for every non-OK result.

    Low-risk by design: clicks only the one named element; never fills or
    submits forms. Side-effecting flows (submit, pay, delete) need explicit
    user authorization and are out of scope here.

    Returns {viewport: result}; each result has `outcome`, `verdict`, `reason`,
    final_url/final_status, popup_url, download, covered_by, click_error,
    console_errors, evidence. Returns {"error": ...} if Playwright is missing —
    then report NOT VERIFIED.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {"error": f"Playwright unavailable: {e}"}
    if expect is not None and expect not in EXPECTATIONS:
        raise ValueError(f"expect must be one of {sorted(EXPECTATIONS)}")
    sel = _target_selector(target)
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, w, h, mobile in viewports:
            res = {"found": False, "visible": False, "covered_by": None, "href": None,
                   "outcome": None, "final_url": None, "final_status": None,
                   "popup_url": None, "download": None, "console_errors": [],
                   "click_error": None, "error": None, "expect": expect,
                   "evidence": None}
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile,
                                has_touch=mobile, user_agent=UA, accept_downloads=True)
            pg = ctx.new_page()
            opened, downloads, post = [], [], {"on": False, "nav": {}}
            nav_status = {}

            def on_resp(resp, post=post, nav_status=nav_status):
                try:
                    if resp.request.is_navigation_request():
                        nav_status[resp.url] = resp.status
                        if post["on"]:
                            post["nav"][resp.url] = resp.status
                except Exception:
                    pass
            ctx.on("response", on_resp)
            ctx.on("page", lambda pp, opened=opened: opened.append(pp))
            pg.on("download", lambda d, downloads=downloads: downloads.append(d))
            pg.on("console", lambda m, r=res: r["console_errors"].append(m.text[:200])
                  if m.type == "error" else None)
            shot_page = pg
            try:
                pg.goto(url, wait_until="networkidle", timeout=timeout_ms)
                loc = pg.locator(sel)
                n = loc.count()
                visible = [i for i in range(n) if loc.nth(i).is_visible()]
                res["found"] = n > 0
                if not visible:
                    res["error"] = ("element not visible at this width" if n
                                    else "element not found")
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
                    before_url, before_state = pg.url, pg.evaluate(_STATE_JS)
                    post["on"] = True
                    try:
                        el.click(timeout=8000)
                    except Exception as e:
                        res["click_error"] = f"{type(e).__name__}: {e}"[:300]
                    if not res["click_error"]:
                        pg.wait_for_timeout(settle_ms)
                        popups = [pp for pp in opened if pp is not pg]
                        if downloads:
                            d = downloads[0]
                            try:
                                fail = d.failure()
                            except Exception as e:
                                fail = f"{type(e).__name__}: {e}"[:200]
                            res["outcome"] = "download"
                            res["download"] = {"url": d.url, "filename": d.suggested_filename,
                                               "failure": fail}
                        elif popups:
                            pp = shot_page = popups[0]
                            try:
                                pp.wait_for_load_state("load", timeout=15000)
                            except Exception as e:
                                res["error"] = f"popup did not finish loading: {e}"[:300]
                            res["outcome"] = "popup"
                            res["popup_url"] = res["final_url"] = pp.url
                            res["final_status"] = nav_status.get(pp.url)
                        else:
                            try:
                                pg.wait_for_load_state("networkidle", timeout=10000)
                            except Exception:
                                pass  # long-polling pages never go idle; judge by URL/status
                            after = pg.url
                            res["final_url"] = after
                            if after in post["nav"]:
                                res["outcome"] = "navigation"
                                res["final_status"] = post["nav"][after]
                            elif (after != before_url and urldefrag(after)[0]
                                  == urldefrag(before_url)[0]):
                                res["outcome"] = "anchor"
                                frag = urldefrag(after)[1]
                                exists = pg.evaluate(
                                    "f => !!(document.getElementById(f) || "
                                    "document.getElementsByName(f).length)", frag)
                                if frag and not exists:
                                    res["error"] = f"anchor target #{frag} not found on page"
                            elif after != before_url:
                                res["outcome"] = "client_navigation"
                            elif pg.evaluate(_STATE_JS) != before_state:
                                res["outcome"] = "dom_change"
                            else:
                                res["outcome"] = "no_change"
            except Exception as e:
                res["error"] = f"{type(e).__name__}: {e}"[:300]
            res["verdict"], res["reason"] = _verdict(res)
            if evidence_dir and res["verdict"] != "OK":
                try:
                    os.makedirs(evidence_dir, exist_ok=True)
                    slug = re.sub(r"[^A-Za-z0-9]+", "-", f"{target}-{name}").strip("-")[:80]
                    path = os.path.join(evidence_dir, f"{slug}.png")
                    shot_page.screenshot(path=path, full_page=False)
                    res["evidence"] = path
                except Exception:
                    pass
            ctx.close()
            out[name] = res
        b.close()
    return out


def _verdict(r):
    """(verdict, reason). Verdicts:
    OK         the click did what a working control does and it loaded
    FAIL       observed error: HTTP >= 400, click/load error, covered, failed
               download, missing anchor target, or outcome != expect
    UNVERIFIED something happened but its result could not be measured
    CHANGED    in-page state changed (menu/tab/dialog); correct only if expected
    NO_CHANGE  nothing observable happened (fact, not proof the control is broken)
    """
    if r.get("click_error"):
        return "FAIL", "click failed: " + r["click_error"]
    if r.get("covered_by"):
        return "FAIL", f"element covered by {r['covered_by']}"
    if r.get("error"):
        return "FAIL", r["error"]
    out = r.get("outcome") or ("popup" if r.get("popup_url") else "navigation")
    exp = r.get("expect")
    if exp and out not in EXPECTATIONS[exp]:
        return "FAIL", f"expected {exp}, observed {out}"
    if out == "download":
        f = (r.get("download") or {}).get("failure")
        return ("FAIL", f"download failed: {f}") if f else ("OK", "download completed")
    if out in ("navigation", "popup"):
        st = r.get("final_status")
        if out == "popup" and r.get("final_url") != r.get("popup_url"):
            return "UNVERIFIED", "new window opened; its own status was not captured"
        if st is None:
            return "UNVERIFIED", f"{out} happened but HTTP status was not captured"
        if st >= 400:
            return "FAIL", f"{out} landed on HTTP {st}"
        return "OK", f"{out} → HTTP {st}"
    if out == "anchor":
        return "OK", "scrolled to in-page anchor"
    if out == "client_navigation":
        if exp:
            return "OK", "URL changed client-side as expected (no HTTP status to judge)"
        return "CHANGED", "URL changed client-side; content not judged"
    if out == "dom_change":
        return ("OK", "in-page change as expected") if exp else (
            "CHANGED", "in-page state changed (menu/tab/dialog?); correctness needs an expectation")
    return "NO_CHANGE", "no navigation, popup, download or DOM change observed"


def click_verdict(r):
    """Verdict string for one viewport result (see _verdict)."""
    return _verdict(r)[0]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def format_report(audit, clicks=None):
    """Markdown report. Coverage + blind spots are always included — never send
    a link-check verdict without them."""
    c = audit["coverage"]
    restricted = audit.get("restricted", [])
    L = [f"# Link audit: {audit['start_url']}", "",
         f"**Result:** {len(audit['broken'])} broken, "
         f"{len(restricted)} restricted (unverified), "
         f"{len(audit['false_positives'])} bot-only failures (not user-facing), "
         f"{len(audit.get('script_only_unreachable', []))} script-only refs to review, "
         f"{c['urls_checked']} URLs checked across {c['pages_crawled']} pages.", ""]
    if audit["broken"]:
        L += ["## Broken", "| URL | Status | Found on | Found via |", "|---|---|---|---|"]
        for r in audit["broken"]:
            L.append(f"| {r['url']} | {r['status'] or r.get('note') or '-'} | "
                     f"{', '.join(r['referrers'][:2]) or '-'} | {', '.join(r['found_via'])} |")
        L.append("")
    if restricted:
        L += ["## Restricted — refused this checker, NOT verified (open in a browser)"]
        L += [f"- {r['url']} ({r['status']})" for r in restricted]
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
    L += ["## Pages", "| URL | Status | Render | Found via |", "|---|---|---|---|"]
    for pg in audit["pages"]:
        rn = pg.get("render", "-")
        if pg.get("render_note") and rn != "rendered":
            rn += f" ({pg['render_note'][:60]})"
        L.append(f"| {pg['url']} | {pg['status']} | {rn} | {', '.join(pg['found_via'])} |")
    if clicks:
        L += ["", "## Click checks (real browser)"]
        for target, by_vp in clicks.items():
            if isinstance(by_vp.get("error"), str):
                L.append(f"- {target}: NOT VERIFIED — {by_vp['error']}")
                continue
            for vp, r in by_vp.items():
                verdict, reason = (r.get("verdict"), r.get("reason")) if r.get("verdict") \
                    else _verdict(r)
                L.append(f"- {target} [{vp}]: {verdict} — {reason}"
                         f" (outcome={r.get('outcome')}, final={r.get('final_url')}, "
                         f"href={r.get('href')}, console_errors={len(r.get('console_errors', []))}"
                         f"{', evidence=' + r['evidence'] if r.get('evidence') else ''})")
    rc = c.get("render_counts", {})
    L += ["", "## Coverage",
          f"- robots.txt: {'yes' if c['robots_txt'] else 'no'}; sitemap: "
          f"{'yes' if c['sitemap'] else 'no'}; rendered pages: {c['rendered_pages']} "
          f"({', '.join(f'{k} {v}' for k, v in sorted(rc.items())) or 'none'})",
          f"- Budget: {c.get('budget_hit') or 'not hit'}; elapsed {c.get('elapsed_s')}s"]
    if c.get("unvisited"):
        L.append(f"- Discovered but not visited ({len(c['unvisited'])}): "
                 + ", ".join(c["unvisited"][:10]))
    if c["pages_found_only_via_js_or_script"]:
        L.append("- Pages found ONLY via scripts/rendered DOM (a plain <a> crawler misses "
                 "these): " + ", ".join(c["pages_found_only_via_js_or_script"]))
    if c["user_named_urls"]:
        L.append("- User-named URLs checked: " + ", ".join(c["user_named_urls"]))
    L += ["", "## Not covered"] + [f"- {b}" for b in c["blind_spots"]]
    return "\n".join(L)

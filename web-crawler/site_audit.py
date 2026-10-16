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
from urllib.parse import parse_qsl, urldefrag, urlencode, urljoin, urlparse, urlunparse
import xml.etree.ElementTree as ET

from site_browser import (DEFAULT_CONFIG, VIEWPORTS, _Renderer, _excluded, _verdict,  # noqa: F401
                          click_check, click_verdict)

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


# Only parameters that are KNOWN tracking noise are removed for dedup. Anything
# else (?ag-tab=3, ?page=2, ?id=...) may change content and is kept.
TRACKING_PARAM_RE = re.compile(
    r"^(utm_\w+|fbclid|gclid|gbraid|wbraid|dclid|msclkid|mc_cid|mc_eid|igshid|"
    r"yclid|twclid|ttclid|_hsenc|_hsmi|hsCtaTracking|ref_src|ref_url|srsltid)$", re.I)


def canonical_url(url):
    """Dedup key: drop fragment and known tracking params, nothing else."""
    url = urldefrag(url.strip())[0]
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return None
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not TRACKING_PARAM_RE.match(k)]
    netloc = p.netloc
    if (p.scheme, p.port) in (("http", 80), ("https", 443)):
        netloc = p.hostname
    return urlunparse((p.scheme, netloc, p.path, p.params,
                       urlencode(q, doseq=True), ""))


_norm = canonical_url


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
    """Return (page_urls, child_sitemap_urls) from a sitemap or sitemap index.
    Real XML parsing (namespaces, &amp; escapes, CDATA); regex only as a
    fallback for malformed files."""
    xml = (xml or "").strip()
    try:
        root = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        local = lambda t: t.rsplit("}", 1)[-1].lower()  # noqa: E731
        locs = [(e.text or "").strip() for e in root.iter()
                if local(e.tag) == "loc" and (e.text or "").strip()]
        if local(root.tag) == "sitemapindex":
            return [], locs
        return locs, []
    except ET.ParseError:
        locs = [u.replace("&amp;", "&") for u in
                re.findall(r"<loc>\s*(?:<!\[CDATA\[)?\s*([^<\s\]]+)", xml, re.I)]
        if re.search(r"<sitemapindex", xml, re.I):
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


_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.S | re.I)
NOT_FOUND_RE = re.compile(
    r"\b(404|not found|page not found|page doesn.t exist|no longer available|"
    r"p[áa]gina n[ãa]o encontrada|no encontrada|nicht gefunden|introuvable|"
    r"页面不存在|找不到页面|ページが見つかりません)\b", re.I)


def _fingerprint(html):
    """(title_lower, text_len) — cheap shape of a page for soft-404 comparison."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip().lower() if m else ""
    text = re.sub(r"\s+", " ", _TAG_RE.sub(" ", html or "")).strip()
    return title, len(text)


def _soft404_reason(html, baseline_fp):
    """Why a 200 page looks like an error page, or None."""
    title, n = _fingerprint(html)
    if baseline_fp:
        bt, bn = baseline_fp
        if title and title == bt and abs(n - bn) <= max(50, 0.1 * max(n, bn)):
            return "same title and size as the site's response to a non-existent URL"
    if NOT_FOUND_RE.search(title):
        return f"title looks like an error page: {title[:60]!r}"
    return None


# Statuses that mean "this checker was refused", not "the link is broken".
RESTRICTED_STATUSES = (401, 403, 407, 429, 451, 999)


def audit_site(start_url, max_pages=150, render=True, check_external=True,
               timeout=15, workers=8, extra_urls=None, max_render=30,
               max_seconds=600, render_timeout_ms=30000, config=None,
               evidence_dir=None):
    """Crawl one site and check every link it references.

    config: per-site overrides, see site_browser.DEFAULT_CONFIG (wait_for,
    scroll_steps, max_interactions, expand_selectors, exclude, entry_points).
    evidence_dir: save screenshots for pages with JS errors / failed images.

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
      soft_404_suspects: 200 pages that look like an error page
      coverage:   what was and wasn't done — ALWAYS show this to the user
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
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
    for u in list(extra_urls or []) + list(cfg.get("entry_points") or []):
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

    # soft-404 baseline: what does this site return for a URL that cannot exist?
    probe = _fetch(f"{origin}/sc-probe-{int(t0 * 1000) % 10_000_000}-does-not-exist",
                   timeout=timeout)
    soft404_fp = _fingerprint(probe["body"]) if probe["status"] == 200 else None

    # 2. crawl same-site pages (BFS), per-page fetch + render log
    crawled, page_log, rendered_pages, budget_hit = {}, {}, 0, None
    excluded, dynamic_found = [], 0
    renderer = _Renderer(render_timeout_ms, cfg, evidence_dir) if render else None
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
            if _excluded(url, cfg.get("exclude")):
                if url not in excluded:
                    excluded.append(url)
                continue
            r = _fetch(url, timeout=timeout)
            crawled[url] = r["status"]
            log = page_log[url] = {"fetch_error": r["error"], "render": "skipped",
                                   "render_note": None, "soft_404": None, "analysis": None}
            if r["status"] != 200 or "html" not in (r["content_type"] or "html").lower():
                log["render_note"] = "not an HTML 200 page"
                continue
            log["soft_404"] = _soft404_reason(r["body"], soft404_fp)
            page_url = r["final_url"]
            groups = extract_urls(r["body"], page_url)
            if not render:
                log["render_note"] = "rendering disabled"
            elif rendered_pages >= max_render:
                log["render_note"] = f"max_render={max_render} reached"
            else:
                rec, err = renderer.analyze(page_url)
                if rec is None:
                    log["render"] = "unavailable" if renderer.unavailable else "failed"
                    log["render_note"] = err
                else:
                    log["render"] = "rendered"
                    log["analysis"] = rec
                    rendered_pages += 1
                    a_set = groups.get("a", set())
                    dom = {u for u in (_norm(urljoin(page_url, x)) for x in rec["links"]) if u}
                    dyn = {u for u in (_norm(urljoin(page_url, x)) for x in rec["dynamic_links"]) if u}
                    groups["rendered"] = dom - a_set
                    groups["dynamic"] = dyn - dom - a_set
                    dynamic_found += len(groups["dynamic"])
            for src, urls in groups.items():
                for u in urls:
                    if src == "hint":
                        note(u, src, url, "hint")
                    elif src == "asset" or _ASSET_RE.search(urlparse(u).path):
                        note(u, src, url, "asset")
                    elif _same_site(u, start_url):
                        note(u, src, url, "page")
                        if u in crawled:
                            pass
                        elif _excluded(u, cfg.get("exclude")):
                            if u not in excluded:
                                excluded.append(u)
                        else:
                            queue.append(u)
                    else:
                        note(u, src, url, "external")
    finally:
        if renderer:
            renderer.close()
    unvisited = sorted({u for u in queue if u not in crawled})

    # 3. check every non-crawled URL
    to_check = []
    for u in found_via:
        if u in crawled or u in unvisited:
            continue
        if not check_external and kinds.get(u) == "external":
            continue
        if _excluded(u, cfg.get("exclude")):
            if u not in excluded:
                excluded.append(u)
            continue
        to_check.append(u)
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
               if pg["status"] == 200 and set(pg["found_via"]) & {"script", "rendered", "dynamic"}
               and not set(pg["found_via"]) & {"a", "sitemap", "start"}]
    soft_404_suspects = [{"url": pg["url"], "reason": pg["soft_404"]}
                         for pg in pages if pg.get("soft_404")]
    blind = [
        "Pages that nothing references (no link, no script, no sitemap) cannot be "
        "discovered by any crawler — ask the user for those URLs.",
        "Status checks prove a URL loads; they do not prove a button works. For a "
        "specific button/flow, run click_check() in a real browser.",
        "Dynamic discovery is bounded (scroll_steps / max_interactions per page); "
        "content behind logins, forms, or deeper interaction chains is not explored.",
        "Page analysis records are evidence (title, forms, failed images, JS errors); "
        "whether the content is correct for the business is for the reader to judge.",
    ]
    if soft404_fp is None:
        blind.append("Soft-404 check: the site returns a real 404 for unknown URLs, so "
                     "only title heuristics were used for soft-404 detection.")
    if excluded:
        blind.append(f"{len(excluded)} URLs skipped by config.exclude.")
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
        "dynamic_links_found": dynamic_found,
        "soft_404_baseline": soft404_fp is not None,
        "excluded": excluded,
        "user_named_urls": [u for u, s in found_via.items() if "user" in s],
        "blind_spots": blind,
    }
    return {"start_url": start_url, "pages": pages, "links": links,
            "broken": broken, "restricted": restricted, "false_positives": fps,
            "script_only_unreachable": script_only, "soft_404_suspects": soft_404_suspects,
            "coverage": coverage}


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
    if audit.get("soft_404_suspects"):
        L += ["## Soft-404 suspects (HTTP 200 but looks like an error page)"]
        L += [f"- {x['url']}: {x['reason']}" for x in audit["soft_404_suspects"]]
        L.append("")
    L += ["## Pages", "| URL | Status | Render | Found via |", "|---|---|---|---|"]
    for pg in audit["pages"]:
        rn = pg.get("render", "-")
        if pg.get("render_note") and rn != "rendered":
            rn += f" ({pg['render_note'][:60]})"
        L.append(f"| {pg['url']} | {pg['status']} | {rn} | {', '.join(pg['found_via'])} |")
    analysed = [pg for pg in audit["pages"] if pg.get("analysis")]
    if analysed:
        L += ["", "## Page analysis (evidence from the rendered page)",
              "| URL | Title | H1 | Forms | Imgs failed | JS errors | Failed reqs | Overflow | Dyn links |",
              "|---|---|---|---|---|---|---|---|---|"]
        for pg in analysed:
            a = pg["analysis"]
            L.append(f"| {pg['url']} | {(a.get('title') or '-')[:40]} | "
                     f"{(a.get('h1') or ['-'])[0][:30]} | {len(a.get('forms') or [])} | "
                     f"{len((a.get('images') or {}).get('failed') or [])} | "
                     f"{len(a.get('js_errors') or [])} | {len(a.get('failed_requests') or [])} | "
                     f"{'yes' if a.get('overflow_x') else 'no'} | {len(a.get('dynamic_links') or [])} |")
        flagged = [pg for pg in analysed if pg["analysis"].get("js_errors")
                   or (pg["analysis"].get("images") or {}).get("failed")
                   or pg["analysis"].get("failed_requests")]
        if flagged:
            L.append("")
            L.append("Details for flagged pages:")
            for pg in flagged[:15]:
                a = pg["analysis"]
                for e in (a.get("js_errors") or [])[:3]:
                    L.append(f"- {pg['url']} JS: {e}")
                for u in ((a.get("images") or {}).get("failed") or [])[:3]:
                    L.append(f"- {pg['url']} image failed: {u}")
                for fr in (a.get("failed_requests") or [])[:3]:
                    L.append(f"- {pg['url']} request {fr.get('status') or fr.get('failure')}: {fr['url']}")
                if a.get("evidence"):
                    L.append(f"- {pg['url']} screenshot: {a['evidence']}")
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
          f"- Budget: {c.get('budget_hit') or 'not hit'}; elapsed {c.get('elapsed_s')}s",
          f"- Dynamic discovery: {c.get('dynamic_links_found', 0)} links found only after "
          f"scroll/expand; soft-404 baseline: {'yes' if c.get('soft_404_baseline') else 'no'}"]
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

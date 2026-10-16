"""
Real-browser layer for the site audit (Playwright, optional).

- _Renderer: ONE reused headless Chromium, a fresh context per page. A failure
  on one page never disables rendering for the rest.
- _Renderer.analyze(): bounded dynamic discovery (scroll for lazy-load, expand
  menus / dropdowns / "load more"; never inside forms) + a structured per-page
  record (content, structure, display, technical). Links that appear only after
  interaction are returned separately so the crawler can tag them "dynamic".
- click_check(): click ONE named element at desktop + mobile widths and
  classify what happened. Verdicts separate facts from conclusions.

Safety: this layer only navigates, scrolls and expands. It never types into or
submits forms. Side-effecting flows need explicit user authorization.

Everything degrades to "not verified" when Playwright is missing — callers
must never treat that as OK.
"""
import os
import re
import time
from urllib.parse import urldefrag, urljoin

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
VIEWPORTS = (("desktop", 1280, 800, False), ("mobile", 390, 844, True))

# Per-site knobs. Pass overrides via audit_site(config={...}); nothing is
# hardcoded for one site.
DEFAULT_CONFIG = {
    "wait_for": None,          # CSS selector to wait for before extracting
    "scroll_steps": 4,         # lazy-load: scroll to bottom in N steps (0 = off)
    "max_interactions": 8,     # per page: expanders / load-more clicks (0 = off)
    "expand_selectors": [],    # extra selectors for menus/"load more" on this site
    "exclude": [],             # regexes: URLs never visited or clicked
    "entry_points": [],        # extra start URLs (merged with extra_urls)
    "viewport": (1280, 800),
}

# Buttons matched by accessible name (Playwright get_by_role, regex allowed).
EXPANDER_NAME_RE = re.compile(
    r"^\s*(menu|more|load more|show more|see more|view more|ver mais|carregar mais|"
    r"mostrar mais|更多|加载更多|查看更多)\s*$", re.I)

# Generic expanders. Form-associated and submit-like controls are never clicked.
EXPANDER_SELECTORS = [
    '[aria-expanded="false"]',
    '[aria-haspopup]:not(a)',
    'details:not([open]) > summary',
    'nav button, nav [role="button"]',
    '[class*="dropdown"] > :is(button, [role="button"]), [class*="dropdown-toggle"]',
    '[class*="load-more"], [class*="show-more"], [class*="accordion"] > :is(button, [role="button"])',
]

_LINKS_JS = """() => {
  const out = new Set();
  const grab = root => root.querySelectorAll('a[href], area[href], [data-href]')
    .forEach(e => out.add(e.href || e.getAttribute('data-href')));
  grab(document);
  const walk = root => root.querySelectorAll('*').forEach(e => {
    if (e.shadowRoot) { grab(e.shadowRoot); walk(e.shadowRoot); }
  });
  walk(document);
  return [...out].filter(Boolean);
}"""

_STATE_JS = """() => {
  const vis = [...document.querySelectorAll('body *')]
    .filter(e => e.getClientRects().length).length;
  const aria = [...document.querySelectorAll('[aria-expanded],[aria-selected],[aria-pressed],[open]')]
    .map(e => [e.getAttribute('aria-expanded'), e.getAttribute('aria-selected'),
               e.getAttribute('aria-pressed'), e.hasAttribute('open')].join(':')).join(',');
  const dlg = document.querySelectorAll('dialog[open],[aria-modal="true"]').length;
  return [vis, aria, dlg, (document.body && document.body.innerText || '').length].join('|');
}"""

_RECORD_JS = """() => {
  const txt = e => (e.innerText || e.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 120);
  const q = (s, n) => [...document.querySelectorAll(s)].slice(0, n);
  const meta = n => { const m = document.querySelector(`meta[name="${n}"], meta[property="${n}"]`);
                      return m ? (m.getAttribute('content') || '').slice(0, 300) : null; };
  const body = document.body ? (document.body.innerText || '') : '';
  const imgs = [...document.images];
  const failed = imgs.filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src'))
                     .map(i => i.currentSrc || i.src).slice(0, 10);
  const can = document.querySelector('link[rel="canonical"]');
  return {
    title: document.title || null, lang: document.documentElement.lang || null,
    description: meta('description') || meta('og:description'),
    canonical: can ? can.href : null,
    h1: q('h1', 5).map(txt), headings: q('h2, h3', 30).map(txt),
    text_len: body.length, text_sample: body.trim().replace(/\\s+/g, ' ').slice(0, 300),
    buttons: q('button, [role="button"], input[type="submit"], input[type="button"]', 40)
      .map(e => txt(e) || e.value || e.getAttribute('aria-label') || '').filter(Boolean),
    ctas: q('a[class*="btn"], a[class*="button"], a[role="button"]', 20)
      .map(e => ({text: txt(e), href: e.href})),
    forms: q('form', 10).map(f => ({
      action: f.getAttribute('action'), method: (f.getAttribute('method') || 'get').toLowerCase(),
      fields: [...f.querySelectorAll('input, select, textarea')].slice(0, 30).map(i => ({
        name: i.name || i.id || null, type: i.type || i.tagName.toLowerCase(),
        required: i.required})),
    })),
    images: {total: imgs.length, failed, missing_alt: imgs.filter(i => !i.hasAttribute('alt')).length},
    iframes: q('iframe', 10).map(f => f.src).filter(Boolean),
    overflow_x: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    nav_links: q('nav a[href], header a[href]', 60).map(a => a.href),
  };
}"""

_CLICKABLE_EXPANDER_JS = """e => {
  // Real form association: <button form="id"> outside the form counts too.
  if (e.form || e.closest('form') || e.hasAttribute('form')) return false;
  if (e.closest('a[href], [role="link"]')) return false;     // links are crawled, not clicked
  // A <button> with no form owner (checked above via e.form / form= / closest)
  // cannot submit anything, so a missing type is harmless there. Explicit
  // submit-like controls are still never clicked.
  const t = (e.getAttribute('type') || '').toLowerCase();
  if (t === 'submit' || t === 'reset' || t === 'image') return false;
  const txt = (e.innerText || e.getAttribute('aria-label') || '').toLowerCase();
  return !/(submit|send|enviar|buy|comprar|pay|pagar|delete|excluir|remove|checkout|login|sign ?in|logout|subscribe)/.test(txt);
}"""


def _excluded(url, patterns):
    return any(re.search(p, url) for p in patterns or [])


class _Renderer:
    """One headless Chromium reused for the whole audit; a fresh context per page.
    A failure on one page never disables rendering for the rest."""

    def __init__(self, timeout_ms=30000, config=None, evidence_dir=None):
        self.timeout_ms = timeout_ms
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self.evidence_dir = evidence_dir
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
        """Backward-compatible: (set_of_links, None) or (None, reason)."""
        rec, err = self.analyze(url)
        if rec is None:
            return None, err
        return set(rec["links"]) | set(rec["dynamic_links"]), None

    def analyze(self, url):
        """Return (record, None) or (None, reason). record keys:
        links, dynamic_links, main_status, js_errors, failed_requests,
        interactions, plus everything from _RECORD_JS (title, h1, forms, images...)."""
        self._start()
        if self.unavailable:
            return None, "browser unavailable: " + self.unavailable
        cfg = self.cfg
        ctx = None
        try:
            w, h = cfg["viewport"]
            ctx = self._b.new_context(user_agent=UA, viewport={"width": w, "height": h})
            pg = ctx.new_page()
            js_errors, failed = [], []
            pg.on("pageerror", lambda e: js_errors.append(str(e)[:200]))
            pg.on("console", lambda m: js_errors.append("console: " + m.text[:200])
                  if m.type == "error" else None)
            pg.on("response", lambda r: failed.append(
                {"url": r.url[:200], "status": r.status, "type": r.request.resource_type})
                if r.status >= 400 else None)
            # ERR_ABORTED = the page itself cancelled the request (beacons, preloads
            # replaced by a newer one); that is not a failure a visitor sees.
            pg.on("requestfailed", lambda r: failed.append(
                {"url": r.url[:200], "status": None, "type": r.resource_type,
                 "failure": (r.failure or "")[:100]})
                if "ERR_ABORTED" not in (r.failure or "") else None)
            # domcontentloaded, not load: slow third-party assets (fonts, widgets,
            # analytics) must not time out the whole page. Then settle briefly.
            resp = pg.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            try:
                pg.wait_for_load_state("load", timeout=8000)
            except Exception:
                pass
            try:
                pg.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # long-polling pages never go idle
            if cfg.get("wait_for"):
                try:
                    pg.wait_for_selector(cfg["wait_for"], timeout=8000)
                except Exception:
                    pass
            base_links = set(pg.evaluate(_LINKS_JS))
            dynamic = set()
            inter = {"scroll_steps": 0, "clicked": 0, "expanded": 0, "skipped_unsafe": 0}

            # 1. lazy-load: scroll in steps, collect new links after each
            for i in range(int(cfg.get("scroll_steps") or 0)):
                pg.evaluate("n => window.scrollTo(0, document.body.scrollHeight * n)",
                            (i + 1) / cfg["scroll_steps"])
                pg.wait_for_timeout(250)
                inter["scroll_steps"] += 1
                dynamic |= set(pg.evaluate(_LINKS_JS)) - base_links
            pg.evaluate("window.scrollTo(0, 0)")

            # 2. expand menus / dropdowns / load-more (bounded, never in forms)
            budget = int(cfg.get("max_interactions") or 0)
            seen_states = {pg.evaluate(_STATE_JS)}
            locators = [pg.get_by_role("button", name=EXPANDER_NAME_RE)]
            locators += [pg.locator(sel) for sel in
                         EXPANDER_SELECTORS + list(cfg.get("expand_selectors") or [])]
            for loc in locators:
                if budget <= 0:
                    break
                try:
                    n = min(loc.count(), 12)
                except Exception:
                    continue
                for i in range(n):
                    if budget <= 0:
                        break
                    el = loc.nth(i)
                    try:
                        if not el.is_visible() or not el.evaluate(_CLICKABLE_EXPANDER_JS):
                            if el.is_visible():
                                inter["skipped_unsafe"] += 1
                            continue
                        before_url = pg.url
                        el.click(timeout=2000)
                        budget -= 1
                        inter["clicked"] += 1
                        pg.wait_for_timeout(350)
                        if pg.url != before_url:
                            pg.go_back(wait_until="load", timeout=10000)
                            continue
                        # Always re-extract: same-shape updates (Item 1 -> Item 2)
                        # change links without changing the fingerprint.
                        dynamic |= set(pg.evaluate(_LINKS_JS)) - base_links
                        st = pg.evaluate(_STATE_JS)
                        if st not in seen_states:
                            seen_states.add(st)
                            inter["expanded"] += 1
                    except Exception:
                        continue

            rec = pg.evaluate(_RECORD_JS)
            rec.update({
                "url": url, "final_url": pg.url,
                "main_status": resp.status if resp else None,
                "links": sorted(base_links), "dynamic_links": sorted(dynamic - base_links),
                "js_errors": js_errors[:20], "failed_requests": failed[:30],
                "interactions": inter, "evidence": None,
            })
            if self.evidence_dir and (js_errors or rec["images"]["failed"] or rec["overflow_x"]):
                rec["evidence"] = self._shot(pg, url)
            return rec, None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"[:200]
        finally:
            if ctx:
                try:
                    ctx.close()
                except Exception:
                    pass

    def _shot(self, pg, label):
        try:
            os.makedirs(self.evidence_dir, exist_ok=True)
            slug = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-")[:80] or "page"
            path = os.path.join(self.evidence_dir, f"{slug}.png")
            pg.screenshot(path=path, full_page=False)
            return path
        except Exception:
            return None

    def close(self):
        for obj, fn in ((self._b, "close"), (self._pw, "stop")):
            if obj:
                try:
                    getattr(obj, fn)()
                except Exception:
                    pass
        self._pw = self._b = None


# ---------------------------------------------------------------------------

# Runs on the already-located element (Playwright passes it as `target`), so
# Playwright-only selectors like text=/alt= never reach document.querySelector.
_COVER_JS = """(target, [x, y]) => {
  const e = document.elementFromPoint(x, y);
  if (!e) return null;
  return {tag: e.tagName.toLowerCase(), cls: (e.className || '').toString().slice(0, 80),
          inside_target: target === e || target.contains(e)};
}"""

# Cheap page-state fingerprint to detect in-page changes (menu, tab, dialog).
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
                # Same wait policy as _Renderer.analyze: never let analytics
                # beacons or long-polling widgets time out the whole check.
                pg.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                for state, ms in (("load", 8000), ("networkidle", 5000)):
                    try:
                        pg.wait_for_load_state(state, timeout=ms)
                    except Exception:
                        pass
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



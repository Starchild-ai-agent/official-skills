"""
Site-agnostic primitives for auditing a website. They OBSERVE and return raw
data; they never decide whether something is broken. The agent decides — see
SKILL.md "Site audit" and reference/site-audit-method.md.

No site-specific, language-specific or platform-specific rules live here:
no keyword lists, no "known false positive" tables, no status-code verdicts.

    fetch(url)                  one HTTP request, raw result
    check_urls(urls)            many requests in parallel, raw results (no body)
    extract_refs(html, base)    every URL-like reference in HTML, with where it came from
    parse_sitemap(xml)          <loc> entries of a sitemap / sitemap index
    browse(url, actions=[...])  real Chromium: rendered DOM, controls, errors,
                                requests, and what each action you asked for did
"""
import re
import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_CTX = ssl.create_default_context()


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def fetch(url, method="GET", timeout=15, headers=None, max_bytes=3_000_000,
          read_body=True):
    """One request. Returns raw facts:
    {url, method, status, final_url, content_type, headers, body, error, elapsed_ms}.
    status is None when the request did not complete (DNS, TLS, timeout...);
    error then says why. 4xx/5xx are returned as data, not raised."""
    t0 = time.monotonic()
    out = {"url": url, "method": method, "status": None, "final_url": url,
           "content_type": "", "headers": {}, "body": "", "error": None}
    req = urllib.request.Request(url, method=method,
                                 headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            out.update(status=r.status, final_url=r.geturl(),
                       content_type=r.headers.get("Content-Type", ""),
                       headers=dict(r.headers.items()))
            if read_body and method != "HEAD":
                out["body"] = r.read(max_bytes).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out.update(status=e.code, final_url=e.geturl() or url,
                   content_type=e.headers.get("Content-Type", "") if e.headers else "",
                   headers=dict(e.headers.items()) if e.headers else {})
        if read_body and method != "HEAD":
            try:
                out["body"] = e.read(max_bytes).decode("utf-8", "replace")
            except Exception:
                pass
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"[:300]
    out["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
    return out


def check_urls(urls, method="HEAD", timeout=15, workers=8):
    """fetch() many URLs in parallel without bodies. Returns a list in input
    order. Some servers reject HEAD (403/405/501) — re-check those with
    method="GET" yourself before drawing a conclusion."""
    urls = list(dict.fromkeys(urls))

    def one(u):
        r = fetch(u, method=method, timeout=timeout, read_body=False)
        r.pop("body", None)
        return r
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return list(ex.map(one, urls))


# ---------------------------------------------------------------------------
# HTML references
# ---------------------------------------------------------------------------
_QUOTED_PATH_RE = re.compile(r"""["'`](/[^"'`\s<>{}]{1,300})["'`]""")
_ABS_URL_RE = re.compile(r"""https?://[^\s"'`<>()]{3,500}""")
_URL_ATTRS = {"href", "src", "action", "formaction", "poster", "data", "cite",
              "background", "longdesc", "manifest", "ping"}


class _RefParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []          # (raw_value, source, tag, attr, text)
        self.base = None
        self._script = None     # buffer while inside an inline <script>
        self._a = None          # index of the open <a>, to attach its text

    def _add(self, value, source, tag, attr):
        if value and value.strip():
            self.refs.append([value.strip(), source, tag, attr, ""])

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "base" and d.get("href") and self.base is None:
            self.base = d["href"]
        for k, v in attrs:
            if not v:
                continue
            if k in _URL_ATTRS:
                src = f"{tag}[{k}]"
                if tag == "link":
                    src = f"link[rel={(d.get('rel') or '').lower()}]"
                self._add(v, src, tag, k)
                if tag in ("a", "area") and k == "href":
                    self._a = len(self.refs) - 1
            elif k in ("srcset", "imagesrcset"):
                for part in v.split(","):
                    self._add(part.strip().split(" ")[0], f"{tag}[{k}]", tag, k)
            elif k.startswith("data-") or k.startswith("on") or k == "style":
                # navigation hidden in attributes: data-href, onclick="location='/x'"
                for m in _QUOTED_PATH_RE.findall(v) + _ABS_URL_RE.findall(v):
                    self._add(m, f"attr[{k}]", tag, k)
                if k.startswith("data-") and v.startswith(("/", "http://", "https://")):
                    self._add(v, f"attr[{k}]", tag, k)
        if tag == "meta" and (d.get("http-equiv") or "").lower() == "refresh":
            m = re.search(r"url\s*=\s*['\"]?([^'\";]+)", d.get("content") or "", re.I)
            if m:
                self._add(m.group(1), "meta[refresh]", tag, "content")
        if tag == "script" and not d.get("src"):
            self._script = []

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            body = "".join(self._script)
            for m in _QUOTED_PATH_RE.findall(body) + _ABS_URL_RE.findall(body):
                self._add(m, "inline-script", "script", None)
            self._script = None
        if tag in ("a", "area"):
            self._a = None

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)
        elif self._a is not None and data.strip():
            self.refs[self._a][4] = (self.refs[self._a][4] + " " + data.strip()).strip()[:120]


def extract_refs(html, base_url):
    """Every URL-like reference in one HTML document, resolved to absolute.
    Returns a list of {url, raw, source, tag, attr, text}, one per occurrence.
    `source` says where it was found, e.g. "a[href]", "link[rel=canonical]",
    "img[srcset]", "inline-script", "attr[data-href]", "meta[refresh]".
    Nothing is filtered or judged: inline-script matches in particular are
    candidates (route configs, API paths, asset paths) for you to inspect."""
    p = _RefParser()
    try:
        p.feed(html or "")
        p.close()
    except Exception:
        pass  # malformed HTML: keep what was parsed
    base = urljoin(base_url, p.base) if p.base else base_url
    out = []
    for raw, source, tag, attr, text in p.refs:
        if raw.startswith(("javascript:", "data:", "#")) and source.endswith("[href]"):
            url = raw  # keep visible, but it is not a fetchable URL
        else:
            url = urljoin(base, raw)
        out.append({"url": url, "raw": raw, "source": source, "tag": tag,
                    "attr": attr, "text": text})
    return out


def parse_sitemap(xml):
    """{"urls": [...], "sitemaps": [...], "error": str|None} from a sitemap or a
    sitemap index (namespaces, &amp; and CDATA handled by the XML parser).
    On malformed XML, falls back to a plain <loc> scan and reports the error."""
    xml = (xml or "").strip()
    try:
        root = ET.fromstring(xml.encode("utf-8"))
        local = lambda t: t.rsplit("}", 1)[-1].lower()  # noqa: E731
        locs = [(e.text or "").strip() for e in root.iter()
                if local(e.tag) == "loc" and (e.text or "").strip()]
        if local(root.tag) == "sitemapindex":
            return {"urls": [], "sitemaps": locs, "error": None}
        return {"urls": locs, "sitemaps": [], "error": None}
    except ET.ParseError as e:
        locs = [u.replace("&amp;", "&") for u in re.findall(
            r"<loc>\s*(?:<!\[CDATA\[)?\s*([^<\s\]]+)", xml, re.I)]
        key = "sitemaps" if re.search(r"<sitemapindex", xml, re.I) else "urls"
        return {"urls": [], "sitemaps": [], key: locs, "error": f"XML parse error: {e}"}


def same_host(a, b):
    """True if two URLs share a hostname (ignoring a leading www.)."""
    h = lambda u: (urlparse(u).hostname or "").removeprefix("www.")  # noqa: E731
    return h(a) == h(b)


# ---------------------------------------------------------------------------
# Real browser (Playwright, optional)
# ---------------------------------------------------------------------------
_LINKS_JS = """() => {
  const out = new Map();
  const grab = root => root.querySelectorAll('a[href], area[href]').forEach(e => {
    if (!out.has(e.href)) out.set(e.href, (e.innerText || e.getAttribute('aria-label') || '')
      .trim().replace(/\\s+/g, ' ').slice(0, 120));
  });
  const walk = root => { grab(root); root.querySelectorAll('*').forEach(e => {
    if (e.shadowRoot) walk(e.shadowRoot); }); };
  walk(document);
  return [...out].map(([url, text]) => ({url, text}));
}"""

# Generic interactive elements, described — not judged. The agent decides what
# (if anything) to click, using `selector`.
_CONTROLS_JS = """() => {
  const path = e => {
    if (e.id && document.querySelectorAll('#' + CSS.escape(e.id)).length === 1)
      return '#' + CSS.escape(e.id);
    const parts = [];
    for (let n = e; n && n.nodeType === 1 && n !== document.body; n = n.parentElement) {
      let i = 1; for (let s = n.previousElementSibling; s; s = s.previousElementSibling)
        if (s.tagName === n.tagName) i++;
      parts.unshift(n.tagName.toLowerCase() + ':nth-of-type(' + i + ')');
    }
    return 'body > ' + parts.join(' > ');
  };
  const sel = 'button, [role=button], [role=tab], [role=menuitem], [aria-expanded], ' +
              '[aria-haspopup], summary, [onclick], input[type=button], input[type=submit], ' +
              'input[type=image], select';
  return [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length)
    .slice(0, 80).map(e => ({
      selector: path(e), tag: e.tagName.toLowerCase(),
      type: e.getAttribute('type'), role: e.getAttribute('role'),
      text: (e.innerText || e.value || e.getAttribute('aria-label') || '').trim()
              .replace(/\\s+/g, ' ').slice(0, 80),
      aria_expanded: e.getAttribute('aria-expanded'),
      form_associated: !!(e.form || e.closest('form') || e.hasAttribute('form')),
      inside_link: !!e.closest('a[href]'),
    }));
}"""

_ELEMENT_JS = """e => {
  const r = e.getBoundingClientRect();
  const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
  const a = e.closest('a');
  return {
    tag: e.tagName.toLowerCase(), type: e.getAttribute('type'),
    text: (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 80),
    href: a ? a.getAttribute('href') : null, target: a ? a.getAttribute('target') : null,
    download: a ? a.hasAttribute('download') : false,
    form_associated: !!(e.form || e.closest('form') || e.hasAttribute('form')),
    box: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
    topmost_at_center: top ? {tag: top.tagName.toLowerCase(),
      cls: (top.className || '').toString().slice(0, 80),
      is_element_or_child: e === top || e.contains(top)} : null,
  };
}"""

_STATE_JS = """() => [document.querySelectorAll('body *').length,
  (document.body && document.body.innerText || '').length,
  [...document.querySelectorAll('[aria-expanded],[aria-selected],[open],[hidden]')]
    .map(e => (e.getAttribute('aria-expanded') || '') + (e.getAttribute('aria-selected') || '') +
              e.hasAttribute('open') + e.hasAttribute('hidden')).join('')].join('|')"""


def browse(url, actions=None, viewport=(1280, 800), mobile=False, allow_writes=False,
           timeout_ms=30000, settle_ms=800, screenshot=None, save_html=None,
           popup_timeout_ms=10000):
    """Open `url` in headless Chromium, optionally perform `actions`, and return
    what was observed. Nothing here decides pass/fail.

    actions: list of dicts, executed in order on the current page:
        {"click": "<selector>"}      Playwright selector (CSS, text=..., role=...)
        {"hover": "<selector>"}
        {"scroll": "bottom" | <pixels>}
        {"press": "<key>"}           e.g. "Escape"
        {"wait": <ms>}
        {"back": true}
        {"screenshot": "<path>"}
    allow_writes: False (default) aborts every non-GET/HEAD/OPTIONS request for
        the whole browser context — initial load, actions, new windows, and
        anything they send later (fetch/XHR POST, beacons, form submits) — and
        lists them in `blocked_writes` as {method, url, phase}. Writes blocked
        during "load" may change how the page renders; check `phase`.
        Only set True with the user's explicit OK.
    popup_timeout_ms: upper bound for waiting on a new window that an action
        started (its response may be slow). If it does not finish in time the
        new_pages entry has status None and `timeout: True` — not verified.

    Returns {
      url, final_url, status, title, error,
      links: [{url, text}]           rendered DOM incl. shadow roots, after all actions
      controls: [{selector, tag, type, role, text, aria_expanded,
                  form_associated, inside_link}]   on the initial page
      text_sample, text_len,
      page_errors: [...]              uncaught JS exceptions
      console: [{type, text}]         console errors/warnings
      bad_responses: [{url, status, type}]   any response >= 400
      failed_requests: [{url, type, failure}]
      blocked_writes: [...]
      actions: [{action, element, url_before, url_after, navigations: [{url, status}],
                 new_pages: [{url, status, timeout, failure}], downloads: [{url, filename, failure}],
                 dom_changed, new_links, error}]
      screenshot, html_path
    }
    If Playwright is unavailable, returns {"error": ...} — treat as NOT verified.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {"error": f"Playwright unavailable: {e}"}
    out = {"url": url, "final_url": None, "status": None, "title": None, "error": None,
           "links": [], "controls": [], "text_sample": "", "text_len": 0,
           "page_errors": [], "console": [], "bad_responses": [], "failed_requests": [],
           "blocked_writes": [], "actions": [], "screenshot": None, "html_path": None}
    w, h = viewport
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile,
                            has_touch=mobile, user_agent=UA, accept_downloads=True)
        navs, new_pages, downloads, doc_status = [], [], [], {}
        acting = {"on": False, "phase": "load"}
        # top-level navigations NOT belonging to the main page (popups / new tabs),
        # tracked from the first request so a slow new window is never missed
        popup_navs = []

        def on_response(r):
            try:
                if r.status >= 400:
                    out["bad_responses"].append(
                        {"url": r.url[:300], "status": r.status, "type": r.request.resource_type})
                if r.request.resource_type == "document":
                    doc_status[r.url] = r.status
                if r.request.is_navigation_request() and r.frame == r.frame.page.main_frame:
                    navs.append({"url": r.url, "status": r.status, "page": r.frame.page})
            except Exception:
                pass

        def guard(route, req):
            # Write protection is a code-level safety boundary: it stays on for
            # the whole browser context (initial load, every action, popups and
            # anything they do later), not just the instant of a click.
            if allow_writes or req.method in ("GET", "HEAD", "OPTIONS"):
                return route.continue_()
            out["blocked_writes"].append(
                {"method": req.method, "url": req.url[:300], "phase": acting["phase"]})
            return route.abort()

        def on_request(r):
            try:
                if not (r.is_navigation_request() and r.resource_type == "document"):
                    return
                try:
                    fr = r.frame
                except Exception:
                    # Playwright: a popup's first navigation request is issued
                    # before its frame exists, so .frame raises — it is a new window
                    fr = None
                if fr is not None:
                    if fr.parent_frame is not None:
                        return
                    try:
                        if fr.page is pg:
                            return
                    except Exception:
                        pass
                popup_navs.append({"request": r, "url": r.url, "status": None,
                                   "done": False, "failure": None, "phase": acting["phase"]})
            except Exception:
                pass

        def on_popup_done(r, failure=None):
            for n in popup_navs:
                if n["request"] is r and not n["done"]:
                    n["done"] = True
                    n["failure"] = failure
                    try:
                        resp = r.response() if failure is None else None
                        n["status"] = resp.status if resp else n["status"]
                    except Exception:
                        pass

        def on_popup_response(resp):
            for n in popup_navs:
                if n["request"] is resp.request:
                    n["status"] = resp.status
                    n["done"] = True

        def on_failed(r):
            out["failed_requests"].append(
                {"url": r.url[:300], "type": r.resource_type, "failure": (r.failure or "")[:120]})
            on_popup_done(r, failure=(r.failure or "failed")[:120])

        pg = None
        ctx.on("request", on_request)
        ctx.on("response", on_response)
        ctx.on("response", on_popup_response)
        ctx.on("requestfailed", on_failed)
        ctx.on("page", lambda p_: new_pages.append(p_) if p_ is not pg else None)
        ctx.route("**/*", guard)
        pg = ctx.new_page()
        if new_pages and new_pages[-1] is pg:
            new_pages.pop()
        pg.on("pageerror", lambda e: out["page_errors"].append(str(e)[:300]))
        pg.on("console", lambda m: out["console"].append({"type": m.type, "text": m.text[:300]})
              if m.type in ("error", "warning") else None)
        pg.on("download", lambda d: downloads.append(d))
        try:
            resp = pg.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            out["status"] = resp.status if resp else None
            for state, ms in (("load", 8000), ("networkidle", 5000)):
                try:
                    pg.wait_for_load_state(state, timeout=ms)
                except Exception:
                    pass  # slow third parties / long polling never settle
            out["controls"] = pg.evaluate(_CONTROLS_JS)
            for i, act in enumerate(actions or []):
                acting["phase"] = f"action[{i}]"
                out["actions"].append(_do_action(pg, act, navs, new_pages, downloads,
                                                 acting, settle_ms, doc_status,
                                                 popup_navs, popup_timeout_ms))
            acting["phase"] = "after-actions"
            out["final_url"] = pg.url
            out["title"] = pg.title()
            out["links"] = pg.evaluate(_LINKS_JS)
            text = pg.evaluate("() => document.body ? document.body.innerText : ''") or ""
            out["text_len"], out["text_sample"] = len(text), " ".join(text.split())[:500]
            if save_html:
                with open(save_html, "w", encoding="utf-8") as f:
                    f.write(pg.content())
                out["html_path"] = save_html
            if screenshot:
                pg.screenshot(path=screenshot)
                out["screenshot"] = screenshot
        except Exception as e:
            out["error"] = f"{type(e).__name__}: {e}"[:300]
        ctx.close()
        b.close()
    return out


def _do_action(pg, act, navs, new_pages, downloads, acting, settle_ms, doc_status,
               popup_navs, popup_timeout_ms):
    rec = {"action": act, "element": None, "url_before": pg.url, "url_after": None,
           "navigations": [], "new_pages": [], "downloads": [], "dom_changed": None,
           "new_links": [], "error": None}
    n_nav, n_pages, n_dl, n_pop = len(navs), len(new_pages), len(downloads), len(popup_navs)
    try:
        links_before = {x["url"] for x in pg.evaluate(_LINKS_JS)}
        state_before = pg.evaluate(_STATE_JS)
    except Exception:
        links_before, state_before = set(), None
    try:
        if "click" in act or "hover" in act:
            sel = act.get("click") or act.get("hover")
            loc = pg.locator(sel)
            count = loc.count()
            vis = [i for i in range(count) if loc.nth(i).is_visible()]
            if not vis:
                raise RuntimeError(f"no visible match for {sel!r} ({count} in DOM)")
            el = loc.nth(vis[0])
            rec["element"] = {**el.evaluate(_ELEMENT_JS), "matches": count}
            (el.click if "click" in act else el.hover)(timeout=8000)
        elif "scroll" in act:
            v = act["scroll"]
            pg.evaluate("v => window.scrollTo(0, v === 'bottom' ? document.body.scrollHeight : v)", v)
        elif "press" in act:
            pg.keyboard.press(act["press"])
        elif "wait" in act:
            pg.wait_for_timeout(int(act["wait"]))
        elif act.get("back"):
            pg.go_back(wait_until="domcontentloaded", timeout=10000)
        elif "screenshot" in act:
            pg.screenshot(path=act["screenshot"])
        else:
            raise ValueError(f"unknown action {act!r}")
        pg.wait_for_timeout(settle_ms)
        try:
            pg.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
    # New windows: a popup's Page object only appears once its first response
    # commits, so a slow server can outlast the settle time. Popup navigations
    # are tracked from their first request; wait (bounded) for each to finish.
    deadline = time.monotonic() + popup_timeout_ms / 1000
    while time.monotonic() < deadline and any(
            not n["done"] for n in popup_navs[n_pop:]):
        pg.wait_for_timeout(100)
    for np in new_pages[n_pages:]:
        try:
            np.wait_for_load_state(
                "domcontentloaded",
                timeout=max(1, int((deadline - time.monotonic()) * 1000)))
        except Exception:
            pass
    seen = set()
    for np in new_pages[n_pages:]:
        st = next((n["status"] for n in navs if n["page"] is np), None)
        nav = next((n for n in popup_navs[n_pop:] if n["url"] == np.url
                    or n["status"] is not None and doc_status.get(np.url) == n["status"]), None)
        if st is None:
            st = doc_status.get(np.url)
        if nav is not None:
            seen.add(id(nav))
            if st is None:
                st = nav["status"]
        rec["new_pages"].append({"url": np.url, "status": st,
                                 "timeout": st is None and (nav is None or not nav["done"]),
                                 "failure": nav["failure"] if nav else None})
    # popup navigations whose Page never materialised (slow, failed, blocked)
    for n in popup_navs[n_pop:]:
        if id(n) in seen or any(p["url"] == n["url"] for p in rec["new_pages"]):
            continue
        rec["new_pages"].append({"url": n["url"], "status": n["status"],
                                 "timeout": not n["done"], "failure": n["failure"]})
    rec["navigations"] = [{"url": n["url"], "status": n["status"]}
                          for n in navs[n_nav:] if n["page"] is pg]
    for d in downloads[n_dl:]:
        try:
            fail = d.failure()
        except Exception as e:
            fail = f"{type(e).__name__}: {e}"[:200]
        rec["downloads"].append({"url": d.url, "filename": d.suggested_filename, "failure": fail})
    rec["url_after"] = pg.url
    try:
        rec["dom_changed"] = pg.evaluate(_STATE_JS) != state_before
        rec["new_links"] = sorted({x["url"] for x in pg.evaluate(_LINKS_JS)} - links_before)
    except Exception:
        pass
    return rec

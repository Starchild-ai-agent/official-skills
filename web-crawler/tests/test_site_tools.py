"""Tests for the site-agnostic audit primitives (observation only, no verdicts).

Offline tests always run. Real-browser tests need Playwright and
SITE_AUDIT_BROWSER_TESTS=1.
"""
import functools
import http.server
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import site_tools as st  # noqa: E402

BASE = "https://site.test/dir/page.html"


def _serve(files, log):
    d = tempfile.mkdtemp()
    for name, body in files.items():
        with open(os.path.join(d, name), "w") as f:
            f.write(body)

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=d, **k)

        def log_message(self, *a):
            pass

        def do_GET(self):
            log.append(("GET", self.path))
            if self.path.startswith("/slow"):
                # delayed response headers: /slow404-1500 -> 404 after 1.5s
                import re as _re
                import time as _t
                m = _re.match(r"/slow(\d{3})-(\d+)", self.path)
                code, ms = (int(m.group(1)), int(m.group(2))) if m else (200, 1500)
                _t.sleep(ms / 1000)
                body = b"<html><body>slow</body></html>"
                self.send_response(code)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def do_HEAD(self):
            log.append(("HEAD", self.path))
            super().do_HEAD()

        def do_POST(self):
            log.append(("POST", self.path))
            self.send_response(200)
            self.end_headers()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


class ExtractRefsTests(unittest.TestCase):
    def refs(self, html, base=BASE):
        return st.extract_refs(html, base)

    def by_source(self, html):
        out = {}
        for r in self.refs(html):
            out.setdefault(r["source"], []).append(r["url"])
        return out

    def test_sources_are_reported_not_filtered(self):
        html = """<html><head>
<link rel="canonical" href="/canon"><link rel="preconnect" href="https://cdn.test">
<meta http-equiv="refresh" content="0; url=/moved"></head><body>
<a href="a.html">Go <b>there</b></a><area href="/map">
<img src="i.png" srcset="s1.png 1x, s2.png 2x"><form action="/send"></form>
<div data-href="/hidden" onclick="location.href='/clicked'"></div>
<script>const routes = {"/join": "join.html"}; fetch("https://api.test/x")</script>
</body></html>"""
        s = self.by_source(html)
        self.assertEqual(s["a[href]"], ["https://site.test/dir/a.html"])
        self.assertIn("https://site.test/canon", s["link[rel=canonical]"])
        self.assertIn("https://cdn.test", s["link[rel=preconnect]"])
        self.assertEqual(s["meta[refresh]"], ["https://site.test/moved"])
        self.assertEqual(s["img[srcset]"], ["https://site.test/dir/s1.png",
                                            "https://site.test/dir/s2.png"])
        self.assertEqual(s["form[action]"], ["https://site.test/send"])
        self.assertIn("https://site.test/hidden", s["attr[data-href]"])
        self.assertIn("https://site.test/clicked", s["attr[onclick]"])
        self.assertIn("https://site.test/join", s["inline-script"])
        self.assertIn("https://api.test/x", s["inline-script"])

    def test_link_text_and_base_href(self):
        r = self.refs('<base href="https://other.test/x/"><a href="y">Hello <i>you</i></a>')
        a = [x for x in r if x["source"] == "a[href]"][0]
        self.assertEqual(a["url"], "https://other.test/x/y")
        self.assertEqual(a["text"], "Hello you")

    def test_non_fetchable_hrefs_kept_verbatim(self):
        r = self.refs('<a href="javascript:void(0)">x</a><a href="#top">t</a>')
        self.assertEqual([x["url"] for x in r], ["javascript:void(0)", "#top"])

    def test_malformed_html_does_not_raise(self):
        self.assertTrue(self.refs('<a href="/ok">x<div <<<'))


class SitemapTests(unittest.TestCase):
    def test_namespaces_escapes_cdata(self):
        xml = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://s.test/p?a=1&amp;b=2</loc></url><url><loc><![CDATA[https://s.test/q]]></loc></url>
</urlset>"""
        r = st.parse_sitemap(xml)
        self.assertEqual(r, {"urls": ["https://s.test/p?a=1&b=2", "https://s.test/q"],
                             "sitemaps": [], "error": None})

    def test_index(self):
        r = st.parse_sitemap("<sitemapindex><sitemap><loc>https://s/a.xml</loc></sitemap>"
                             "</sitemapindex>")
        self.assertEqual(r["sitemaps"], ["https://s/a.xml"])

    def test_malformed_falls_back_and_reports(self):
        r = st.parse_sitemap("<urlset><url><loc>https://s/x&amp;y</loc></url>")
        self.assertEqual(r["urls"], ["https://s/x&y"])
        self.assertIn("XML parse error", r["error"])


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = []
        cls.srv, cls.base = _serve({"ok.html": "<title>Ok</title>hi"}, cls.log)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_fetch_returns_raw_status_and_body(self):
        r = st.fetch(self.base + "/ok.html")
        self.assertEqual(r["status"], 200)
        self.assertIn("<title>Ok</title>", r["body"])
        r = st.fetch(self.base + "/missing.html")
        self.assertEqual(r["status"], 404)  # data, not an exception
        self.assertIsNone(r["error"])

    def test_fetch_unreachable_reports_error(self):
        r = st.fetch("http://127.0.0.1:9/x", timeout=2)
        self.assertIsNone(r["status"])
        self.assertTrue(r["error"])

    def test_check_urls_order_and_no_body(self):
        rs = st.check_urls([self.base + "/missing.html", self.base + "/ok.html"])
        self.assertEqual([r["status"] for r in rs], [404, 200])
        self.assertNotIn("body", rs[0])

    def test_same_host(self):
        self.assertTrue(st.same_host("https://www.a.test/x", "http://a.test/y"))
        self.assertFalse(st.same_host("https://a.test", "https://b.test"))


try:
    import playwright.sync_api  # noqa: F401
    _HAS_PW = True
except Exception:
    _HAS_PW = False


@unittest.skipUnless(_HAS_PW and os.environ.get("SITE_AUDIT_BROWSER_TESTS") == "1",
                     "real-browser test: set SITE_AUDIT_BROWSER_TESTS=1 with Playwright")
class BrowseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = []
        cls.srv, cls.base = _serve({
            "home.html": """<html><head><title>Home</title></head><body>
<nav><button id="menu" aria-expanded="false">Menu</button><div id="dd"></div></nav>
<form id="f" action="/submitted" method="post"><input name="q"></form>
<button form="f" id="outside">Outside</button>
<button type="button" id="fav" onclick="fetch('/api/fav',{method:'POST'})">Fav</button>
<button type="button" id="noop">Noop</button>
<a id="blank404" href="missing.html" target="_blank">New tab</a>
<a id="dl" href="ok.html" download>Get</a>
<a id="anchor" href="#sec">Jump</a>
<a id="slow404" href="/slow404-1500" target="_blank">Slow 404</a>
<a id="slow200" href="/slow200-1500" target="_blank">Slow 200</a>
<a id="hang" href="/slow200-4000" target="_blank">Hang</a>
<a id="latepost" href="late-post.html" target="_blank">Late post</a>
<my-el></my-el><img src="nope.png">
<div style="height:2000px"></div><h2 id="sec">Sec</h2>
<script>
document.getElementById('menu').onclick=function(){this.setAttribute('aria-expanded','true');
  document.getElementById('dd').innerHTML='<a href="menu-only.html">M</a>';};
customElements.define('my-el', class extends HTMLElement{connectedCallback(){
  this.attachShadow({mode:'open'}).innerHTML='<a href="shadow.html">S</a>';}});
undefined_call();
</script></body></html>""",
            "ok.html": "<html><body>ok</body></html>",
            # new window that only POSTs well after the click finished
            "late-post.html": """<html><body>late<script>
setTimeout(function(){ fetch('/api/late', {method: 'POST', body: 'x'}); }, 1500);
</script></body></html>""",
            "menu-only.html": "<html><body>m</body></html>",
            "shadow.html": "<html><body>s</body></html>",
        }, cls.log)
        cls.url = cls.base + "/home.html"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_observation_without_actions(self):
        r = st.browse(self.url)
        self.assertIsNone(r["error"], r["error"])
        self.assertEqual((r["status"], r["title"]), (200, "Home"))
        names = {x["url"].rsplit("/", 1)[-1] for x in r["links"]}
        self.assertIn("shadow.html", names)              # shadow DOM
        self.assertNotIn("menu-only.html", names)        # only after a click
        self.assertTrue(any("undefined_call" in e for e in r["page_errors"]))
        self.assertTrue(any(b["status"] == 404 for b in r["bad_responses"]))
        ctl = {c["selector"]: c for c in r["controls"]}
        self.assertTrue(ctl["#outside"]["form_associated"])
        self.assertFalse(ctl["#fav"]["form_associated"])
        self.assertEqual(ctl["#menu"]["aria_expanded"], "false")

    def test_actions_report_what_happened(self):
        r = st.browse(self.url, actions=[
            {"click": "#menu"}, {"click": "#noop"}, {"click": "#blank404"},
            {"click": "#dl"}, {"click": "#anchor"}])
        menu, noop, blank, dl, anchor = r["actions"]
        self.assertTrue(menu["dom_changed"])
        self.assertTrue(any(u.endswith("/menu-only.html") for u in menu["new_links"]))
        self.assertFalse(noop["dom_changed"])
        self.assertEqual(noop["new_links"], [])
        self.assertEqual(blank["new_pages"][0]["status"], 404)   # the new window's own status
        self.assertEqual(blank["element"]["target"], "_blank")
        self.assertEqual(dl["downloads"][0]["failure"], None)
        self.assertTrue(anchor["url_after"].endswith("#sec"))
        self.assertEqual(anchor["navigations"], [])

    def test_writes_blocked_during_actions_by_default(self):
        del self.log[:]
        r = st.browse(self.url, actions=[{"click": "#fav"}])
        self.assertEqual([x for x in self.log if x[0] == "POST"], [])
        self.assertTrue(any("/api/fav" in w["url"] and w["phase"] == "action[0]"
                            for w in r["blocked_writes"]))

    def test_writes_from_late_new_window_still_blocked(self):
        # regression: protection used to end when the click returned, so a
        # new window that POSTed later reached the server
        del self.log[:]
        r = st.browse(self.url, actions=[{"click": "#latepost"}, {"wait": 2500}])
        self.assertEqual([x for x in self.log if x[0] == "POST"], [])
        self.assertTrue(any("/api/late" in w["url"] for w in r["blocked_writes"]),
                        r["blocked_writes"])

    def test_slow_new_window_status_is_captured(self):
        # regression: response headers delayed 1.5s used to yield new_pages == []
        r = st.browse(self.url, actions=[{"click": "#slow404"}, {"click": "#slow200"}])
        a, b = r["actions"]
        self.assertEqual([(p["status"], p["timeout"]) for p in a["new_pages"]], [(404, False)],
                         a["new_pages"])
        self.assertEqual([(p["status"], p["timeout"]) for p in b["new_pages"]], [(200, False)],
                         b["new_pages"])

    def test_new_window_over_wait_cap_is_reported_as_timeout(self):
        r = st.browse(self.url, actions=[{"click": "#hang"}], popup_timeout_ms=1000)
        pages = r["actions"][0]["new_pages"]
        self.assertEqual(len(pages), 1, pages)
        self.assertIsNone(pages[0]["status"])
        self.assertTrue(pages[0]["timeout"])

    def test_missing_target_is_an_action_error(self):
        r = st.browse(self.url, actions=[{"click": "#nope"}])
        self.assertIn("no visible match", r["actions"][0]["error"])


if __name__ == "__main__":
    unittest.main()

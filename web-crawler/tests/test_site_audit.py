"""Offline regression tests for site_audit (no network, no browser).
Run: python -m pytest web-crawler/tests -q
Fixture mirrors the 2026-10-16 numastudios case: a live page referenced only
from an inline script config, Cloudflare email-protection links, preconnect
hints, and JS route strings that 404."""
import os, sys, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import site_audit as sa  # noqa: E402

BASE = "https://site.test"
HOME = """<html><head>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="css/site.css" rel="stylesheet"></head><body>
<a href="planos.html">Planos</a><a href="#top">top</a><a href="mailto:x@y.z">mail</a>
<a href="/cdn-cgi/l/email-protection#abc">email</a>
<a href="https://wa.me/123">WhatsApp</a>
<div data-href="/agenda">Agenda</div>
<script>
  window.cfg = {"chat": {"page": "/quero-fazer-parte"}, "logo": "/images/x.png"};
  if (path === "/qrcode") { window.location.href = "/lp"; }
  fetch("https://cdn.other.test/lib.js");
</script></body></html>"""
QUERO = '<html><body><a href="index.html" class="logo"><img src="images/numa.png"></a></body></html>'
PLAIN = "<html><body><a href='index.html'>home</a></body></html>"

PAGES = {
    BASE + "/": HOME, BASE + "/index.html": HOME, BASE + "/planos.html": PLAIN,
    BASE + "/agenda": PLAIN, BASE + "/quero-fazer-parte": QUERO,
}
STATUS = {"https://wa.me/123": 200, "https://fonts.googleapis.com": 404,
          BASE + "/css/site.css": 200, BASE + "/images/numa.png": 200}


def fake_fetch(url, method="GET", timeout=15, read=True):
    if url in PAGES:
        return {"status": 200, "final_url": url, "body": PAGES[url] if read else "",
                "content_type": "text/html", "error": None}
    return {"status": STATUS.get(url, 404), "final_url": url, "body": "",
            "content_type": "text/plain", "error": None}


class ExtractTests(unittest.TestCase):
    def test_sources_split(self):
        g = sa.extract_urls(HOME, BASE + "/")
        self.assertIn(BASE + "/planos.html", g["a"])
        self.assertIn("https://fonts.googleapis.com", g["hint"])
        self.assertIn(BASE + "/css/site.css", g["asset"])
        # the page a plain <a> crawler misses
        self.assertIn(BASE + "/quero-fazer-parte", g["script"])
        self.assertIn(BASE + "/agenda", g["script"])  # data-href
        # script assets and cross-site URLs are not treated as pages
        self.assertNotIn(BASE + "/images/x.png", g["script"])
        self.assertFalse(any("other.test" in u for u in g["script"]))
        # fragments / mailto dropped
        self.assertFalse(any(u.startswith("mailto") for u in g["a"]))

    def test_sitemap_index(self):
        pages, kids = sa.parse_sitemap("<sitemapindex><sitemap><loc>https://s/a.xml</loc></sitemap></sitemapindex>")
        self.assertEqual((pages, kids), ([], ["https://s/a.xml"]))
        pages, kids = sa.parse_sitemap("<urlset><url><loc> https://s/p </loc></url></urlset>")
        self.assertEqual((pages, kids), (["https://s/p"], []))

    def test_false_positive_notes(self):
        self.assertTrue(sa.false_positive_note(BASE + "/cdn-cgi/l/email-protection"))
        self.assertTrue(sa.false_positive_note("https://fonts.gstatic.com/"))
        self.assertIsNone(sa.false_positive_note(BASE + "/old-home.html"))


class AuditTests(unittest.TestCase):
    def run_audit(self, **kw):
        with mock.patch.object(sa, "_fetch", side_effect=fake_fetch):
            return sa.audit_site(BASE + "/", render=False, **kw)

    def test_finds_script_only_page_and_reports_it(self):
        a = self.run_audit()
        crawled = {p["url"]: p for p in a["pages"]}
        self.assertEqual(crawled[BASE + "/quero-fazer-parte"]["status"], 200)
        self.assertIn(BASE + "/quero-fazer-parte",
                      a["coverage"]["pages_found_only_via_js_or_script"])

    def test_classification(self):
        a = self.run_audit()
        broken = {r["url"] for r in a["broken"]}
        fps = {r["url"] for r in a["false_positives"]}
        script_only = {r["url"] for r in a["script_only_unreachable"]}
        self.assertIn(BASE + "/cdn-cgi/l/email-protection", fps)
        self.assertIn("https://fonts.googleapis.com", fps)
        # JS route strings that 404 are review items, not broken links
        self.assertIn(BASE + "/qrcode", script_only)
        self.assertIn(BASE + "/lp", script_only)
        self.assertEqual(broken, set())

    def test_user_named_url_always_checked(self):
        a = self.run_audit(extra_urls=["/old-home.html"])
        broken = {r["url"]: r for r in a["broken"]}
        self.assertIn(BASE + "/old-home.html", broken)
        self.assertEqual(broken[BASE + "/old-home.html"]["found_via"], ["user"])
        self.assertIn(BASE + "/old-home.html", a["coverage"]["user_named_urls"])

    def test_coverage_states_blind_spots(self):
        a = self.run_audit()
        c = a["coverage"]
        self.assertFalse(c["rendered_dom"])
        self.assertFalse(c["sitemap"])
        self.assertTrue(any("Rendered DOM was NOT inspected" in b for b in c["blind_spots"]))
        self.assertTrue(any("click_check" in b for b in c["blind_spots"]))
        report = sa.format_report(a)
        self.assertIn("## Coverage", report)
        self.assertIn("## Not covered", report)
        self.assertIn("quero-fazer-parte", report)

    def test_max_pages_cap_is_reported(self):
        a = self.run_audit(max_pages=1)
        self.assertTrue(any("max_pages=1" in b for b in a["coverage"]["blind_spots"]))


class ClickReportTests(unittest.TestCase):
    def test_unverified_click_is_never_ok(self):
        a = {"start_url": BASE, "pages": [], "links": [], "broken": [],
             "false_positives": [], "script_only_unreachable": [],
             "coverage": {"pages_crawled": 0, "urls_checked": 0, "robots_txt": False,
                          "sitemap": False, "rendered_dom": False, "rendered_pages": 0,
                          "pages_found_only_via_js_or_script": [], "user_named_urls": [],
                          "blind_spots": []}}
        r = sa.format_report(a, {"logo": {"error": "Playwright unavailable"}})
        self.assertIn("NOT VERIFIED", r)


if __name__ == "__main__":
    unittest.main()


class ClickVerdictTests(unittest.TestCase):
    """Review on #189: a click landing on a 404 was reported OK."""
    base = {"error": None, "covered_by": None, "popup_url": None,
            "final_url": BASE + "/x", "href": "x", "console_errors": []}

    def v(self, **kw):
        return sa.click_verdict({**self.base, **kw})

    def test_http_error_is_fail(self):
        self.assertEqual(self.v(final_status=404), "FAIL")
        self.assertEqual(self.v(final_status=500), "FAIL")

    def test_unknown_status_is_unverified(self):
        self.assertEqual(self.v(final_status=None), "UNVERIFIED")
        self.assertEqual(self.v(final_status=None, popup_url="https://p"), "UNVERIFIED")

    def test_ok_only_when_loaded_and_uncovered(self):
        self.assertEqual(self.v(final_status=200), "OK")
        self.assertEqual(self.v(final_status=200, covered_by="div.overlay"), "FAIL")
        self.assertEqual(self.v(final_status=200, error="click did not navigate"), "FAIL")

    def test_report_shows_fail_for_404(self):
        a = {"start_url": BASE, "pages": [], "links": [], "broken": [],
             "false_positives": [], "script_only_unreachable": [],
             "coverage": {"pages_crawled": 0, "urls_checked": 0, "robots_txt": False,
                          "sitemap": False, "rendered_dom": False, "rendered_pages": 0,
                          "pages_found_only_via_js_or_script": [], "user_named_urls": [],
                          "blind_spots": []}}
        r = sa.format_report(a, {"logo": {"desktop": {**self.base, "final_status": 404}}})
        self.assertIn("[desktop]: FAIL", r)
        self.assertNotIn(": OK", r)


try:
    import playwright.sync_api  # noqa: F401
    _HAS_PW = True
except Exception:
    _HAS_PW = False


@unittest.skipUnless(_HAS_PW and os.environ.get("SITE_AUDIT_BROWSER_TESTS") == "1",
                     "real-browser test: set SITE_AUDIT_BROWSER_TESTS=1 with Playwright")
class ClickCheckBrowserTests(unittest.TestCase):
    """Review on #189: text= targets crashed the cover check (native
    querySelector got a Playwright selector); 404 landings showed OK."""

    @classmethod
    def setUpClass(cls):
        import functools, http.server, tempfile, threading
        cls.dir = tempfile.mkdtemp()
        open(os.path.join(cls.dir, "page.html"), "w").write(
            '<html><body><a href="missing.html">Numa</a> '
            '<a href="ok.html">Home</a></body></html>')
        open(os.path.join(cls.dir, "ok.html"), "w").write("<html><body>ok</body></html>")
        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=cls.dir)
        http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}/page.html"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_text_selector_clicks_and_404_fails(self):
        out = sa.click_check(self.url, "text=Numa", viewports=sa.VIEWPORTS[:1])
        r = out["desktop"]
        self.assertIsNone(r["error"], r)
        self.assertTrue(r["final_url"].endswith("/missing.html"))
        self.assertEqual(r["final_status"], 404)
        self.assertEqual(sa.click_verdict(r), "FAIL")

    def test_text_selector_ok_target(self):
        r = sa.click_check(self.url, "text=Home", viewports=sa.VIEWPORTS[:1])["desktop"]
        self.assertEqual((r["error"], r["final_status"]), (None, 200))
        self.assertEqual(sa.click_verdict(r), "OK")

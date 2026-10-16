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
        # opener's 200 must never stand in for the new window's status
        self.assertEqual(self.v(final_status=200, popup_url="https://p",
                                final_url=BASE + "/page.html"), "UNVERIFIED")

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


class Priority1OfflineTests(unittest.TestCase):
    """Review follow-up: restricted != fine; one render failure must not stop rendering."""

    def test_restricted_is_unverified_not_false_positive(self):
        pages = {BASE + "/": '<a href="https://x.test/members">m</a><a href="/admin">a</a>'}

        def fetch(url, method="GET", timeout=15, read=True):
            if url in pages:
                return {"status": 200, "final_url": url, "body": pages[url],
                        "content_type": "text/html", "error": None}
            st = {"https://x.test/members": 403, BASE + "/admin": 401}.get(url, 404)
            return {"status": st, "final_url": url, "body": "", "content_type": "",
                    "error": None}
        with mock.patch.object(sa, "_fetch", side_effect=fetch):
            a = sa.audit_site(BASE + "/", render=False)
        restricted = {r["url"] for r in a["restricted"]}
        self.assertEqual(restricted, {"https://x.test/members", BASE + "/admin"})
        self.assertFalse(a["false_positives"])
        self.assertTrue(any("unverified" in b for b in a["coverage"]["blind_spots"]))
        self.assertIn("NOT verified", sa.format_report(a))

    def test_one_render_failure_does_not_stop_rendering(self):
        calls = []

        def render(self, url):
            calls.append(url)
            if len(calls) == 1:
                return None, "TimeoutError: page hung"
            return set(), None
        with mock.patch.object(sa, "_fetch", side_effect=fake_fetch), \
                mock.patch.object(sa._Renderer, "render", render), \
                mock.patch.object(sa._Renderer, "close", lambda self: None):
            a = sa.audit_site(BASE + "/", render=True)
        states = [p["render"] for p in a["pages"] if p["status"] == 200]
        self.assertEqual(states[0], "failed")
        self.assertIn("rendered", states[1:])
        self.assertEqual(a["coverage"]["render_counts"]["failed"], 1)
        self.assertTrue(a["coverage"]["rendered_dom"])
        self.assertIn("TimeoutError", sa.format_report(a))

    def test_render_cap_is_recorded_per_page(self):
        with mock.patch.object(sa, "_fetch", side_effect=fake_fetch), \
                mock.patch.object(sa._Renderer, "render", lambda self, u: (set(), None)), \
                mock.patch.object(sa._Renderer, "close", lambda self: None):
            a = sa.audit_site(BASE + "/", render=True, max_render=1)
        notes = [p["render_note"] for p in a["pages"] if p["render"] == "skipped"
                 and p["render_note"] != "not an HTML 200 page"]
        self.assertTrue(notes and all("max_render=1" in n for n in notes), notes)
        self.assertTrue(any("were not rendered" in b for b in a["coverage"]["blind_spots"]))

    def test_time_budget_reports_unvisited(self):
        with mock.patch.object(sa, "_fetch", side_effect=fake_fetch):
            a = sa.audit_site(BASE + "/", render=False, max_seconds=-1)
        self.assertEqual(a["coverage"]["budget_hit"], "max_seconds=-1")
        self.assertTrue(a["coverage"]["unvisited"])


class OutcomeVerdictTests(unittest.TestCase):
    def v(self, **kw):
        return sa.click_verdict({"error": None, "covered_by": None, "click_error": None,
                                 "popup_url": None, "final_url": BASE + "/", **kw})

    def test_in_page_outcomes_are_facts_not_failures(self):
        self.assertEqual(self.v(outcome="dom_change"), "CHANGED")
        self.assertEqual(self.v(outcome="no_change"), "NO_CHANGE")
        self.assertEqual(self.v(outcome="client_navigation"), "CHANGED")
        self.assertEqual(self.v(outcome="anchor"), "OK")

    def test_expectation_decides(self):
        self.assertEqual(self.v(outcome="dom_change", expect="change"), "OK")
        self.assertEqual(self.v(outcome="dom_change", expect="navigate"), "FAIL")
        self.assertEqual(self.v(outcome="no_change", expect="change"), "FAIL")

    def test_click_error_and_download(self):
        self.assertEqual(self.v(click_error="TimeoutError"), "FAIL")
        self.assertEqual(self.v(outcome="download", download={"failure": None}), "OK")
        self.assertEqual(self.v(outcome="download", download={"failure": "canceled"}), "FAIL")



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
            '<a href="ok.html">Home</a> '
            '<a href="missing.html" target="_blank">NewTab404</a> '
            '<a href="ok.html" target="_blank">NewTabOK</a> '
            '<button id="menu" aria-expanded="false">Menu</button>'
            '<div id="drop" hidden>items</div> <button id="noop">Noop</button> '
            '<a href="#sec">ToSec</a> <a href="#nowhere">ToNowhere</a> '
            '<a href="ok.html" download>Get</a>'
            '<div style="height:3000px"></div><h2 id="sec">Section</h2>'
            "<script>document.getElementById('menu').onclick=function(){"
            "this.setAttribute('aria-expanded','true');"
            "document.getElementById('drop').hidden=false;};</script></body></html>")
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


    def test_new_window_404_fails_on_both_viewports(self):
        out = sa.click_check(self.url, "text=NewTab404")
        for vp in ("desktop", "mobile"):
            r = out[vp]
            self.assertTrue(r["popup_url"].endswith("/missing.html"), r)
            self.assertEqual(r["final_status"], 404, r)
            self.assertEqual(sa.click_verdict(r), "FAIL", r)

    def test_new_window_ok(self):
        r = sa.click_check(self.url, "text=NewTabOK", viewports=sa.VIEWPORTS[:1])["desktop"]
        self.assertEqual((r["final_status"], sa.click_verdict(r)), (200, "OK"), r)


    def test_menu_toggle_is_changed_not_fail(self):
        r = sa.click_check(self.url, "#menu", viewports=sa.VIEWPORTS[:1])["desktop"]
        self.assertEqual((r["outcome"], r["verdict"]), ("dom_change", "CHANGED"), r)
        r = sa.click_check(self.url, "#menu", viewports=sa.VIEWPORTS[:1],
                           expect="change")["desktop"]
        self.assertEqual(r["verdict"], "OK", r)

    def test_noop_is_no_change(self):
        r = sa.click_check(self.url, "#noop", viewports=sa.VIEWPORTS[:1])["desktop"]
        self.assertEqual((r["outcome"], r["verdict"]), ("no_change", "NO_CHANGE"), r)

    def test_anchor_ok_and_missing_target(self):
        r = sa.click_check(self.url, "text=ToSec", viewports=sa.VIEWPORTS[:1])["desktop"]
        self.assertEqual((r["outcome"], r["verdict"]), ("anchor", "OK"), r)
        r = sa.click_check(self.url, "text=ToNowhere", viewports=sa.VIEWPORTS[:1])["desktop"]
        self.assertEqual((r["outcome"], r["verdict"]), ("anchor", "FAIL"), r)

    def test_download(self):
        r = sa.click_check(self.url, "text=Get", viewports=sa.VIEWPORTS[:1])["desktop"]
        self.assertEqual((r["outcome"], r["verdict"]), ("download", "OK"), r)

    def test_evidence_saved_for_non_ok(self):
        import tempfile
        d = tempfile.mkdtemp()
        r = sa.click_check(self.url, "text=NewTab404", viewports=sa.VIEWPORTS[:1],
                           evidence_dir=d)["desktop"]
        self.assertEqual(r["verdict"], "FAIL")
        self.assertTrue(r["evidence"] and os.path.exists(r["evidence"]), r)

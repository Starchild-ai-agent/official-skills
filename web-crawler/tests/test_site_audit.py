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

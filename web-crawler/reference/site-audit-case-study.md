# Case study: "check every link on my site"

A real audit, anonymised. It shows how a link-only, status-only check gave a
confident wrong answer, and what the method above finds instead.

## The request

A user asked the agent to check every link on a small static marketing site
(about a dozen pages, hosted on a site builder). Later they added: "the logo on
the *join us* page sends me to a page that doesn't exist."

## What went wrong the first time

1. The agent crawled `<a href>` links only. The join page was not linked from
   any `<a>`. The site reached it through a small inline script that mapped
   button clicks to paths, so the crawler never saw it.
2. The agent fetched each URL, saw 200s, and replied "all links work".
3. After the user named the page, the agent repeated the same crawl without
   opening that page, and said the site had fewer pages than it really did.

## Doing it with the method

**Map from several sources.** `extract_refs(home)` showed the join path under
`source="inline-script"` next to other route strings. Reading the surrounding
script confirmed it was a click → path map. The sitemap listed it too. The
reconciled map had about 12 pages, against the 8 found from `<a>` links.

**Error signature.** A random path returned a real 404 from the host, so
status codes could be trusted on this site.

**Check references.** All internal pages returned 200. One old URL the user
remembered (`/old-home.html`) returned 404, but no page or script referenced
it. It was most likely a cached bookmark, so it was reported as "404 but not
linked from the site", not as a broken link.

**Click what users click.** `browse(join_url, actions=[{"click": <logo selector>}])`
at 1280px and 390px (mobile): `navigations` showed the home page with status
200 in both, and the element was not covered. The logo worked. The user's
report could not be reproduced on the current site, and the reply said exactly
that, with the evidence.

## Lessons that generalise

- A page the user names but your map lacks means your map is wrong. Find out
  how the site reaches that page.
- Read `inline-script` and `attr[...]` references yourself. They are where
  hidden routes live.
- A 200 response proves nothing about a click. Click it, at each viewport.
- "Can't reproduce" with evidence is a valid result. "All good" without
  coverage is not.

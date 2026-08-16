# Local Web Development

Driving the browser against the user's local dev server — `localhost`,
`127.0.0.1`, `::1`, or local network URLs. The extra concerns are refresh
timing and not fighting the dev server.

## Getting oriented

- Open the dev URL with `tab_open {url}` (background by default — dev
  verification rarely needs the user's screen; use `page_screenshot` to show
  findings instead, see `screenshots.md`). For the user's own dev machine,
  the extension's browser can reach their local server directly.
- First `page_snapshot` tells you if the server is even up: a connection
  error / "site can't be reached" state means the dev server is not running
  (or not on that port). Report that plainly rather than retrying in a loop —
  the server doesn't start itself.
- Confirm you are on the right port/URL; dev setups often run several
  (frontend on 3000, backend on 8000, storybook on 6006).

## After code or build changes

- Hot reload (Vite, Next dev mode, HMR) usually updates the page on its own.
  Verify with a fresh `page_snapshot` rather than reloading blindly.
- If the framework has no hot reload, is in a production build, or HMR is
  disabled/hung: `tab_navigate` to the same URL to force a reload, then take
  a fresh snapshot or screenshot before verifying anything. Old snapshots
  are worthless after a rebuild.
- Signs you need a hard reload: snapshot unchanged after an obvious code
  change, stale asset errors, or half-updated pages. Prefer one deliberate
  reload over repeated "maybe it refreshed?" snapshots.

## Verification loop

- Snapshot for content/behavior checks; screenshot for layout/rendering
  checks. A visual regression ("the button moved", "styles broke") is only
  provable visually.
- `wait_for {selector}` is useful after reloads: dev servers and lazy bundles
  make pages settle late; wait for the root element or a key component
  instead of snapshotting a blank page and concluding the app is broken.
- Console-level errors are not visible in snapshots; if behavior is wrong
  with no visual cue, say what you observed and suggest the user check the
  dev console — you see the DOM, not the logs.

## Cautions

- Local dev servers often auto-refresh, redirect (http→https, trailing
  slash), or show auth prompts — each invalidates your refs. Re-snapshot
  after any of these before interacting (see `api-use-behavior.md`).
- Don't restart the user's dev server or run build commands from the browser
  skill; that belongs to the shell, not the browser.
- Dev-only overlays (error overlays, HRM badges) can sit atop the page and
  intercept clicks. If clicks land oddly, snapshot — the overlay's elements
  will be in the list.

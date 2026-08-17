# File Uploads

**Status: not supported.** The current `mcp__browser__*` toolset has no file
upload capability: no tool can set files on an `input[type=file]`, and
`element_click` cannot drive the native OS file picker (the picker belongs to
the OS, not the page — clicking "Choose file" would open a dialog only the
user can operate). This document explains how to recognize the situation and
what to do instead.

## How to recognize it

- A form contains a file input. `page_snapshot`'s `elements[]` will show it
  as an `input` (tag) whose `ariaLabel`/`text` is empty or "Choose file" /
  "No file chosen" — file inputs generally expose no useful text.
- An upload button that opens a modal with drag-and-drop. Uploading requires
  injecting a File into the page, which the current tools cannot do.
- Clicking upload controls may open a native dialog that then blocks the tab
  for you. Do not click into upload controls you cannot complete.

## What to do instead

0. **Do not search the user's machine.** `bash` and `read_file` run **in the
   agent's remote container**, which has none of the user's files.
   `local_shell` runs on the user's machine only if they have the
   `starchild agent-shell` daemon installed and authorized — most users do
   not, so it is usually unavailable or denied. Either way, running shell
   commands to locate or read the user's local files (Downloads, Desktop,
   Documents, etc.) is wrong: it cannot reliably work and burns turns. The
   only dependable path to a user-local file is the browser's native file
   picker, which only the user can operate.

1. **Hand off to the user, precisely.** State what to upload and where:
   "The form needs your passport scan — the file chooser only works for you
   directly. Could you attach it in the tab I have open, then tell me when
   it's done?" Leave the tab open at the right step (a handoff tab — see
   `tab-cleanup-chrome.md`).
   - If the user named a file by description ("the Meituan earnings report"),
     do **not** try to resolve it to a path yourself. Tell them to pick the
     matching file in the chooser; they know which one it is.
2. **Continue after the user uploads.** When they confirm, `page_snapshot`
   to verify the file registered (the input usually changes to the file
   name, or a file chip/thumbnail appears), then continue the flow. Verify
   rather than trusting — a mis-uploaded or missing file should be caught
   before any submit.
3. **Never fake it.** Do not submit a form pretending an upload happened,
   and do not claim a file was attached when the snapshot doesn't show one.
4. If the task is *fundamentally* about getting a file onto a site and the
   site has no alternative (no API, no email-in option), the honest answer
   is: this step needs the user.

## Expected future shape (orientation only)

Upload support, when added, is expected to take the form of an explicit
upload tool: you specify the element (by ref) plus a file already available
to the agent (e.g. in the workspace), and the tool attaches it as the page's
file input value — bypassing the native picker entirely. Refs would follow
the usual staleness rules; confirmation policy for transmitting personal
files (`browser-safety.md`) would still apply.

Until such a tool actually appears in the session's tool list, uploads
remain user-only steps.

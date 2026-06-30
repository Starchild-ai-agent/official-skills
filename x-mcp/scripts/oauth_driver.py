#!/usr/bin/env python3
"""Persistent xurl headless OAuth driver.
Keeps xurl's stdin open until a code arrives via CODE_FILE, then feeds it."""
import subprocess, time, os, json, sys, fcntl

CODE_FILE = "/tmp/xurl_code_input.txt"
URL_FILE  = "/tmp/xurl_auth_url.txt"
DONE_FILE = "/tmp/xurl_oauth_done.json"
PID_FILE  = "/tmp/xurl_oauth.pid"

for f in (CODE_FILE, URL_FILE, DONE_FILE):
    try: os.remove(f)
    except FileNotFoundError: pass

# NOTE: no USERNAME arg. xurl resolves the account via /2/users/me and stores the
# token under the resolved X handle key, e.g. apps.starchild-x.oauth2_tokens['ud_noel']
# (NOT an empty-string key). Downstream readers must discover the key dynamically:
#   toks = d['apps']['starchild-x']['oauth2_tokens']; key = next(iter(toks))
# Never hardcode the handle or '' — that KeyErrors on a different account.
proc = subprocess.Popen(
    ["xurl", "auth", "oauth2", "--app", "starchild-x", "--headless"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    bufsize=0,
)
with open(PID_FILE, "w") as f: f.write(str(proc.pid))

# Non-blocking read
fd = proc.stdout.fileno()
fl = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

# Phase 1: capture authorize URL
buf = b""
url = None
deadline = time.time() + 20
while time.time() < deadline:
    try:
        chunk = os.read(fd, 4096)
        if chunk: buf += chunk
    except BlockingIOError: pass
    for line in buf.decode("utf-8", "replace").splitlines():
        if "oauth2/authorize" in line:
            url = line.strip()
            break
    if url: break
    if proc.poll() is not None:
        with open(DONE_FILE, "w") as f:
            json.dump({"error": "xurl exited before printing URL",
                       "out": buf.decode("utf-8", "replace")}, f, indent=2)
        sys.exit(1)
    time.sleep(0.3)

if not url:
    with open(DONE_FILE, "w") as f:
        json.dump({"error": "no URL found", "out": buf.decode("utf-8","replace")}, f, indent=2)
    sys.exit(1)

with open(URL_FILE, "w") as f: f.write(url)

# Phase 2: wait for code file (up to 10 min)
deadline = time.time() + 600   # ~10 min for the user to authorize (matches SKILL.md)
code = None
while time.time() < deadline:
    if os.path.exists(CODE_FILE):
        c = open(CODE_FILE).read().strip()
        if c:
            code = c
            break
    if proc.poll() is not None:
        with open(DONE_FILE, "w") as f:
            json.dump({"error": "xurl died waiting for code",
                       "out": buf.decode("utf-8","replace")}, f, indent=2)
        sys.exit(1)
    time.sleep(1)

if not code:
    with open(DONE_FILE, "w") as f: json.dump({"error": "code timeout"}, f)
    proc.kill(); sys.exit(1)

# Phase 3: feed code to xurl
proc.stdin.write((code + "\n").encode())
proc.stdin.flush()

# Phase 4: read result
time.sleep(3)
result = b""
deadline2 = time.time() + 15
while time.time() < deadline2:
    try:
        chunk = os.read(fd, 4096)
        if chunk: result += chunk
        else: break
    except BlockingIOError: pass
    if proc.poll() is not None: break
    time.sleep(0.3)

try:
    proc.wait(timeout=5)
except subprocess.TimeoutExpired:
    proc.kill()

with open(DONE_FILE, "w") as f:
    json.dump({"exit": proc.returncode,
               "out": (buf + result).decode("utf-8", "replace")}, f, indent=2)

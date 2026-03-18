---
name: starchild-doctor
version: 1.0.0
description: Diagnose and troubleshoot Starchild agent issues — checks service health, memory, disk, logs, sessions, and scheduled tasks to identify what went wrong.

metadata:
  starchild:
    emoji: "🩺"

user-invocable: true
---

# Starchild Doctor — Agent Diagnostics

You are running a structured health check on this machine. Work through each section below **in order**, executing the bash commands, then write a final report. Do not skip sections.

**Always respond in the user's language.**

---

## Step 1: Service Health

Check if the main service process is alive:

```bash
python3 -c "
import urllib.request, json
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)
    print('SERVICE: OK —', r.read().decode())
except Exception as e:
    print('SERVICE: DEAD —', e)
"
```

Check the process list:

```bash
ps aux | grep -E "uvicorn|python" | grep -v grep
```

---

## Step 2: Memory & Disk

```bash
# Memory usage
cat /sys/fs/cgroup/memory/memory.usage_in_bytes 2>/dev/null | awk '{printf "Memory used: %.1f MB\n", $1/1024/1024}' || free -m | awk 'NR==2{printf "Memory used: %s MB / %s MB\n", $3, $2}'

# OOM kill history
cat /sys/fs/cgroup/memory/memory.oom_control 2>/dev/null || echo "(cgroup oom_control not available)"

# Disk usage
df -h / /data 2>/dev/null || df -h /

# Data directory sizes
du -sh /data/* 2>/dev/null || echo "(no /data directory)"
```

---

## Step 3: Log File Overview

```bash
ls -lah /data/logs/ 2>/dev/null || echo "(no /data/logs directory)"
```

Count archive files — many short-interval archives mean frequent restarts:

```bash
ls /data/logs/*.log 2>/dev/null | wc -l
```

Read the last 300 lines of the current log and extract the key events:

```bash
tail -300 /data/logs/app.log 2>/dev/null | grep -E "TURN|Agent completed|Marked run|stop=|ERROR|WARNING|safety limit|active runs|Available tools|OOM|killed|timeout|overload|Overload"
```

If the above returns nothing useful, read the raw tail:

```bash
tail -100 /data/logs/app.log 2>/dev/null
```

---

## Step 4: Error Detection

Count and show all errors in the current log:

```bash
grep -c "ERROR" /data/logs/app.log 2>/dev/null && grep "ERROR" /data/logs/app.log 2>/dev/null | tail -20
```

Check for circuit breaker triggers:

```bash
grep -E "circuit_breaker|Circuit breaker" /data/logs/app.log 2>/dev/null | tail -10
```

Check for API timeouts and overloads:

```bash
grep -E "timeout|Overload|overload|529|503" /data/logs/app.log 2>/dev/null | tail -10
```

---

## Step 5: Active Run Status

Check if any agent runs are currently stuck or active:

```bash
grep "Marked run" /data/logs/app.log 2>/dev/null | tail -10
```

- `Marked run as completed` = normal end
- `Marked run as error` = error termination
- Last run has neither = may be live or zombie

---

## Step 6: Session Files

```bash
ls -lah /data/sessions/ 2>/dev/null || echo "(no sessions)"
```

Check for corrupted sessions (those ending with `assistant` role cause prefill errors):

```bash
python3 -c "
import os, json, glob
session_dir = '/data/sessions'
if not os.path.exists(session_dir):
    print('No sessions directory')
else:
    files = glob.glob(os.path.join(session_dir, '*.json'))
    print(f'Total session files: {len(files)}')
    for f in sorted(files, key=os.path.getmtime)[-5:]:
        try:
            with open(f) as fh:
                data = json.load(fh)
            msgs = data.get('messages', [])
            last_role = msgs[-1]['role'] if msgs else 'empty'
            size_kb = os.path.getsize(f) // 1024
            print(f'{os.path.basename(f)}: {len(msgs)} msgs, last_role={last_role}, {size_kb}KB')
        except Exception as e:
            print(f'{os.path.basename(f)}: ERROR reading — {e}')
" 2>/dev/null
```

---

## Step 7: Scheduled Tasks

```bash
ls -lah /data/scheduled_logs/ 2>/dev/null || echo "(no scheduled task logs)"
```

If any scheduled logs exist, check the most recent one:

```bash
ls -t /data/scheduled_logs/*.log 2>/dev/null | head -3 | xargs -I{} sh -c 'echo "=== {} ==="; tail -20 {}'
```

---

## Step 8: Model Routing (Smart Router)

Check which models have been used in recent runs:

```bash
grep "\[API\]" /data/logs/app.log 2>/dev/null | tail -20 | grep -oE "model=[^ ]+" | sort | uniq -c | sort -rn
```

Note: `gemini-flash-lite` or similar weak models routing complex tasks can trigger circuit breakers.

---

## Report Format

After collecting all data, produce a structured report:

```
🩺 DOCTOR REPORT
════════════════════════════════════

🟢/🔴 SERVICE: <OK or DEAD, with detail>
💾 MEMORY: <used MB / limit MB, OOM kills if any>
💿 DISK: <usage, flag if >80%>

📋 LOG SUMMARY
  Archives: <count> (last restart: <timestamp from filename>)
  Errors: <count in current log>
  Last activity: <what the last few log lines show>

⚠️  ISSUES FOUND
  • <each specific problem, one per bullet>
  • (or "None detected" if clean)

🔍 ROOT CAUSE
  <Best explanation of what caused the user's reported problem>

✅ RECOMMENDED ACTIONS
  1. <Most important fix first>
  2. <Next step>
  ...
```

---

## Quick Reference: Common Problems & Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Service DEAD | uvicorn process crashed | Restart the machine |
| Zombie run (no response) | ActiveRunRegistry not cleaned | Restart the machine |
| Circuit breaker fired | Weak model hallucinated tool name | Check which model was routed; consider `/model` switch |
| `prefill` / `thinking` error | Session corrupted (ends with assistant) | Delete or fix session JSON |
| OOM kill | Memory limit exceeded | Check session/log sizes; clear large files |
| Scheduled task not firing | Session corrupted or push error | Check `/data/scheduled_logs/` + session last role |
| Empty replies | Weak model returning empty content | Switch to stronger model |
| Context too large | Session > 850K tokens | Start a new thread |

If the user tells you what specific behavior they observed, focus your analysis on the most likely cause from this table.

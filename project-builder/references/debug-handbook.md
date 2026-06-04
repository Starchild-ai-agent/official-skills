# Debug Handbook — Systematic Diagnosis

**When something goes wrong, follow a system. Don't guess.**

## The Debug Protocol

```
1. CHECK LOGS → Read existing logs/errors first — they often reveal the cause directly
2. REPRODUCE  → See the actual failure (not just the user's description)
3. ISOLATE    → Which layer/component is broken?
4. DIAGNOSE   → What specifically is wrong?
5. FIX        → Targeted fix for the root cause
6. VERIFY     → Prove the fix works with the same reproduction steps
7. REGRESS    → Make sure the fix didn't break something else
```

**Step 1 — Check logs first:**
- Tasks: `get_scheduled_task_log(job_id)` — full stdout + stderr
- Previews: `preview_check(preview_id)` + check process output
- Scripts: read stderr from last run
- If logs reveal a clear root cause (e.g. traceback, API 401, missing env var), skip straight to FIX — no need to reproduce what you can already see.

**Rules:**
- Always check logs before attempting reproduction.
- Never fix without diagnosing. "I added some error handling" is not a fix.
- Never declare fixed without step 6. "Should work now" is not verification.
- If the same fix fails twice, STOP. The diagnosis is wrong — go back to step 3.

---

## Debugging Scheduled Tasks

**Step 1: See what actually happened**
```
get_scheduled_task_log(job_id="xxx")    # Full stdout + stderr of last run
list_scheduled_tasks()                   # Status, next run, last result
```

**Step 2: Isolate the layer**

Run the script manually with diagnostic output:
```bash
python3 tasks/{id}/run.py 2>&1
```

The task pipeline has these layers — check them in order:

```
Layer 1: DATA FETCH   → Did the API call succeed? Did it return valid data?
Layer 2: VALIDATION   → Did validation catch bad data, or let it through?
Layer 3: PROCESSING   → Did analysis/formatting produce correct output?
Layer 4: LLM (if any) → Did the LLM hallucinate numbers or ignore injected data?
Layer 5: OUTPUT       → Is the final print correct? Formatting issues?
```

**Layer-by-layer diagnosis:**
```python
# Add temporary debug prints to isolate:
data = fetch_prices()
print(f"[DEBUG L1] Raw API response: {json.dumps(data)}", file=sys.stderr)

validated = validate(data)
print(f"[DEBUG L2] After validation: {validated}", file=sys.stderr)

result = process(validated)
print(f"[DEBUG L3] After processing: {result}", file=sys.stderr)

# If LLM is involved:
llm_response = call_agent(prompt)
print(f"[DEBUG L4] LLM response: {llm_response[:200]}", file=sys.stderr)
# Compare numbers in llm_response with validated data

output = format_output(result)
print(f"[DEBUG L5] Final output: {output}", file=sys.stderr)
```

**Common task issues:**

| Symptom | Layer | Likely cause | Fix |
|---------|-------|-------------|-----|
| No output (silent) | L1 or L5 | API returned error; or output was empty | Check API response code + body |
| Wrong numbers | L1 or L4 | API returned stale data; or LLM hallucinated | Compare raw API response vs output |
| Old/duplicate alerts | L3 | Dedup logic broken or missing | Check dedup store, verify timestamps |
| Runs but no push | L5 | stdout was empty (auto-silenced) | Verify `print()` is reached |
| Task never runs | — | Schedule parse error or task paused | Check `list_scheduled_tasks()` status |
| Crashes with traceback | L1-L3 | Unhandled exception | Read the traceback, fix the exception |

---

## Debugging Previews / Dashboards

**Step 1: Check the preview service**
```bash
cat /data/previews.json                        # Is it running?
curl -s -o /dev/null -w "%{http_code}" http://localhost:{port}  # Is it responding?
preview_check(preview_id="xxx")                # Detailed diagnostics
```

**Step 2: Isolate frontend vs backend**
```bash
# Backend OK?
curl -s http://localhost:{port}/api/data | head -50

# Frontend OK?
curl -s http://localhost:{port}/ | head -30
```

**Common preview issues:**

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Blank page | JS error, CDN blocked | Read HTML source, check for script errors |
| "Directory listing" | No command/port, or no index.html | Add command+port to preview_serve |
| 404 on resources | Absolute paths in HTML/JS/CSS | Change `/path` to `./path` everywhere |
| CORS error | Frontend calling external API directly | Add backend proxy endpoint |
| Data shows "undefined" | API endpoint returns unexpected shape | curl the endpoint, check JSON structure |
| "Connection failed" | Process crashed or wrong port | Check command, read error log |
| Stale data | Caching or frontend not re-fetching | Add cache-busting, check polling logic |
| **Charts keep growing / page height explodes** | Chart container has no fixed px height, or chart.resize() in ResizeObserver loop | Set explicit `height: Npx` + `position: relative` + `overflow: hidden` on chart container. See `project-design/references/charts.md` "Chart Container Anti-Expansion" section |

**Fix in place:** Use `edit_file` to fix the specific bug. Don't create new files. Then `preview_stop` + `preview_serve` to restart.

---

## Debugging Scripts

```bash
# Run with full error output
python3 scripts/my_script.py 2>&1

# Module issue?
pip list | grep <package>

# Env var issue?
echo $RELEVANT_VAR

# Network issue?
curl -v "https://api.example.com/endpoint" 2>&1 | tail -20
```

---

## The Three-Strike Rule

If the same approach fails twice with similar errors:

1. **STOP editing the same code**
2. **Re-read the error** — the full traceback, not just the last line
3. **Print the actual API/data response** — don't assume what it returns
4. **Try a fundamentally different approach** — different API, different logic, different architecture
5. **Tell the user** what you've tried, what failed, and what you're trying next

```
❌ Bad:  Fix → fail → tweak same fix → fail → tweak again → fail
✅ Good: Fix → fail → fix again → fail → STOP → rethink → explain to user → new approach
```

---

## When the User Reports a Problem

**Always:**
1. Reproduce the issue yourself first (run the script, curl the endpoint, check the preview)
2. Show the user what you found: "I ran the script and got X — here's what's wrong"
3. Fix with evidence, not hope
4. Verify by running the same reproduction after the fix

**Never:**
- "I've fixed it!" (without running the fix)
- "Try again now" (without verifying yourself first)
- "That shouldn't happen" (something happened — investigate)
- Blame the user's input/environment before checking your own code

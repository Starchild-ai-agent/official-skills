#!/usr/bin/env python3
"""Selftest for cjk_punctuation.py (one script, two events).
Run: python3 cjk_punctuation_selftest.py"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "cjk_punctuation.py")

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  \u2713 {name}")
    else:
        FAIL += 1
        print(f"  \u2717 {name} \u2014 {detail}")


def _run(ev, env_extra=None):
    env = dict(os.environ)
    for k in ("CJK_PUNCT_PARENS", "CJK_PUNCT_EAT_SPACE", "CJK_PUNCT_EXTENSIONS"):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        [sys.executable, SCRIPT], input=json.dumps(ev),
        capture_output=True, text=True, timeout=15, env=env,
    )
    out = (p.stdout or "").strip()
    return json.loads(out) if out else {}


def resp(text, env_extra=None):
    """on_response_end → rewritten reply, or None when unchanged."""
    return _run({"event": "on_response_end", "response": text}, env_extra).get("response")


print("── conversion: the basic case ──")
r = resp("对,这正好否掉了一个方案")
check("comma after CJK", r == "对，这正好否掉了一个方案", repr(r))
r = resp("有必要;但不能只靠 prompt")
check("semicolon after CJK", r == "有必要；但不能只靠 prompt", repr(r))
r = resp("结论:这条路不通")
check("colon after CJK", r == "结论：这条路不通", repr(r))
r = resp("真的吗?我不信!")
check("question + exclamation", r == "真的吗？我不信！", repr(r))

print("\n── neighbour rule ──")
r = resp("PR #1117, 修复了这个问题")
check("mark before CJK converts, space eaten", r == "PR #1117，修复了这个问题", repr(r))
r = resp("中文, English follows")
check("mark after CJK converts, space eaten", r == "中文，English follows", repr(r))
r = resp("看 foo(a, b) 这个函数")
check("no CJK neighbour: untouched", r is None, repr(r))
r = resp("金额是 1,000 元")
check("thousands separator untouched", r is None, repr(r))
r = resp("时间 12:30 开始,地点未定")
check("digit colon untouched, CJK comma converted",
      r == "时间 12:30 开始，地点未定", repr(r))
r = resp("看 foo , bar 这里")
check("space before mark: left alone", r is None, repr(r))

print("\n── protected spans ──")
r = resp("修改 `foo(a, b)` 这里,注意")
check("inline code untouched", r == "修改 `foo(a, b)` 这里，注意", repr(r))
r = resp("看文档:\n```py\nd = {'a': 1, 'b': 2}\n```\n就这样,懂了吗")
check("fenced block untouched",
      r is not None and "{'a': 1, 'b': 2}" in r and r.endswith("就这样，懂了吗"), repr(r))
r = resp("见 https://x.com/a?b=1,2 这个链接,谢谢")
check("url untouched", r == "见 https://x.com/a?b=1,2 这个链接，谢谢", repr(r))
r = resp("见 [中文,标题](https://x.com/a,b) 这里")
check("markdown: label converted, target untouched",
      r == "见 [中文，标题](https://x.com/a,b) 这里", repr(r))

print("\n── no-ops ──")
check("pure English untouched", resp("Fixed the parser, added tests.") is None)
check("empty reply untouched", resp("") is None)
check("already full-width untouched", resp("对，这就是结论。") is None)

print("\n── config ──")
r = resp("看(这里)的说明", {"CJK_PUNCT_PARENS": "1"})
check("parens opt-in via env", r == "看（这里）的说明", repr(r))
check("parens off by default", resp("看(这里)的说明") is None)
r = resp("中文, English", {"CJK_PUNCT_EAT_SPACE": "0"})
check("space kept when EAT_SPACE off", r == "中文， English", repr(r))

print("\n── pre_tool_call: prose files only ──")


def tool(name, tool_input, env_extra=None):
    return _run({"event": "pre_tool_call", "tool_name": name,
                 "tool_input": tool_input}, env_extra).get("tool_input")


r = tool("write_file", {"path": "output/post.md", "content": "标题,正文"})
check("write_file .md rewritten", r == {"content": "标题，正文"}, repr(r))
r = tool("edit_file", {"path": "a.md", "old_string": "旧,文", "new_string": "新,文"})
check("edit_file rewrites new_string only", r == {"new_string": "新，文"}, repr(r))
check("yaml skipped (colon is syntax)",
      tool("write_file", {"path": "c.yaml", "content": "名称: 值,备注"}) is None)
check("json skipped", tool("write_file", {"path": "c.json", "content": '{"a": "中文,x"}'}) is None)
check("python skipped", tool("write_file", {"path": "a.py", "content": "x = 1  # 注释,说明"}) is None)
check("csv skipped", tool("write_file", {"path": "a.csv", "content": "名称,数量"}) is None)
check("other tools ignored",
      tool("bash", {"command": "echo 中文,测试"}) is None)
r = tool("write_file", {"path": "a.rst", "content": "标题,正文"}, {"CJK_PUNCT_EXTENSIONS": ".rst"})
check("extension allowlist via env", r == {"content": "标题，正文"}, repr(r))

print("\n── dispatch safety ──")
check("unknown event: no-op", _run({"event": "post_tool_call", "tool_name": "bash"}) == {})
p = subprocess.run([sys.executable, SCRIPT], input="", capture_output=True, text=True, timeout=15)
check("empty stdin: no-op", (p.stdout or "").strip() in ("", "{}"), repr(p.stdout))
p = subprocess.run([sys.executable, SCRIPT], input="{not json", capture_output=True, text=True, timeout=15)
check("bad json: no-op", (p.stdout or "").strip() in ("", "{}"), repr(p.stdout))
check("missing tool_input: no-op",
      _run({"event": "pre_tool_call", "tool_name": "write_file"}) == {})

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

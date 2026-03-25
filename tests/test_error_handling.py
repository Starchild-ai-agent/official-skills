"""
Test 1: Error Handling Quality
核心问题: silent except:pass 让小模型无法知道出了什么错，无法自我修正。
"""
import os, re, ast, json
from config import REPO_ROOT, SKILLS_WITH_CODE

class ErrorHandlingTester:
    def __init__(self):
        self.results = []

    def run(self):
        for skill in SKILLS_WITH_CODE:
            skill_dir = os.path.join(REPO_ROOT, skill)
            py_files = [f for f in os.listdir(skill_dir) if f.endswith('.py')]
            for fname in py_files:
                fpath = os.path.join(skill_dir, fname)
                with open(fpath, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')

                self._check_silent_except(skill, fname, content, lines)
                self._check_bare_return_on_error(skill, fname, content, lines)
                self._check_error_message_quality(skill, fname, content, lines)
                self._check_retry_logic(skill, fname, content, lines)
                self._check_timeout_handling(skill, fname, content, lines)
                self._check_http_status_handling(skill, fname, content, lines)

        return self.results

    def _check_silent_except(self, skill, fname, content, lines):
        """找所有 except 块中没有有意义错误输出的地方"""
        # Pattern: except ... : followed by pass/return None/return ""/return []
        patterns = [
            (r'except\s*(?:\w+\s*(?:as\s+\w+)?)?\s*:\s*\n\s*pass', 'SILENT_EXCEPT_PASS'),
            (r'except\s*(?:\w+\s*(?:as\s+\w+)?)?\s*:\s*\n\s*return\s*None', 'SILENT_EXCEPT_RETURN_NONE'),
            (r'except\s*(?:\w+\s*(?:as\s+\w+)?)?\s*:\s*\n\s*return\s*\[\]', 'SILENT_EXCEPT_RETURN_EMPTY'),
            (r'except\s*(?:\w+\s*(?:as\s+\w+)?)?\s*:\s*\n\s*return\s*\{\}', 'SILENT_EXCEPT_RETURN_EMPTY_DICT'),
            (r'except\s*(?:\w+\s*(?:as\s+\w+)?)?\s*:\s*\n\s*return\s*""', 'SILENT_EXCEPT_RETURN_EMPTY_STR'),
            (r'except\s*:\s*\n', 'BARE_EXCEPT'),  # except: without exception type
        ]
        for pat, issue_type in patterns:
            for m in re.finditer(pat, content):
                line_no = content[:m.start()].count('\n') + 1
                context = self._get_context(lines, line_no, 3)
                self.results.append({
                    'skill': skill,
                    'file': fname,
                    'line': line_no,
                    'severity': 'CRITICAL',
                    'issue': issue_type,
                    'impact': 'Small model receives empty/None, cannot diagnose failure',
                    'context': context,
                    'fix': f'Replace with: raise ToolError("{{skill}}/{{tool}}: {{specific_reason}}")'
                })

    def _check_bare_return_on_error(self, skill, fname, content, lines):
        """找 HTTP 请求后只检查 status 但不返回错误详情的地方"""
        # Pattern: if response.status != 200: return something without error detail
        pat = r'if\s+(?:response|resp|r)\.(?:status|status_code)\s*!=\s*200.*?:\s*\n\s*return\s+(None|\[\]|\{\}|"")'
        for m in re.finditer(pat, content):
            line_no = content[:m.start()].count('\n') + 1
            self.results.append({
                'skill': skill,
                'file': fname,
                'line': line_no,
                'severity': 'HIGH',
                'issue': 'HTTP_ERROR_SWALLOWED',
                'impact': 'API failure returns empty value, small model thinks "no data" instead of "API error"',
                'context': self._get_context(lines, line_no, 3),
                'fix': 'Return error with status code and response body excerpt'
            })

    def _check_error_message_quality(self, skill, fname, content, lines):
        """检查 raise/return 的错误信息是否包含足够上下文"""
        # Find all raise statements
        for i, line in enumerate(lines):
            stripped = line.strip()
            # raise Exception("...") or raise ToolError("...")
            if stripped.startswith('raise') and '(' in stripped:
                # Check if error message includes: tool name, parameter info, or actionable hint
                msg_match = re.search(r'raise\s+\w+\(["\'](.+?)["\']', stripped)
                if msg_match:
                    msg = msg_match.group(1)
                    has_context = any(k in msg.lower() for k in [skill, 'failed', 'invalid', 'missing', 'expected', 'got'])
                    if not has_context and len(msg) < 20:
                        self.results.append({
                            'skill': skill,
                            'file': fname,
                            'line': i + 1,
                            'severity': 'MEDIUM',
                            'issue': 'VAGUE_ERROR_MESSAGE',
                            'impact': f'Error message too vague for small model: "{msg}"',
                            'context': self._get_context(lines, i + 1, 2),
                            'fix': f'Include skill name, tool name, what was expected vs got'
                        })

    def _check_retry_logic(self, skill, fname, content, lines):
        """检查是否有 HTTP 请求但没有重试逻辑"""
        has_http = bool(re.search(r'(?:proxied_get|proxied_post|requests\.|\.get\(|\.post\(|fetch)', content))
        has_retry = bool(re.search(r'(?:retry|retries|max_attempts|backoff|tenacity)', content))
        if has_http and not has_retry:
            self.results.append({
                'skill': skill,
                'file': fname,
                'line': 0,
                'severity': 'MEDIUM',
                'issue': 'NO_RETRY_LOGIC',
                'impact': 'Transient API failures (429/502/503) cause immediate tool failure',
                'context': '',
                'fix': 'Add retry with exponential backoff for 429/5xx responses'
            })

    def _check_timeout_handling(self, skill, fname, content, lines):
        """检查 HTTP 请求是否设置了超时"""
        # Find HTTP calls without timeout
        http_calls = list(re.finditer(r'(?:proxied_get|proxied_post|requests\.get|requests\.post)\s*\(', content))
        for m in http_calls:
            # Look ahead 200 chars for timeout parameter
            snippet = content[m.start():m.start()+300]
            paren_depth = 0
            end = 0
            for j, c in enumerate(snippet):
                if c == '(': paren_depth += 1
                elif c == ')': 
                    paren_depth -= 1
                    if paren_depth == 0:
                        end = j
                        break
            call_text = snippet[:end+1] if end else snippet
            if 'timeout' not in call_text:
                line_no = content[:m.start()].count('\n') + 1
                self.results.append({
                    'skill': skill,
                    'file': fname,
                    'line': line_no,
                    'severity': 'LOW',
                    'issue': 'NO_TIMEOUT',
                    'impact': 'HTTP call can hang indefinitely, blocking agent',
                    'context': self._get_context(lines, line_no, 1),
                    'fix': 'Add timeout=15 (or appropriate value)'
                })

    def _check_http_status_handling(self, skill, fname, content, lines):
        """检查 HTTP 响应是否检查了状态码"""
        http_calls = list(re.finditer(r'(?:await\s+)?(?:proxied_get|proxied_post)\s*\(', content))
        for m in http_calls:
            line_no = content[:m.start()].count('\n') + 1
            # Check next 10 lines for status check
            check_region = '\n'.join(lines[line_no:line_no+10])
            has_check = bool(re.search(r'(?:status|status_code|\.ok|raise_for_status)', check_region))
            if not has_check:
                self.results.append({
                    'skill': skill,
                    'file': fname,
                    'line': line_no,
                    'severity': 'HIGH',
                    'issue': 'NO_STATUS_CHECK',
                    'impact': 'HTTP error response parsed as valid data, returns garbage to agent',
                    'context': self._get_context(lines, line_no, 2),
                    'fix': 'Check response status before parsing JSON'
                })

    def _get_context(self, lines, line_no, ctx=2):
        start = max(0, line_no - ctx - 1)
        end = min(len(lines), line_no + ctx)
        result = []
        for i in range(start, end):
            prefix = ">>>" if i == line_no - 1 else "   "
            result.append(f"{prefix} {i+1:4d}: {lines[i]}")
        return '\n'.join(result)


def run_test():
    tester = ErrorHandlingTester()
    results = tester.run()
    return {
        'test_name': 'Error Handling Quality',
        'total_issues': len(results),
        'by_severity': {
            'CRITICAL': len([r for r in results if r['severity'] == 'CRITICAL']),
            'HIGH': len([r for r in results if r['severity'] == 'HIGH']),
            'MEDIUM': len([r for r in results if r['severity'] == 'MEDIUM']),
            'LOW': len([r for r in results if r['severity'] == 'LOW']),
        },
        'by_skill': {},
        'details': results
    }
    # Aggregate by skill
    for r in results:
        s = r['skill']
        if s not in result['by_skill']:
            result['by_skill'][s] = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'total': 0}
        result['by_skill'][s][r['severity']] += 1
        result['by_skill'][s]['total'] += 1
    return result

if __name__ == '__main__':
    r = run_test()
    print(json.dumps(r, indent=2, default=str))


# ---- pytest-compatible entry point ----
def test_audit_runs_without_crash():
    """Verify the audit analysis completes without exceptions."""
    result = run_test()
    assert result is not None
    assert 'test_name' in result

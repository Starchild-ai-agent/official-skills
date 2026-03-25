"""
Test 2: Return Format Consistency
核心问题: 小模型需要可预测的返回格式。混用 dict/str/ToolResult/None 会导致解析混乱。
"""
import os, re, ast, json
from config import REPO_ROOT, SKILLS_WITH_CODE

class ReturnFormatTester:
    def __init__(self):
        self.results = []
        self.tool_signatures = {}  # skill -> [{name, returns, pattern}]

    def run(self):
        for skill in SKILLS_WITH_CODE:
            skill_dir = os.path.join(REPO_ROOT, skill)
            self.tool_signatures[skill] = []

            py_files = [f for f in os.listdir(skill_dir) if f.endswith('.py') and f != '__init__.py']
            for fname in py_files:
                fpath = os.path.join(skill_dir, fname)
                with open(fpath, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')

                self._analyze_tool_returns(skill, fname, content, lines)
                self._check_return_type_consistency(skill, fname, content, lines)
                self._check_json_serialization(skill, fname, content, lines)
                self._check_large_response_handling(skill, fname, content, lines)

        self._check_cross_skill_consistency()
        return self.results

    def _analyze_tool_returns(self, skill, fname, content, lines):
        """分析每个 tool 函数的返回类型模式"""
        # Find all async def that look like tool functions (in tools.py or *_tools.py)
        if 'tools' not in fname and 'client' not in fname:
            return

        func_pattern = re.compile(r'async\s+def\s+(\w+)\s*\(.*?\).*?:', re.DOTALL)
        for m in func_pattern.finditer(content):
            func_name = m.group(1)
            if func_name.startswith('_'):
                continue

            # Find function body
            func_start = m.end()
            indent_match = re.search(r'\n(\s+)', content[func_start:func_start+100])
            if not indent_match:
                continue

            base_indent = len(indent_match.group(1))
            func_body = self._extract_func_body(content, func_start, base_indent)

            # Classify return patterns
            return_patterns = set()
            for ret_match in re.finditer(r'return\s+(.+?)(?:\n|$)', func_body):
                ret_val = ret_match.group(1).strip()
                ret_type = self._classify_return(ret_val)
                return_patterns.add(ret_type)

            if len(return_patterns) > 1:
                line_no = content[:m.start()].count('\n') + 1
                self.results.append({
                    'skill': skill,
                    'file': fname,
                    'line': line_no,
                    'severity': 'HIGH',
                    'issue': 'MIXED_RETURN_TYPES',
                    'impact': f'Tool "{func_name}" returns multiple types: {return_patterns}. Small model cannot predict parse strategy.',
                    'context': f'Function: {func_name}',
                    'fix': 'Standardize: always return dict on success, always raise ToolError on failure'
                })

            self.tool_signatures[skill].append({
                'name': func_name,
                'file': fname,
                'return_types': list(return_patterns)
            })

    def _classify_return(self, ret_val):
        """Classify what type a return statement produces"""
        if ret_val in ('None', ''):
            return 'None'
        if ret_val.startswith('{') or ret_val.startswith('dict('):
            return 'dict'
        if ret_val.startswith('['):
            return 'list'
        if ret_val.startswith('"') or ret_val.startswith("'") or ret_val.startswith('f"') or ret_val.startswith("f'"):
            return 'string'
        if ret_val.startswith('json.dumps'):
            return 'json_string'
        if ret_val.startswith('ToolResult'):
            return 'ToolResult'
        if '.json()' in ret_val or 'data' in ret_val:
            return 'parsed_response'
        return 'other'

    def _check_return_type_consistency(self, skill, fname, content, lines):
        """检查同一文件内的工具函数是否用一致的返回模式"""
        # Already covered by _analyze_tool_returns at function level
        pass

    def _check_json_serialization(self, skill, fname, content, lines):
        """检查是否有返回无法 JSON 序列化的对象"""
        # Pattern: returning raw datetime, Decimal, or custom objects
        dangerous_returns = [
            (r'return\s+.*datetime\.now', 'UNSERIALIZABLE_DATETIME'),
            (r'return\s+.*Decimal\(', 'UNSERIALIZABLE_DECIMAL'),
        ]
        for pat, issue in dangerous_returns:
            for m in re.finditer(pat, content):
                line_no = content[:m.start()].count('\n') + 1
                self.results.append({
                    'skill': skill,
                    'file': fname,
                    'line': line_no,
                    'severity': 'MEDIUM',
                    'issue': issue,
                    'impact': 'Return value may fail JSON serialization',
                    'context': self._get_context(lines, line_no, 1),
                    'fix': 'Convert to string/float before returning'
                })

    def _check_large_response_handling(self, skill, fname, content, lines):
        """检查是否有工具返回未截断的大数据"""
        # Skills that return lists without pagination/limits
        if 'tools' not in fname:
            return

        # Find functions that return list data without any limit/truncation
        for m in re.finditer(r'async\s+def\s+(\w+)', content):
            func_name = m.group(1)
            func_start = m.start()
            # Check next 50 lines for evidence of pagination/limit
            region = content[func_start:func_start+3000]
            returns_list = bool(re.search(r'return\s+\[', region) or re.search(r'return\s+(?:data|results|items)', region))
            has_limit = bool(re.search(r'(?:limit|max_results|page|[:]\s*\d+\]|truncat)', region))

            if returns_list and not has_limit and not func_name.startswith('_'):
                line_no = content[:func_start].count('\n') + 1
                self.results.append({
                    'skill': skill,
                    'file': fname,
                    'line': line_no,
                    'severity': 'MEDIUM',
                    'issue': 'UNBOUNDED_RESPONSE',
                    'impact': f'Tool "{func_name}" may return unbounded list, flooding small model context window',
                    'context': f'Function: {func_name}',
                    'fix': 'Add default limit parameter, truncate with "[...N more items]" indicator'
                })

    def _check_cross_skill_consistency(self):
        """检查不同 skill 之间的返回格式是否一致"""
        # Group by return type patterns
        pattern_groups = {}
        for skill, tools in self.tool_signatures.items():
            for tool in tools:
                key = tuple(sorted(tool['return_types']))
                if key not in pattern_groups:
                    pattern_groups[key] = []
                pattern_groups[key].append(f"{skill}/{tool['name']}")

        # If there are many different patterns, that's an issue
        if len(pattern_groups) > 3:
            self.results.append({
                'skill': '_cross_skill',
                'file': 'N/A',
                'line': 0,
                'severity': 'HIGH',
                'issue': 'INCONSISTENT_CROSS_SKILL_FORMATS',
                'impact': f'{len(pattern_groups)} different return patterns across skills. Small model must learn each one.',
                'context': json.dumps({str(k): len(v) for k, v in pattern_groups.items()}, indent=2),
                'fix': 'Standardize on: success → dict with typed fields, error → ToolError with message'
            })

    def _extract_func_body(self, content, start, base_indent):
        """Extract function body based on indentation"""
        lines = content[start:].split('\n')
        body_lines = []
        for line in lines[1:]:
            if line.strip() == '':
                body_lines.append(line)
                continue
            indent = len(line) - len(line.lstrip())
            if indent < base_indent and line.strip():
                break
            body_lines.append(line)
        return '\n'.join(body_lines)

    def _get_context(self, lines, line_no, ctx=2):
        start = max(0, line_no - ctx - 1)
        end = min(len(lines), line_no + ctx)
        return '\n'.join(f"{'>>>' if i==line_no-1 else '   '} {i+1:4d}: {lines[i]}" for i in range(start, end))


def run_test():
    tester = ReturnFormatTester()
    results = tester.run()

    by_skill = {}
    for r in results:
        s = r['skill']
        if s not in by_skill:
            by_skill[s] = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'total': 0}
        by_skill[s][r['severity']] += 1
        by_skill[s]['total'] += 1

    return {
        'test_name': 'Return Format Consistency',
        'total_issues': len(results),
        'by_severity': {
            'CRITICAL': len([r for r in results if r['severity'] == 'CRITICAL']),
            'HIGH': len([r for r in results if r['severity'] == 'HIGH']),
            'MEDIUM': len([r for r in results if r['severity'] == 'MEDIUM']),
            'LOW': len([r for r in results if r['severity'] == 'LOW']),
        },
        'by_skill': by_skill,
        'tool_signatures': {s: t for s, t in tester.tool_signatures.items() if t},
        'details': results
    }

if __name__ == '__main__':
    r = run_test()
    print(json.dumps(r, indent=2, default=str))


# ---- pytest-compatible entry point ----
def test_audit_runs_without_crash():
    """Verify the audit analysis completes without exceptions."""
    result = run_test()
    assert result is not None
    assert 'test_name' in result

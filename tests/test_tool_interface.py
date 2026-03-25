"""
Test 4: Tool Interface Quality  
核心问题: 小模型需要清晰的函数签名 — 命名直觉、参数少且有默认值、description 精确。
"""
import os, re, json, ast
from config import REPO_ROOT, SKILLS_WITH_CODE

class ToolInterfaceTester:
    def __init__(self):
        self.results = []
        self.all_tools = []

    def run(self):
        for skill in SKILLS_WITH_CODE:
            skill_dir = os.path.join(REPO_ROOT, skill)
            py_files = [f for f in os.listdir(skill_dir) if f.endswith('.py')]

            for fname in py_files:
                fpath = os.path.join(skill_dir, fname)
                with open(fpath, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')

                self._check_tool_naming(skill, fname, content)
                self._check_param_complexity(skill, fname, content)
                self._check_descriptions(skill, fname, content)
                self._check_param_validation(skill, fname, content)
                self._check_param_defaults(skill, fname, content)

        self._check_naming_collisions()
        return self.results

    def _check_tool_naming(self, skill, fname, content):
        """Tool 名字是否直觉：动词_名词 模式，长度适中"""
        # Find tool registration patterns: name="xxx"
        for m in re.finditer(r'name\s*=\s*["\'](\w+)["\']', content):
            name = m.group(1)
            line_no = content[:m.start()].count('\n') + 1

            self.all_tools.append({'skill': skill, 'name': name, 'file': fname})

            # Check naming conventions
            parts = name.split('_')

            # Too long?
            if len(name) > 30:
                self._add(skill, fname, line_no, 'MEDIUM', 'LONG_TOOL_NAME',
                    f'Tool name "{name}" is {len(name)} chars. Small model may truncate or confuse.',
                    'Keep tool names under 25 chars')

            # No verb prefix?
            common_verbs = ['get', 'set', 'create', 'delete', 'update', 'list', 'search', 'check', 'send', 'cancel', 'modify']
            has_verb = any(parts[0] == v for v in common_verbs)
            # Also accept skill-prefixed names like hl_account, cg_trending
            is_prefixed = len(parts) >= 2 and len(parts[0]) <= 3

            if not has_verb and not is_prefixed and len(parts) > 1:
                self._add(skill, fname, line_no, 'LOW', 'NO_VERB_PREFIX',
                    f'Tool "{name}" has no action verb. Consider: get_{name} or {name}_get',
                    'Prefix with action verb for clarity')

            # Ambiguous names
            if name in ['data', 'info', 'result', 'query', 'fetch']:
                self._add(skill, fname, line_no, 'HIGH', 'AMBIGUOUS_NAME',
                    f'Tool name "{name}" is too generic. Small model cannot distinguish from other skills.',
                    f'Prefix with skill domain: {skill}_{name}')

    def _check_param_complexity(self, skill, fname, content):
        """Too many required params = small model makes mistakes"""
        # Find tool class definitions with parameters
        param_blocks = re.finditer(
            r'class\s+(\w+).*?parameters\s*=\s*\[(.*?)\]',
            content, re.DOTALL
        )

        for m in param_blocks:
            class_name = m.group(1)
            param_text = m.group(2)
            line_no = content[:m.start()].count('\n') + 1

            # Count required params (required=True)
            required_count = len(re.findall(r'required\s*=\s*True', param_text))
            total_params = len(re.findall(r'ToolParameter\s*\(', param_text))

            if required_count > 4:
                self._add(skill, fname, line_no, 'HIGH', 'TOO_MANY_REQUIRED_PARAMS',
                    f'Tool "{class_name}" has {required_count} required params. Small model error rate rises sharply above 3.',
                    'Add sensible defaults, make params optional with documented defaults')

            if total_params > 8:
                self._add(skill, fname, line_no, 'MEDIUM', 'TOO_MANY_PARAMS',
                    f'Tool "{class_name}" has {total_params} params total. Consider splitting into focused tools.',
                    'Split into sub-tools or use a config object')

    def _check_descriptions(self, skill, fname, content):
        """Tool descriptions should be concise and actionable"""
        for m in re.finditer(r'description\s*=\s*["\'](.+?)["\']', content):
            desc = m.group(1)
            line_no = content[:m.start()].count('\n') + 1

            if len(desc) < 10:
                self._add(skill, fname, line_no, 'HIGH', 'DESCRIPTION_TOO_SHORT',
                    f'Description too short: "{desc}". Small model cannot understand tool purpose.',
                    'Add what the tool does, what it returns, when to use it')

            if len(desc) > 200:
                self._add(skill, fname, line_no, 'LOW', 'DESCRIPTION_TOO_LONG',
                    f'Description is {len(desc)} chars. Small model may not read it all.',
                    'Keep under 150 chars, put details in SKILL.md')

            # Check for actionable language
            if not any(w in desc.lower() for w in ['get', 'fetch', 'return', 'check', 'set', 'create', 'list',
                                                     'search', 'send', 'cancel', 'calculate', 'monitor', 'swap',
                                                     'find', 'query', 'place', 'show', 'display', 'retrieve']):
                self._add(skill, fname, line_no, 'MEDIUM', 'PASSIVE_DESCRIPTION',
                    f'Description lacks action verb: "{desc[:60]}..."',
                    'Start with action verb: "Get...", "List...", "Calculate..."')

    def _check_param_validation(self, skill, fname, content):
        """Do tools validate their inputs or just crash?"""
        # Find tool execute methods
        for m in re.finditer(r'async\s+def\s+execute\s*\(self.*?\).*?:', content):
            func_start = m.end()
            body = content[func_start:func_start+2000]
            line_no = content[:m.start()].count('\n') + 1

            # Check for any validation
            has_validation = bool(re.search(r'(?:if\s+not\s+|if\s+\w+\s*(?:is None|==|!=|not in)|raise\s+\w*(?:Value|Type|Tool)Error|validate)', body))
            has_params = bool(re.search(r'params\s*[\.\[]', body))

            if has_params and not has_validation:
                self._add(skill, fname, line_no, 'MEDIUM', 'NO_INPUT_VALIDATION',
                    'Tool execute() reads params but never validates. Bad input → cryptic error.',
                    'Add early validation with clear error messages')

    def _check_param_defaults(self, skill, fname, content):
        """Check if optional params have documented defaults"""
        for m in re.finditer(r'ToolParameter\s*\(\s*name\s*=\s*["\'](\w+)["\'].*?required\s*=\s*False', content, re.DOTALL):
            param_name = m.group(1)
            param_block = content[m.start():m.start()+300]
            has_default_doc = bool(re.search(r'(?:default|defaults?\s*(?:to|:|\=))', param_block, re.I))

            if not has_default_doc:
                line_no = content[:m.start()].count('\n') + 1
                self._add(skill, fname, line_no, 'LOW', 'UNDOCUMENTED_DEFAULT',
                    f'Optional param "{param_name}" has no documented default value.',
                    'Add "Default: X" to description')

    def _check_naming_collisions(self):
        """同名工具跨 skill 冲突"""
        names = {}
        for t in self.all_tools:
            if t['name'] not in names:
                names[t['name']] = []
            names[t['name']].append(t['skill'])

        for name, skills in names.items():
            if len(skills) > 1:
                self.results.append({
                    'skill': '/'.join(skills),
                    'file': 'N/A',
                    'line': 0,
                    'severity': 'CRITICAL',
                    'issue': 'TOOL_NAME_COLLISION',
                    'impact': f'Tool name "{name}" used by {skills}. Agent may call wrong skill.',
                    'context': '',
                    'fix': f'Prefix with skill name: {skills[0]}_{name}, {skills[1]}_{name}'
                })

    def _add(self, skill, fname, line, severity, issue, impact, fix=''):
        self.results.append({
            'skill': skill, 'file': fname, 'line': line,
            'severity': severity, 'issue': issue,
            'impact': impact, 'context': '', 'fix': fix
        })


def run_test():
    tester = ToolInterfaceTester()
    results = tester.run()

    by_skill = {}
    for r in results:
        s = r['skill']
        if s not in by_skill:
            by_skill[s] = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'total': 0}
        by_skill[s][r['severity']] += 1
        by_skill[s]['total'] += 1

    return {
        'test_name': 'Tool Interface Quality',
        'total_issues': len(results),
        'total_tools_found': len(tester.all_tools),
        'by_severity': {
            'CRITICAL': len([r for r in results if r['severity'] == 'CRITICAL']),
            'HIGH': len([r for r in results if r['severity'] == 'HIGH']),
            'MEDIUM': len([r for r in results if r['severity'] == 'MEDIUM']),
            'LOW': len([r for r in results if r['severity'] == 'LOW']),
        },
        'by_skill': by_skill,
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

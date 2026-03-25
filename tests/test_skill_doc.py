"""
Test 3: SKILL.md Documentation Quality (Small Model Parsability)
核心问题: 小模型的 context window 小、推理弱，SKILL.md 必须极度结构化才能被正确理解。
"""
import os, re, json, yaml
from config import REPO_ROOT, SKILLS_WITH_CODE

# All skills (including doc-only)
ALL_SKILLS = [d for d in os.listdir(REPO_ROOT)
              if os.path.isdir(os.path.join(REPO_ROOT, d))
              and os.path.exists(os.path.join(REPO_ROOT, d, 'SKILL.md'))
              and not d.startswith('.')]


class SkillDocTester:
    def __init__(self):
        self.results = []
        self.scores = {}

    def run(self):
        for skill in ALL_SKILLS:
            skill_md = os.path.join(REPO_ROOT, skill, 'SKILL.md')
            with open(skill_md, 'r') as f:
                content = f.read()

            score = 0
            max_score = 0

            # 1. Frontmatter completeness
            s, m = self._check_frontmatter(skill, content)
            score += s; max_score += m

            # 2. Has explicit workflow/decision tree
            s, m = self._check_workflow(skill, content)
            score += s; max_score += m

            # 3. Tool descriptions with params & examples
            s, m = self._check_tool_docs(skill, content)
            score += s; max_score += m

            # 4. Error handling guidance
            s, m = self._check_error_docs(skill, content)
            score += s; max_score += m

            # 5. Token efficiency (small model = every token counts)
            s, m = self._check_token_efficiency(skill, content)
            score += s; max_score += m

            # 6. Decision boundaries (when to use THIS skill vs others)
            s, m = self._check_decision_boundaries(skill, content)
            score += s; max_score += m

            self.scores[skill] = {
                'score': score,
                'max_score': max_score,
                'pct': round(score / max_score * 100) if max_score > 0 else 0,
                'grade': self._grade(score, max_score),
                'char_count': len(content),
                'line_count': content.count('\n'),
            }

        return self.results

    def _check_frontmatter(self, skill, content):
        """YAML frontmatter: name, description, tools, version"""
        score, max_s = 0, 5
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            self._add(skill, 'CRITICAL', 'NO_FRONTMATTER', 'SKILL.md has no YAML frontmatter. Agent cannot auto-discover tools.')
            return 0, max_s

        try:
            fm = yaml.safe_load(fm_match.group(1))
        except:
            self._add(skill, 'CRITICAL', 'INVALID_FRONTMATTER', 'YAML frontmatter parse error')
            return 0, max_s

        score += 1  # has frontmatter
        required = ['name', 'description', 'tools']
        for field in required:
            if field in fm and fm[field]:
                score += 1
            else:
                self._add(skill, 'HIGH', f'MISSING_FM_{field.upper()}', f'Frontmatter missing "{field}"')

        if 'tags' in fm and fm['tags']:
            score += 1
        else:
            self._add(skill, 'LOW', 'NO_TAGS', 'No tags for marketplace discovery')

        return score, max_s

    def _check_workflow(self, skill, content):
        """Does it have a clear step-by-step workflow?"""
        score, max_s = 0, 4

        has_workflow = bool(re.search(r'(?i)##\s*(?:workflow|usage|how to|steps|quick\s*start)', content))
        has_numbered = bool(re.search(r'(?:^|\n)\s*[1-3]\.\s+', content))
        has_code_block = bool(re.search(r'```', content))
        has_decision = bool(re.search(r'(?:if|when|choose|prefer|instead)', content, re.I))

        if has_workflow:
            score += 1
        else:
            self._add(skill, 'HIGH', 'NO_WORKFLOW_SECTION', 'No explicit Workflow section. Small model cannot infer tool call sequence.')

        if has_numbered:
            score += 1
        else:
            self._add(skill, 'MEDIUM', 'NO_NUMBERED_STEPS', 'No numbered step sequence.')

        if has_code_block:
            score += 1
        else:
            self._add(skill, 'MEDIUM', 'NO_CODE_EXAMPLES', 'No code/tool call examples.')

        if has_decision:
            score += 1

        return score, max_s

    def _check_tool_docs(self, skill, content):
        """Each tool should have: description, params table, example call"""
        score, max_s = 0, 4

        # Check if tools section exists
        has_tools_section = bool(re.search(r'(?i)##\s*(?:tools|available tools|tool reference)', content))
        if has_tools_section:
            score += 1
        # Check for parameter docs (params, arguments, etc.)
        has_params = bool(re.search(r'(?i)(?:param|argument|input|field)\s*[:\|]', content))
        if has_params:
            score += 1
        else:
            self._add(skill, 'MEDIUM', 'NO_PARAM_DOCS', 'Tool parameters not documented. Small model guesses param names.')

        # Check for return value docs
        has_returns = bool(re.search(r'(?i)(?:return|output|response)\s*[:\|]', content))
        if has_returns:
            score += 1
        else:
            self._add(skill, 'MEDIUM', 'NO_RETURN_DOCS', 'Tool return values not documented.')

        # Check for usage examples
        has_examples = bool(re.search(r'(?:`[a-z_]+\(|example|usage\s*:)', content, re.I))
        if has_examples:
            score += 1

        return score, max_s

    def _check_error_docs(self, skill, content):
        """Does the doc tell the agent what to do when things fail?"""
        score, max_s = 0, 3

        has_error_section = bool(re.search(r'(?i)(?:error|troubleshoot|common issues|gotcha|caveat|important)', content))
        has_rate_limit = bool(re.search(r'(?i)(?:rate.?limit|429|throttl)', content))
        has_fallback = bool(re.search(r'(?i)(?:fallback|alternative|if.*fail|retry)', content))

        if has_error_section:
            score += 1
        else:
            self._add(skill, 'MEDIUM', 'NO_ERROR_GUIDANCE', 'No error handling guidance. Small model stuck when tool fails.')
        if has_rate_limit:
            score += 1
        if has_fallback:
            score += 1

        return score, max_s

    def _check_token_efficiency(self, skill, content):
        """Is the doc concise enough for small model context?"""
        score, max_s = 0, 3
        lines = content.count('\n')
        chars = len(content)

        if chars < 8000:
            score += 2  # good, fits in small context
        elif chars < 15000:
            score += 1
            self._add(skill, 'LOW', 'LARGE_SKILLMD', f'SKILL.md is {chars} chars ({lines} lines). May crowd small model context.')
        else:
            self._add(skill, 'MEDIUM', 'OVERSIZED_SKILLMD', f'SKILL.md is {chars} chars ({lines} lines). Will consume most of small model context window.')

        # Check for redundancy
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) > 0:
            avg_len = sum(len(p) for p in paragraphs) / len(paragraphs)
            if avg_len < 300:
                score += 1  # good density
            else:
                self._add(skill, 'LOW', 'VERBOSE_PARAGRAPHS', f'Average paragraph length {avg_len:.0f} chars. Consider tighter writing.')

        return score, max_s

    def _check_decision_boundaries(self, skill, content):
        """Does it tell the agent WHEN to use this skill vs alternatives?"""
        score, max_s = 0, 2

        has_when_to_use = bool(re.search(r'(?i)(?:when to use|use this when|best for|not for|don.t use)', content))
        if has_when_to_use:
            score += 1
        else:
            self._add(skill, 'MEDIUM', 'NO_USAGE_BOUNDARIES', 'No guidance on when to use/not use this skill. Small model may pick wrong skill.')

        has_prereqs = bool(re.search(r'(?i)(?:prerequisite|requires|before using|setup|must have)', content))
        if has_prereqs:
            score += 1

        return score, max_s

    def _grade(self, score, max_s):
        pct = score / max_s * 100 if max_s > 0 else 0
        if pct >= 85: return 'A'
        if pct >= 70: return 'B'
        if pct >= 55: return 'C'
        if pct >= 40: return 'D'
        return 'F'

    def _add(self, skill, severity, issue, impact, fix=''):
        self.results.append({
            'skill': skill,
            'file': 'SKILL.md',
            'line': 0,
            'severity': severity,
            'issue': issue,
            'impact': impact,
            'context': '',
            'fix': fix
        })


def run_test():
    tester = SkillDocTester()
    results = tester.run()
    return {
        'test_name': 'SKILL.md Documentation Quality',
        'total_issues': len(results),
        'scores': tester.scores,
        'by_severity': {
            'CRITICAL': len([r for r in results if r['severity'] == 'CRITICAL']),
            'HIGH': len([r for r in results if r['severity'] == 'HIGH']),
            'MEDIUM': len([r for r in results if r['severity'] == 'MEDIUM']),
            'LOW': len([r for r in results if r['severity'] == 'LOW']),
        },
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
